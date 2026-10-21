"""ECE 导出模块单测：只测不依赖 Motor-CAD 的纯数据部分。

对应设计 `docs/design/e11-control-model.md` §4.3（产出物）与 §6（验收标准 F2）。
Motor-CAD 相关步骤（反电势、饱和图）需真实实例，不在单测范围——由 `scripts/run_ece_export.py`
的端到端运行覆盖。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from motorcad_controller.ece_exporter import (
    ECEExportError,
    GridPlan,
    LookupTable,
    build_lookup,
    derive_grid,
    write_sml,
    write_txt,
)


class TestGridContainsZero:
    """Motor-CAD 要求饱和图网格含 Id=0；偶数点数会把 0 挤掉（实测拒绝导出）。"""

    @staticmethod
    def _req(step: float):
        from pathlib import Path

        from motorcad_controller.ece_exporter import ECERequest

        return ECERequest(
            mot_path=Path("x.mot"), output_dir=Path("o"), base_name="e11",
            shaft_speed=6000, dc_bus_voltage=400, machine_temp=65,
            id_max=433, current_step=step,
        )

    def test_even_segments_accepted(self) -> None:
        # 20 段 / 21 点、40 段 / 41 点、8 段 / 9 点都含 0
        from motorcad_controller.ece_exporter import _check_grid_contains_zero
        _check_grid_contains_zero(self._req(2 * 433 / 20))
        _check_grid_contains_zero(self._req(2 * 433 / 40))
        _check_grid_contains_zero(self._req(2 * 433 / 8))

    def test_even_point_grid_without_zero_rejected(self) -> None:
        """20 点偶数段：端点 433、步长不整除，0 落在两个格点之间（实测 Motor-CAD 拒绝）。"""
        from motorcad_controller.ece_exporter import _check_grid_contains_zero
        with pytest.raises(ECEExportError, match="含 Id = 0"):
            _check_grid_contains_zero(self._req(2 * 433 / 19))

    def test_short_step_rejected(self) -> None:
        """步长不整除 2·id_max 时末点越过 max，取点规则下同样可能漏 0。"""
        from motorcad_controller.ece_exporter import _check_grid_contains_zero
        with pytest.raises(ECEExportError, match="含 Id = 0"):
            _check_grid_contains_zero(self._req(100.0))


class TestDeriveGrid:
    """官方 :241-262 的网格推导。"""

    def test_integer_alignment_gives_expected_step(self) -> None:
        # 对齐角 90° → 质因数 [2,3,3,5]；最大因式 5 → 120/5 = 24 < 30，退到 3 → 120/3 = 40 ✓
        grid = derive_grid(90.0, pole_pairs=4.0)
        assert grid.elec_step_deg == 3.0
        assert grid.points_per_cycle == 120
        assert grid.map_points == 41
        assert grid.mech_step_deg == pytest.approx(0.75)

    def test_alignment_120(self) -> None:
        # 120° → 质因数 [2,2,2,3,5]；最大 5 → 24 < 30，退到 3 → 40 ✓
        grid = derive_grid(120.0, pole_pairs=4.0)
        assert grid.elec_step_deg == 3.0
        assert grid.map_points == 41

    def test_non_integer_alignment_is_rounded(self) -> None:
        # 实测 e11 的 DriveOffsetAngleLoad = 0 → 对齐角 90；这里验证四舍五入口径
        grid = derive_grid(90.4, pole_pairs=4.0)
        assert grid.elec_step_deg == 3.0

    def test_zero_pole_pairs_rejected(self) -> None:
        with pytest.raises(ECEExportError, match="极对数"):
            derive_grid(90.0, pole_pairs=0.0)


def _make_mat(n_pos: int, d_vals: np.ndarray, q_vals: np.ndarray) -> dict:
    """构造一份饱和图 MAT。

    位置轴用**递增斜坡**（第 k 个样本值 = k），磁链也随样本号递增。这样索引取错点会直接反在
    数值上，测试才能区分「按周期回绕」与「按样本数回绕」——两者只差一个下标。
    """
    pos_ramp = np.arange(n_pos, dtype=float)
    flux_d = np.repeat(pos_ramp[None, None, :], d_vals.size, axis=0)
    flux_d = np.repeat(flux_d, q_vals.size, axis=1)
    return {
        "Id_Peak": np.repeat(d_vals[:, None], q_vals.size, axis=1),
        "Iq_Peak": np.repeat(q_vals[None, :], d_vals.size, axis=0),
        "Angular_Flux_Linkage_D": flux_d,
        "Angular_Flux_Linkage_Q": np.ones((d_vals.size, q_vals.size, n_pos)),
        "Angular_Rotor_Position": np.repeat(pos_ramp[None, None, :], d_vals.size, axis=0).repeat(q_vals.size, axis=1),
        "Angular_Electromagnetic_Torque": np.full((d_vals.size, q_vals.size, n_pos), 2.0),
        "Phase_Advance": np.full((d_vals.size, q_vals.size), 45.0),
    }


def _synthetic_lookup(pole_pairs: float = 4.0) -> tuple[LookupTable, GridPlan]:
    """造一份 3×3 电流 × 一个满周期的假饱和图（121 样本 = 0..360 含首尾）。"""
    grid = derive_grid(90.0, pole_pairs)
    d_vals = np.array([-100.0, 0.0, 100.0])
    q_vals = np.array([-50.0, 0.0, 50.0])
    return build_lookup(_make_mat(121, d_vals, q_vals), grid), grid


class TestBuildLookup:
    def test_shape_and_order(self) -> None:
        table, grid = _synthetic_lookup()
        assert table.rows() == 3 * 3 * grid.map_points
        # 官方取负：ECE 侧转矩正方向与 Motor-CAD 相反（:382）
        assert np.allclose(table.torque, -2.0)
        # Id 外层循环，Iq 内层——与官方 for i(Id) → for j(Iq) 一致
        assert table.id[0] == -100.0 and table.iq[0] == -50.0
        assert table.id[grid.map_points] == -100.0 and table.iq[grid.map_points] == 0.0

    def test_position_index_wraps_by_period(self) -> None:
        """索引序列必须与官方逐点一致：从 30 起往前取 41 点，负索引按**周期**回绕。

        期望序列（周期 120、样本 121）：
            raw  = 30, 29, ..., 0, -1, ..., -10
            idx  = 30, 29, ..., 0, 119, 118, ..., 110
        若按样本数 121 回绕，-1 会落成 120（360° 的重复样本），序列尾部整体错位——本测试能抓住。
        """
        table, grid = _synthetic_lookup()
        expected = list(range(30, -1, -1)) + list(range(119, 109, -1))
        assert grid.points_per_cycle == 120
        assert grid.map_points == 41
        # 位置斜坡第 k 个样本值就是 k，直接比对取到的样本号
        assert [int(v) for v in table.rotor_pos[: grid.map_points]] == expected

    def test_flux_follows_same_index(self) -> None:
        """磁链与位置用同一套索引，不能一个按周期、一个按样本数。"""
        table, grid = _synthetic_lookup()
        expected = list(range(30, -1, -1)) + list(range(119, 109, -1))
        assert [int(v) for v in table.flux_d[: grid.map_points]] == expected

    def test_missing_key_rejected(self) -> None:
        grid = derive_grid(90.0, 4.0)
        with pytest.raises(ECEExportError, match="MAT 缺键"):
            build_lookup({"Id_Peak": np.zeros((1, 1))}, grid)

    def test_actual_position_count_is_used(self) -> None:
        """位置点数按 MAT 实际值取（e11 实测 121 点 = 0..360 含首尾），不按 360/步长 推算。"""
        grid = derive_grid(90.0, 4.0)
        mat = _make_mat(121, np.array([0.0]), np.array([0.0]))
        table = build_lookup(mat, grid)
        assert table.rows() == grid.map_points
        # 121 样本（含首尾重复）必须能正常取满，不因多一个样本而拒绝
        assert int(table.rotor_pos[0]) == 30

    def test_short_map_rejected(self) -> None:
        """样本数少于一个周期（120）时无法覆盖满周期，必须拒。"""
        grid = derive_grid(90.0, 4.0)
        mat = _make_mat(100, np.array([0.0]), np.array([0.0]))
        with pytest.raises(ECEExportError, match="位置样本数"):
            build_lookup(mat, grid)

    def test_single_position_rejected(self) -> None:
        grid = derive_grid(90.0, 4.0)
        bad = {
            "Id_Peak": np.zeros((1, 1)), "Iq_Peak": np.zeros((1, 1)),
            "Angular_Flux_Linkage_D": np.zeros((1, 1, 1)),
            "Angular_Flux_Linkage_Q": np.zeros((1, 1, 1)),
            "Angular_Rotor_Position": np.zeros((1, 1, 1)),
            "Angular_Electromagnetic_Torque": np.zeros((1, 1, 1)),
            "Phase_Advance": np.zeros((1, 1)),
        }
        with pytest.raises(ECEExportError, match="位置样本数"):
            build_lookup(bad, grid)


class TestWriteTxt:
    def test_sections_and_poles(self, tmp_path: Path) -> None:
        table, grid = _synthetic_lookup()
        out = tmp_path / "t.txt"
        write_txt(out, table, grid, pole_pairs=4.0, phase_res=0.0134, phase_l=6.03e-6)
        text = out.read_text(encoding="ascii")
        for token in ("B_BasicData", "E_BasicData", "B_PhaseImp 3", "E_PhaseImp",
                      "B_Sweepings", "E_Sweepings", "B_OutputMatrix DQ0", "E_OutputMatrix"):
            assert token in text
        assert "\tPoles\t8" in text  # 极对数 4 → 8 极

    def test_row_count_matches_table(self, tmp_path: Path) -> None:
        table, grid = _synthetic_lookup()
        out = tmp_path / "t.txt"
        write_txt(out, table, grid, 4.0, 0.0134, 6.03e-6)
        rows = [ln for ln in out.read_text(encoding="ascii").splitlines()
                if ln.startswith("\t") and ln.count("\t") == 5 and ln[1].isdigit()]
        assert len(rows) == table.rows()


class TestWriteSml:
    def test_ports_complete(self, tmp_path: Path) -> None:
        table, grid = _synthetic_lookup()
        out = tmp_path / "m.sml"
        write_sml(out, table, grid, 4.0, 0.0134, 6.03e-6, "e11")
        text = out.read_text(encoding="ascii")
        assert text.startswith("MODELDEF ECE_e11")
        for port in ("A0", "X0", "B0", "Y0", "C0", "Z0"):
            assert f"PORT electrical: {port};" in text
        assert "PORT ROTATIONAL_V: ROT1;" in text
        assert "PORT ROTATIONAL_V: ROT2;" in text
        assert "PORT REAL OUT ANGLE[deg]: Pos = VM_Mdeg.V;" in text

    def test_records_not_double_spaced(self, tmp_path: Path) -> None:
        """写文件时不得把换行叠两层（Windows 上 text 模式会把 \\n 再转成 \\r\\n）。"""
        table, grid = _synthetic_lookup()
        out = tmp_path / "m.sml"
        write_sml(out, table, grid, 4.0, 0.0134, 6.03e-6, "e11")
        raw = out.read_bytes().decode("ascii")
        assert "\r\r\n" not in raw
        assert raw.split("\r\n")[0] == "MODELDEF ECE_e11"

    def test_mech_to_elec_ratio(self, tmp_path: Path) -> None:
        # Rpos = 0.0174533 · 极对数（官方 :654）
        table, grid = _synthetic_lookup()
        out = tmp_path / "m.sml"
        write_sml(out, table, grid, 4.0, 0.0134, 6.03e-6, "e11")
        assert "R:=0.0698132" in out.read_text(encoding="ascii")

    def test_pwl_data_volume_is_not_multiplied(self, tmp_path: Path) -> None:
        """表内数字总量必须是 d*q*mp*5 量级，不能是整列重复（历史缺陷：多写了 d*q 倍）。"""
        import re

        table, grid = _synthetic_lookup()
        out = tmp_path / "m.sml"
        write_sml(out, table, grid, 4.0, 0.0134, 6.03e-6, "e11")
        text = out.read_text(encoding="ascii")
        nums = re.findall(r"-?\d+\.?\d*(?:[eE][-+]?\d+)?", text)
        d_q = len(np.unique(table.id)) * len(np.unique(table.iq))
        mp = grid.map_points
        expected = d_q * mp * 4 + d_q * mp + d_q + d_q  # 4 列输出 + 位置坐标 + 电流坐标
        # 允许各层声明与端口常数带来的少量偏差，但绝不允许 d*q 倍重复
        assert len(nums) < expected * 1.5, f"数字 {len(nums)} 远超 {expected}，疑似整列重复"
        assert len(nums) > expected * 0.5

    def test_pwl_structure(self, tmp_path: Path) -> None:
        table, grid = _synthetic_lookup()
        out = tmp_path / "m.sml"
        write_sml(out, table, grid, 4.0, 0.0134, 6.03e-6, "e11")
        text = out.read_text(encoding="ascii")
        assert "pwl TABLE=(" in text
        assert "DEEPSPLINE" in text
        # 三层嵌套：Id 层 3 个、每个 Id 下 3 个 Iq 层，故位置层共 3×3 个
        assert text.count(f" {grid.map_points},") == 3 * 3
