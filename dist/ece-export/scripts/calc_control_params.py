"""e11 IPM 控制参数计算：从 ECE 数据反推电机参数、MTPA/弱磁轨迹与 PI 增益。

对应文档 本工具的开发者手册。

设计原则：
- **只用 ECE 的磁链表**，不用 MAT 里的 `Ld`/`Lq` 字段——后者在零电流处是除零产物
  （实测读到 -7.4e13），且量纲与 `varUnits` 标称不符。
- 电感一律按定义反推：`Lq = λq/iq`（Id=0 时）、`Ld = (λd − λpm)/id`（Iq=0 时）。
- 每个结果都打印公式与代入值，便于人工复核。

用法：
    python scripts/calc_control_params.py --mat results/e11-ece-61x61/ECE_e11_61x61_map.mat
    python scripts/calc_control_params.py --mat ... --json-out results/e11-params.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# 电机参数
# ---------------------------------------------------------------------------


@dataclass
class MotorParams:
    """从 ECE 数据与设计规格得到的电机参数。"""

    pole_pairs: int = 4                 # 极对数
    rs_ohm: float = 0.0133773639742649  # 每相电阻（ECE 实测，65 ℃）
    vdc: float = 400.0                  # 母线电压
    i_max: float = 433.0                # 峰值电流上限

    lam_pm: float = 0.0       # 永磁磁链 λpm (Wb)
    ld_h: float = 0.0         # d 轴电感（额定点，H）
    lq_h: float = 0.0         # q 轴电感（额定点，H）
    ld_sat_h: float = 0.0     # 大电流下的 Ld
    lq_sat_h: float = 0.0     # 大电流下的 Lq

    # 派生量
    v_max_peak: float = 0.0   # SVPWM 线性区相电压峰值
    lambda_max: float = 0.0   # 弱磁起点磁链模值上限
    base_speed_rpm: float = 0.0
    mtpa_id: float = 0.0
    mtpa_iq: float = 0.0
    mtpa_torque: float = 0.0
    torque_id0: float = 0.0   # id=0 时的电流圆转矩
    saliency: float = 0.0     # Lq/Ld

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# 1. 从 ECE MAT 提取
# ---------------------------------------------------------------------------


def load_ece(mat_path: Path) -> dict:
    """读 ECE 饱和图 MAT。"""
    from scipy import io as sio

    if not mat_path.is_file():
        raise SystemExit(f"MAT 不存在：{mat_path}")
    m = sio.loadmat(str(mat_path))
    required = ("Id_Peak", "Iq_Peak", "Flux_Linkage_D", "Flux_Linkage_Q",
                "Electromagnetic_Torque", "PM_Flux_Linkage")
    missing = [k for k in required if k not in m]
    if missing:
        raise SystemExit(f"MAT 缺键：{missing}")
    return m


def zero_index(vec: np.ndarray) -> int:
    """找最接近 0 的索引。"""
    return int(np.argmin(np.abs(vec)))


def derive_inductance(m: dict) -> tuple[float, float, float, float, float]:
    """由磁链反推 λpm 与 Ld/Lq。

    定义：λd = Ld·id + λpm，λq = Lq·iq
    故在 Iq=0 的截面上：λd(id) − λpm = Ld·id → Ld = Δλd/id
    在 Id=0 的截面上：λq = Lq·iq → Lq = λq/iq

    **取哪个点**：MTPA 工作点大致在 |Id|≈0.7·Imax、Iq≈0.7·Imax 附近，
    所以「额定点电感」取 0.7·Imax 处的值；「饱和端电感」取 Imax 处的值。
    早期版本取「|I|>0.2·Imax 的平均」，把轻载 655 µH 与满载 297 µH 混在一起平均，
    凸极率算成 2.01（正确值约 1.3）。
    """
    Id = np.asarray(m["Id_Peak"])[:, 0]
    Iq = np.asarray(m["Iq_Peak"])[0, :]
    Fd = np.asarray(m["Flux_Linkage_D"])
    Fq = np.asarray(m["Flux_Linkage_Q"])

    i0 = zero_index(Id)
    j0 = zero_index(Iq)
    lam_pm = float(Fd[i0, j0])

    imax = float(np.max(np.abs(Iq)))
    target = 0.7 * imax  # 额定/典型工况点

    # Lq：Id=0 截面上，取 |Iq| 最接近 target 的点
    def _lq_at(iq_target: float) -> float:
        j = int(np.argmin(np.abs(np.abs(Iq) - iq_target)))
        return float(Fq[i0, j] / Iq[j])

    # Ld：Iq=0 截面上，取 |Id| 最接近 target 的点
    def _ld_at(id_target: float) -> float:
        i = int(np.argmin(np.abs(np.abs(Id) - id_target)))
        return float((Fd[i, j0] - lam_pm) / Id[i])

    lq_rated = _lq_at(target)
    ld_rated = _ld_at(target)
    lq_sat = _lq_at(imax)
    ld_sat = _ld_at(imax)

    return lam_pm, ld_sat, lq_sat, ld_rated, lq_rated


# ---------------------------------------------------------------------------
# 2. 派生量计算
# ---------------------------------------------------------------------------


def compute_derived(p: MotorParams) -> None:
    """按 MathWorks 公式计算基速、MTPA 等。"""

    # SVPWM 线性区：相电压峰值 = Vdc/√3
    p.v_max_peak = p.vdc / np.sqrt(3)
    # 弱磁起点：磁链模值上限 |λ| ≤ vmax/ωe
    p.saliency = p.lq_h / p.ld_h if p.ld_h else 0.0

    # MTPA 解析解（MathWorks 公式，Lq > Ld）
    # id_mtpa = λpm/(4(Lq−Ld)) − sqrt( λpm²/(16(Lq−Ld)²) + im²/2 )
    d_l = p.lq_h - p.ld_h
    if d_l > 0:
        p.mtpa_id = (
            p.lam_pm / (4 * d_l)
            - np.sqrt(p.lam_pm**2 / (16 * d_l**2) + p.i_max**2 / 2)
        )
    else:
        p.mtpa_id = 0.0
    p.mtpa_iq = float(np.sqrt(max(p.i_max**2 - p.mtpa_id**2, 0.0)))

    # 转矩 T = 1.5·p·[λpm·iq + (Ld−Lq)·id·iq]
    def torque(i_d: float, i_q: float) -> float:
        return 1.5 * p.pole_pairs * (
            p.lam_pm * i_q + (p.ld_h - p.lq_h) * i_d * i_q
        )

    p.mtpa_torque = torque(p.mtpa_id, p.mtpa_iq)
    p.torque_id0 = torque(0.0, p.i_max)

    # 满载基速：ωbase = vmax / |λ| / p，|λ| = sqrt((Ld·id+λpm)² + (Lq·iq)²)
    lam_d = p.ld_h * p.mtpa_id + p.lam_pm
    lam_q = p.lq_h * p.mtpa_iq
    lam_mag = float(np.hypot(lam_d, lam_q))
    p.lambda_max = lam_mag
    omega_e = p.v_max_peak / lam_mag
    p.base_speed_rpm = omega_e / p.pole_pairs * 60 / (2 * np.pi)


# ---------------------------------------------------------------------------
# 3. 查表峰值搜索（用真实 ECE 数据，不依赖解析式）
# ---------------------------------------------------------------------------


def search_operating_points(m: dict, p: MotorParams) -> dict:
    """在 ECE 网格上搜 MTPA 最优点与各转速下的可达最大转矩。"""
    Id = np.asarray(m["Id_Peak"])[:, 0]
    Iq = np.asarray(m["Iq_Peak"])[0, :]
    T = np.asarray(m["Electromagnetic_Torque"])
    Fd = np.asarray(m["Flux_Linkage_D"])
    Fq = np.asarray(m["Flux_Linkage_Q"])

    # MTPA：电流圆内转矩最大
    best = None
    for i, idv in enumerate(Id):
        for j, iqv in enumerate(Iq):
            if np.hypot(idv, iqv) > p.i_max + 1e-6:
                continue
            if best is None or T[i, j] > best[0]:
                best = (float(T[i, j]), float(idv), float(iqv))
    mtpa_grid = {"torque": best[0], "id": best[1], "iq": best[2]}

    # 各转速：电压约束下的最大转矩
    by_speed = {}
    for rpm in (3000, 4000, 5000, 6000, 8000, 10000):
        omega_e = 2 * np.pi * rpm / 60 * p.pole_pairs
        lam_lim = p.v_max_peak / omega_e
        cand = None
        for i, idv in enumerate(Id):
            for j, iqv in enumerate(Iq):
                if np.hypot(idv, iqv) > p.i_max + 1e-6:
                    continue
                if np.hypot(Fd[i, j], Fq[i, j]) > lam_lim:
                    continue
                if cand is None or T[i, j] > cand[0]:
                    cand = (float(T[i, j]), float(idv), float(iqv))
        by_speed[rpm] = cand

    return {"mtpa_grid": mtpa_grid, "by_speed": by_speed}


# ---------------------------------------------------------------------------
# 4. 控制参数（PI 增益、采样率）
# ---------------------------------------------------------------------------


def compute_control_params(p: MotorParams, pwm_hz: float = 20000.0,
                           speed_loop_ratio: int = 30,
                           current_bandwidth_hz: float = 1000.0,
                           speed_bandwidth_hz: float = 30.0) -> dict:
    """按典型整定规则算 PI 增益。

    电流环（内环）采用「零极点对消 + 期望带宽」：
        Kp = ωc · L
        Ki = ωc · R
    其中 ωc = 2π·f_bw。

    转速环（外环）采用对称最佳或简化：Kp = J·ωs，Ki = Kp·ωs/5（典型经验）。
    """
    Ts = 1.0 / pwm_hz
    Ts_speed = speed_loop_ratio * Ts

    wc_i = 2 * np.pi * current_bandwidth_hz
    kp_d = wc_i * p.ld_h
    ki_d = wc_i * p.rs_ohm
    kp_q = wc_i * p.lq_h
    ki_q = wc_i * p.rs_ohm

    # 转速环：惯量暂取 0.01 kg·m²（占位，需实测）
    J = 0.01
    wc_s = 2 * np.pi * speed_bandwidth_hz
    kp_s = J * wc_s
    ki_s = kp_s * wc_s / 5

    return {
        "pwm_hz": pwm_hz,
        "Ts_current_s": Ts,
        "Ts_speed_s": Ts_speed,
        "current_bandwidth_hz": current_bandwidth_hz,
        "speed_bandwidth_hz": speed_bandwidth_hz,
        "Kp_d": kp_d,
        "Ki_d": ki_d,
        "Kp_q": kp_q,
        "Ki_q": ki_q,
        "Kp_speed": kp_s,
        "Ki_speed": ki_s,
        "note_inertia_assumed": J,
    }


# ---------------------------------------------------------------------------
# 输出
# ---------------------------------------------------------------------------


def print_report(p: MotorParams, grid: dict, ctrl: dict) -> None:
    w = 62
    print("=" * w)
    print(" e11 IPM 控制参数计算")
    print("=" * w)

    print("\n【1】电机基本参数")
    print(f"  极对数 p                = {p.pole_pairs}")
    print(f"  永磁磁链 λpm            = {p.lam_pm:.6f} Wb")
    print(f"  d 轴电感 Ld（额定点）   = {p.ld_h * 1e6:.1f} µH")
    print(f"  q 轴电感 Lq（额定点）   = {p.lq_h * 1e6:.1f} µH")
    print(f"  Ld（大电流饱和）        = {p.ld_sat_h * 1e6:.1f} µH")
    print(f"  Lq（大电流饱和）        = {p.lq_sat_h * 1e6:.1f} µH")
    print(f"  凸极率 Lq/Ld            = {p.saliency:.2f}")
    print(f"  每相电阻 Rs             = {p.rs_ohm * 1e3:.3f} mΩ")

    print("\n【2】电源与限值")
    print(f"  母线电压 Vdc            = {p.vdc:.0f} V")
    print(f"  SVPWM 相电压峰值 Vmax   = Vdc/√3 = {p.v_max_peak:.2f} V")
    print(f"  峰值电流上限 Imax       = {p.i_max:.0f} A")

    print("\n【3】MTPA（解析式）")
    print("  公式：id = λpm/(4(Lq−Ld)) − sqrt(λpm²/(16(Lq−Ld)²) + Imax²/2)")
    print(f"  id_mtpa                 = {p.mtpa_id:.2f} A")
    print(f"  iq_mtpa                 = {p.mtpa_iq:.2f} A")
    print(f"  转矩（解析）            = {p.mtpa_torque:.1f} N·m")
    print(f"  对照：id=0 时转矩       = {p.torque_id0:.1f} N·m")
    if p.torque_id0 > 0:
        print(f"  MTPA 增益               = {(p.mtpa_torque / p.torque_id0 - 1) * 100:.1f}%")

    print("\n【4】基速（满载）")
    print("  公式：ωbase = Vmax / |λ| / p，|λ| = sqrt((Ld·id+λpm)² + (Lq·iq)²)")
    print(f"  |λ|（MTPA 点）          = {p.lambda_max:.4f} Wb")
    print(f"  基速                    = {p.base_speed_rpm:.0f} rpm")

    print("\n【5】ECE 网格实测（不依赖解析式）")
    g = grid["mtpa_grid"]
    print(f"  MTPA 最优点：T={g['torque']:.1f} N·m @ Id={g['id']:.1f}, Iq={g['iq']:.1f}")
    print("  各转速可达最大转矩（含电压约束）：")
    for rpm, v in grid["by_speed"].items():
        if v is None:
            print(f"    {rpm:6d} rpm : 无可行点")
        else:
            print(f"    {rpm:6d} rpm : {v[0]:7.1f} N·m @ Id={v[1]:7.1f}, Iq={v[2]:7.1f}")

    print("\n【6】控制参数")
    print(f"  PWM 频率                = {ctrl['pwm_hz'] / 1e3:.0f} kHz")
    print(f"  电流环采样 Ts           = {ctrl['Ts_current_s'] * 1e6:.0f} µs")
    print(f"  速度环采样              = {ctrl['Ts_speed_s'] * 1e6:.0f} µs（{ctrl['Ts_speed_s']/ctrl['Ts_current_s']:.0f}×Ts）")
    print(f"  电流环带宽              = {ctrl['current_bandwidth_hz']:.0f} Hz")
    print(f"  速度环带宽              = {ctrl['speed_bandwidth_hz']:.0f} Hz")
    print("\n  电流环 PI（Kp = ωc·L，Ki = ωc·R）：")
    print(f"    Kp_d = {ctrl['Kp_d']:.6f}    Ki_d = {ctrl['Ki_d']:.4f}")
    print(f"    Kp_q = {ctrl['Kp_q']:.6f}    Ki_q = {ctrl['Ki_q']:.4f}")
    print("\n  转速环 PI（惯量占位 {:.3f} kg·m²，需实测替换）：".format(ctrl["note_inertia_assumed"]))
    print(f"    Kp_s = {ctrl['Kp_speed']:.6f}    Ki_s = {ctrl['Ki_speed']:.4f}")

    print("\n" + "=" * w)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="e11 控制参数计算")
    ap.add_argument("--mat", required=True, help="ECE 饱和图 MAT 路径")
    ap.add_argument("--json-out", help="把结果写成 JSON")
    ap.add_argument("--pwm-hz", type=float, default=20000.0, help="PWM 开关频率（默认 20 kHz）")
    ap.add_argument("--current-bw", type=float, default=1000.0, help="电流环带宽 Hz（默认 1000）")
    ap.add_argument("--speed-bw", type=float, default=30.0, help="速度环带宽 Hz（默认 30）")
    args = ap.parse_args(argv)

    mat = Path(args.mat)
    if not mat.is_absolute():
        mat = (PROJECT_ROOT / mat).resolve()

    m = load_ece(mat)
    lam_pm, ld_sat, lq_sat, ld_mid, lq_mid = derive_inductance(m)

    p = MotorParams()
    p.lam_pm = lam_pm
    p.ld_h = abs(ld_mid)
    p.lq_h = abs(lq_mid)
    p.ld_sat_h = abs(ld_sat)
    p.lq_sat_h = abs(lq_sat)
    compute_derived(p)

    grid = search_operating_points(m, p)
    ctrl = compute_control_params(p, args.pwm_hz, current_bandwidth_hz=args.current_bw,
                                  speed_bandwidth_hz=args.speed_bw)

    print_report(p, grid, ctrl)

    if args.json_out:
        out = Path(args.json_out)
        if not out.is_absolute():
            out = (PROJECT_ROOT / out).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "source_mat": str(mat),
            "motor": p.to_dict(),
            "grid_search": grid,
            "control": ctrl,
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已写出：{out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
