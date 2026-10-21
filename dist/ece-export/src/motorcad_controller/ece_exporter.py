"""ECE（等效电路提取）导出：Motor-CAD → Twin Builder 可导入的 SML / TXT / MAT 三件套。

对应设计 `docs/design/e11-control-model.md` §4。逻辑移植自官方示例
`help/repos/pymotorcad/examples/links/ece_export_for_twinbuilder.py`（779 行），差异有三处：

1. 参数改为构造期传入（官方从 `ece_config.json` 现读），便于单测；
2. 计算与写文件拆成独立函数，纯数据变换部分不碰 Motor-CAD，可离线测；
3. 对齐角与位置步长的推导抽成 `derive_grid`，返回 `GridPlan` 供日志与单测核对。

Motor-CAD 相关步骤全部经 `mc.set_variable` / `mc.get_variable`，不做 GUI 操作。
"""

from __future__ import annotations

import math
import string
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

# 官方脚本固定值：只取 120 电角度区间做查表（ece_export_for_twinbuilder.py:245）
MAX_ELEC_DEGREE = 120.0
# 每周期最少位置点数（ece_export_for_twinbuilder.py:244）
MIN_POINTS_PER_CYCLE = 30

# SML/TXT 一律 CRLF：Twin Builder 解析器与官方脚本写出的文件一致
CRLF = "\r\n"


class ECEExportError(Exception):
    """ECE 导出失败；消息写明阶段与原因，由入口脚本映射为退出码 1。"""


class ECEConfigError(Exception):
    """配置不可用（文件缺失 / JSON 非法 / 缺键 / 路径不存在）；入口脚本映射为退出码 2。

    单独一类是为了与导出失败区分：配置错误重试无意义，导出失败可能是环境问题。
    """


@dataclass(frozen=True)
class GridPlan:
    """由对齐角推导出的位置网格。官方脚本 :241-262 的等价结果。"""

    alignment_angle: float  # 90 + DriveOffsetAngleLoad（电角度）
    elec_step_deg: float  # 位置步长（电角度）
    points_per_cycle: int  # 360 / elec_step_deg
    mech_step_deg: float  # 机械角度步长 = elec_step_deg / 极对数
    map_points: int  # 120 电角度内的点数（含两端）

    def __str__(self) -> str:
        return (
            f"对齐角 {self.alignment_angle:.3f}° | 电角步长 {self.elec_step_deg:.3f}° | "
            f"每周期 {self.points_per_cycle} 点 | 机械步长 {self.mech_step_deg:.4f}° | "
            f"查表 {self.map_points} 点"
        )


@dataclass(frozen=True)
class ECERequest:
    """一次 ECE 提取的全部输入（对应官方 `ece_config.json` + 项目路径约定）。"""

    mot_path: Path  # 待计算的 MOT 副本（原文件不动）
    output_dir: Path  # 三件套落地目录
    base_name: str  # 产物名主干，如 "e11"
    shaft_speed: float  # rpm，开环反电势计算用
    dc_bus_voltage: float  # V
    machine_temp: float  # ℃，绕组/磁钢/轴统一取此温度
    id_max: float  # A（peak），饱和图 ±范围
    current_step: float  # A，饱和图电流步长

    @property
    def map_file(self) -> Path:
        return self.output_dir / f"ECE_{self.base_name}_map.mat"

    @property
    def txt_file(self) -> Path:
        return self.output_dir / f"ECE_{self.base_name}_txt_file.txt"

    @property
    def sml_file(self) -> Path:
        return self.output_dir / f"ECE_{self.base_name}_sml_file.sml"


# ---------------------------------------------------------------------------
# 纯计算：位置网格
# ---------------------------------------------------------------------------


def _factorize(value: float) -> list[int]:
    """整数因式分解；输入先四舍五入取整（官方 :246-254 的算法只对整数成立）。"""
    n = int(round(value))  # noqa: RUF046 - 显式取整：字段声明为 int，round 的返回型别对读者不确定
    factors: list[int] = []
    d = 2
    while n >= d:
        if n % d == 0:
            factors.append(d)
            n //= d
        else:
            d += 1
    return factors


def derive_grid(alignment_angle: float, pole_pairs: float) -> GridPlan:
    """由对齐角推位置步长与点数（官方 :241-262 的可读重写）。

    选步长的规则：取对齐角的最大质因数使 120/步长 不低于 30 点；不够则退到次大质因数。
    """
    factors = _factorize(alignment_angle)
    if not factors:
        raise ECEExportError(
            f"网格推导 | 对齐角 {alignment_angle} 无可用质因数 | 对齐角须为正整数（电角度）"
        )
    idx = len(factors) - 1
    elec_step = float(factors[idx])
    while (MAX_ELEC_DEGREE / elec_step) < MIN_POINTS_PER_CYCLE:
        idx -= 1
        if idx < 0:
            raise ECEExportError(
                f"网格推导 | 对齐角 {alignment_angle} 的全部质因数都使 120° 内点数 < {MIN_POINTS_PER_CYCLE}"
            )
        elec_step = float(factors[idx])

    if pole_pairs <= 0:
        raise ECEExportError(f"网格推导 | 极对数 {pole_pairs} 必须为正 | 取自 Pole_Number/2")

    return GridPlan(
        alignment_angle=float(alignment_angle),
        elec_step_deg=elec_step,
        points_per_cycle=int(round(360.0 / elec_step)),  # noqa: RUF046 - 同上
        mech_step_deg=elec_step / pole_pairs,
        map_points=int(MAX_ELEC_DEGREE / elec_step) + 1,
    )


# ---------------------------------------------------------------------------
# Motor-CAD 侧：计算并导出 MAT
# ---------------------------------------------------------------------------


def _set(mc: Any, name: str, value: Any) -> None:
    try:
        mc.set_variable(name, value)
    except Exception as exc:
        raise ECEExportError(f"设置 | {name} = {value!r} | {type(exc).__name__}: {exc}") from exc


def _get(mc: Any, name: str) -> Any:
    try:
        return mc.get_variable(name)
    except Exception as exc:
        raise ECEExportError(f"读取 | {name} | {type(exc).__name__}: {exc}") from exc


def ensure_airgap_mesh(mc: Any) -> bool:
    """确保气隙划分网格已开；返回是否由本函数改动。

    背景（实测）：e11 的 `.mot` 里 `AnsysAirgapMesh=0`（`models/motorcad/e11_User.mot:78` 附近的
    Ansys 段），此时带转子旋转的 FEA 会报
    `Execution error/Mesh17:IntRadius and ExtRadius must be defined if air_gap is not meshed`
    与 `MeshRotate: (UEM) Undefined airgap region`，饱和图整体失效
    （证据：`results/e11-ece/work/e11_User/MessageLogs/messageLog_60804.txt` 21:34:34 起连续报错）。
    这也是 `AGENTS.md` 记录的已知约束「`AnsysAirgapMesh=1` 必须开」。
    只读 `.mot` 不改原文件，故此处对副本强制打开并回读确认。
    """
    current = _get(mc, "AnsysAirgapMesh")
    if int(current) == 1:
        return False
    _set(mc, "AnsysAirgapMesh", 1)
    if int(_get(mc, "AnsysAirgapMesh")) != 1:
        raise ECEExportError(
            f"气隙网格 | AnsysAirgapMesh | 设为 1 并回读为 1 | 回读 {_get(mc, 'AnsysAirgapMesh')}"
        )
    return True


def run_back_emf(mc: Any, req: ECERequest, points_per_cycle: int) -> float:
    """开环反电势计算，返回对齐角（90 + 驱动补偿角）。官方 :149-226。"""
    _set(mc, "TorquePointsPerCycle", points_per_cycle)
    _set(mc, "ShaftSpeed", req.shaft_speed)
    _set(mc, "CurrentDefinition", 0)  # Peak
    _set(mc, "PeakCurrent", 0)
    _set(mc, "DCBusVoltage", req.dc_bus_voltage)
    _set(mc, "ArmatureConductor_Temperature", req.machine_temp)
    _set(mc, "Magnet_Temperature", req.machine_temp)
    _set(mc, "Shaft_Temperature", req.machine_temp)
    _set(mc, "MagneticThermalCoupling", 0)
    _set(mc, "BackEMFCalculation", True)
    _set(mc, "CoggingTorqueCalculation", False)
    _set(mc, "TorqueCalculation", False)
    _set(mc, "TorqueSpeedCalculation", False)

    try:
        mc.do_magnetic_calculation()
    except Exception as exc:
        raise ECEExportError(f"反电势计算 | do_magnetic_calculation | {type(exc).__name__}: {exc}") from exc

    # 读取 A 相开路磁链，作为计算确实跑过的证据（官方 :204）
    try:
        e_deg, flux_a = mc.get_magnetic_graph("FluxLinkageOCPh1")
    except Exception as exc:
        raise ECEExportError(f"反电势结果 | FluxLinkageOCPh1 图 | {type(exc).__name__}: {exc}") from exc
    if len(e_deg) < 2 or len(flux_a) < 2:
        raise ECEExportError(f"反电势结果 | FluxLinkageOCPh1 点数 {len(e_deg)} | 少于 2 点，计算未产出")

    drive_offset = float(_get(mc, "DriveOffsetAngleLoad"))
    return 90.0 + drive_offset


def _check_grid_contains_zero(req: ECERequest) -> None:
    """网格必须含 Id = 0 与 Iq = 0（本地先判，免得起完 Motor-CAD 才被拒）。

    实测：Motor-CAD 对不含 Id=0 的网格直接报
    `Saturation and Loss Map Export requires a point at Id = 0`。

    判据不靠「段数奇偶」这种间接推算，直接按 Motor-CAD 的取点规则
    （Min 起步、按 Step 累加、不超过 Max）算出实际网格再查有没有 0：
    `id_max=433、step=45.5789`（原先的 20 点方案）算出来也是整数段，
    但 433/45.5789 除不尽，0 落在两个格点之间——Motor-CAD 实测拒绝。
    反例 `step=108.25` 恰好整除，0 落在第 5 点（−433 + 4×108.25 = 0），可以通过。
    """
    min_i, max_i, step = -req.id_max, req.id_max, req.current_step
    if step <= 0:
        raise ECEExportError(f"电流网格 | 步长 {step} | 正数 | 步长须为正")
    n_steps = round((max_i - min_i) / step)
    points = [min_i + k * step for k in range(n_steps + 1)]
    has_zero = any(abs(p) < 1e-9 * max(1.0, abs(max_i)) for p in points)
    if not has_zero:
        raise ECEExportError(
            f"电流网格 | 取样 {points[0]:.3f}..{points[-1]:.3f} 步长 {step} | 含 Id = 0 | "
            f"0 A 不落在网格点上（步长须整除 2·id_max 且段数为偶数）"
        )


def run_saturation_map(mc: Any, req: ECERequest, grid: GridPlan,
                       poll_interval_s: float = 15.0, timeout_s: float = 4 * 3600.0) -> None:
    """D/Q 电流扫描饱和图计算，结果写 req.map_file。官方 :264-315。

    `CalculateSaturationMap` 在 Motor-CAD 里是**启动即返回**的异步调用：它设
    `SaturationMapRunning=True` 后立刻回一个「Lab is already running」的错误——那是「已启动」的回执，
    不是失败（实测：`results/e11-ece/work/e11_User/MessageLogs/` 里 21:33:41 设该标志、
    21:33:47 起全核求解）。因此这里不把该错误当失败。
    改为轮询 `SaturationMapRunning` 直到转 False，再看 `SaturationMap_CalculationComplete`
    与导出文件是否存在来判定成败。
    """
    _check_grid_contains_zero(req)

    _set(mc, "TorquePointsPerCycle", grid.points_per_cycle)
    _set(mc, "SaturationMap_ExportFile", str(req.map_file))
    _set(mc, "SaturationMap_InputDefinition", 1)  # D/Q Axis Currents
    _set(mc, "SaturationMap_CalculationMethod", 1)  # FEA
    _set(mc, "SaturationMap_FEACalculationType", 1)  # Full Cycle
    _set(mc, "SaturationMap_ResultType", 1)  # Varying with rotor position
    _set(mc, "LossMap_Export", False)
    _set(mc, "SaturationMap_Current_D_Max", req.id_max)
    _set(mc, "SaturationMap_Current_D_Step", req.current_step)
    _set(mc, "SaturationMap_Current_D_Min", -req.id_max)
    _set(mc, "SaturationMap_Current_Q_Max", req.id_max)
    _set(mc, "SaturationMap_Current_Q_Step", req.current_step)
    _set(mc, "SaturationMap_Current_Q_Min", -req.id_max)

    try:
        started_at = time.time()  # 用于判断 MAT 是不是本次产出的
        mc.calculate_saturation_map()
    except Exception as exc:
        # 「Lab is already running」= 已启动；其余错误才算失败
        if "already running" not in str(exc).lower():
            raise ECEExportError(
                f"饱和图计算 | calculate_saturation_map | {type(exc).__name__}: {exc}"
            ) from exc

    # 等计算结束：只认 `SaturationMap_CalculationComplete`
    # 不靠 `SaturationMapRunning`——实测它在本环境里从不清位为 True，而 Motor-CAD 日志同时在逐点求解，
    # 拿它做启动判据会把等待变成死等。
    #
    # 单次读取失败不中止：FEA 正在跑时 RPC 偶尔会短暂读不到值，而一旦这里抛出，
    # 一次已跑了数分钟的饱和图就被丢掉。只有**连续**失败到超时才判失败。
    deadline = time.monotonic() + timeout_s
    last_err: Exception | None = None
    while time.monotonic() < deadline:
        try:
            if _get(mc, "SaturationMap_CalculationComplete"):
                last_err = None
                break
            last_err = None
        except ECEExportError as exc:
            last_err = exc
        time.sleep(poll_interval_s)

    if last_err is not None:
        raise ECEExportError(f"饱和图计算 | 轮询完成标志 | 能读到 SaturationMap_CalculationComplete | {last_err}")
    if not _get(mc, "SaturationMap_CalculationComplete"):
        raise ECEExportError(
            f"饱和图计算 | SaturationMap_CalculationComplete | 为真 | "
            f"等待 {timeout_s / 3600:.1f} h 后仍未完成"
        )

    if not req.map_file.is_file():
        raise ECEExportError(f"饱和图结果 | 期望 {req.map_file} | 计算完成但文件不存在")
    if req.map_file.stat().st_mtime < started_at:
        raise ECEExportError(
            f"饱和图结果 | {req.map_file} | 本次运行产出（mtime ≥ 启动时刻） | "
            f"文件时间早于本次启动，是上一次运行的残留"
        )


# ---------------------------------------------------------------------------
# 纯数据：MAT → 查找表
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LookupTable:
    """ECE 查表数据，全部为扁平数组（官方 final_table 的等价结构）。"""

    index: np.ndarray
    flux_d: np.ndarray
    flux_q: np.ndarray
    flux_0: np.ndarray
    torque: np.ndarray
    id: np.ndarray
    iq: np.ndarray
    phase_advance: np.ndarray
    rotor_pos: np.ndarray

    def rows(self) -> int:
        return int(self.index.size)


def build_lookup(mat: dict[str, Any], grid: GridPlan) -> LookupTable:
    """把 Motor-CAD 导出的饱和图展平成查表。官方 :347-400 的等价重写。

    环形回绕按**周期**取模，不按样本数：Motor-CAD 的 `Angular_*` 数组给的是 0..360 含首尾，
    末点是首点的重复（e11 实测 121 个样本 / 120 个周期步）。若用样本数 121 做模数，
    `-1 % 121 = 120` 会落到 360° 那个重复样本上，与官方的 `points_per_cycle + k` 取到的
    周期内起点不是同一个物理角。因此这里用 `grid.points_per_cycle` 做模数。
    """
    required = (
        "Id_Peak", "Iq_Peak", "Angular_Flux_Linkage_D", "Angular_Flux_Linkage_Q",
        "Angular_Rotor_Position", "Angular_Electromagnetic_Torque", "Phase_Advance",
    )
    missing = [k for k in required if k not in mat]
    if missing:
        raise ECEExportError(f"查表构建 | MAT 缺键 {missing} | 键清单 {sorted(mat)}")

    id_peak = np.asarray(mat["Id_Peak"], dtype=float)
    iq_peak = np.asarray(mat["Iq_Peak"], dtype=float)
    flux_d = np.asarray(mat["Angular_Flux_Linkage_D"], dtype=float)
    flux_q = np.asarray(mat["Angular_Flux_Linkage_Q"], dtype=float)
    torque = np.asarray(mat["Angular_Electromagnetic_Torque"], dtype=float)
    rot_pos = np.asarray(mat["Angular_Rotor_Position"], dtype=float)
    phase_adv = np.asarray(mat["Phase_Advance"], dtype=float)

    d_values, q_values = id_peak.shape
    n_pos = flux_d.shape[2]
    period = grid.points_per_cycle
    # 样本数须覆盖一个完整周期；含首尾时样本数恰好比周期多 1
    if n_pos < period:
        raise ECEExportError(
            f"查表构建 | 位置样本数 {n_pos} | 不少于一个周期的 {period} 点 | 饱和图未覆盖满周期"
        )

    skip = int(math.ceil(grid.alignment_angle / grid.elec_step_deg))  # noqa: RUF046 - 供切片与 log 当整数用
    # 官方从 skip 起往前取 map_points 个点，负索引按周期回绕
    raw = np.arange(skip, skip - grid.map_points, -1)
    pos_idx = raw % period

    idx = []
    out = {k: [] for k in ("fd", "fq", "tq", "idd", "iqq", "pa", "rp")}
    counter = 0
    for i in range(d_values):
        for j in range(q_values):
            for k in pos_idx:
                idx.append(counter)
                counter += 1
                out["fd"].append(flux_d[i, j, k])
                out["fq"].append(flux_q[i, j, k])
                out["tq"].append(-torque[i, j, k])  # 官方取负：ECE 侧转矩正方向相反（:382）
                out["idd"].append(id_peak[i, j])
                out["iqq"].append(iq_peak[i, j])
                out["pa"].append(phase_adv[i, j])
                out["rp"].append(rot_pos[i, j, k])

    return LookupTable(
        index=np.asarray(idx, dtype=int),
        flux_d=np.asarray(out["fd"]),
        flux_q=np.asarray(out["fq"]),
        flux_0=np.zeros(len(idx)),
        torque=np.asarray(out["tq"]),
        id=np.asarray(out["idd"]),
        iq=np.asarray(out["iqq"]),
        phase_advance=np.asarray(out["pa"]),
        rotor_pos=np.asarray(out["rp"]),
    )


# ---------------------------------------------------------------------------
# 纯数据：写 TXT / SML
# ---------------------------------------------------------------------------


def _safe_name(raw: str) -> str:
    """产物名主干只留 ASCII 字母数字与下划线。

    官方（:497-498）只保留字母数字，e11_20x20 会被压成 e1120x20，多份网格
    的模型名难以区分。下划线是 Twin Builder 模型名的合法字符，保留它。
    """
    stem = raw.rsplit(".", 1)[0] if "." in raw else raw
    allowed = string.ascii_letters + string.digits + "_"
    name = "".join(ch for ch in stem if ch in allowed)
    if not name:
        raise ECEExportError(f"产物命名 | 输入 {raw!r} | 去非字母数字后为空")
    return name


def write_txt(path: Path, table: LookupTable, grid: GridPlan, pole_pairs: float,
              phase_res: float, phase_l: float) -> None:
    """写 TXT 查表。官方 :462-514。"""
    d_vals = np.unique(table.id)
    q_vals = np.unique(table.iq)
    lines = [
        "B_BasicData",
        "\tVersion\t1.1",
        f"\tPoles\t{pole_pairs * 2:.0f}",
        "E_BasicData",
        "",
        "B_PhaseImp 3",
        f"\tWG_Ph1\t{phase_res:.10e}\t{phase_l:.10e}",
        f"\tWG_Ph2\t{phase_res:.10e}\t{phase_l:.10e}",
        f"\tWG_Ph3\t{phase_res:.10e}\t{phase_l:.10e}",
        "E_PhaseImp",
        "",
        "B_Sweepings",
        "",
        f"\tId_Iq\t( {d_vals.size} :" + "".join(f"\t{v}" for v in d_vals) + ")",
        f"\t\t( {q_vals.size} :" + "".join(f"\t{v}" for v in q_vals) + ")",
        f"\tRotate\t( {grid.map_points} :" + "".join(
            f"\t{i * grid.mech_step_deg:.3f}" for i in range(grid.map_points)
        ) + ")",
        "E_Sweepings",
        "",
        "B_OutputMatrix DQ0",
    ]
    for n in range(table.rows()):
        lines.append(
            f"\t{table.index[n]}\t{table.flux_d[n]:.10e}\t{table.flux_q[n]:.10e}"
            f"\t{table.flux_0[n]:.10e}\t{table.torque[n]:.10e}"
        )
    lines.append("E_OutputMatrix")
    path.write_text(CRLF.join(lines) + CRLF, encoding="ascii", newline="")


def write_sml(path: Path, table: LookupTable, grid: GridPlan, pole_pairs: float,
              phase_res: float, phase_l: float, model_name: str) -> None:
    """写 Twin Builder 模型定义。官方 :516-707，逐行对齐。"""
    name = model_name
    out: list[str] = []

    def w(s: str = "") -> None:
        out.append(s)

    w(f"MODELDEF ECE_{name}")
    w("{")
    for port in ("A0", "X0", "B0", "Y0", "C0", "Z0"):
        w(f"PORT electrical: {port};")
    w("PORT ROTATIONAL_V: ROT1;")
    w("PORT ROTATIONAL_V: ROT2;")
    w(f"PORT REAL IN: ra0 = {phase_res:.3f};")
    w(f"PORT REAL IN: la0 = {phase_l:.0e};")
    w("PORT REAL IN: IniIa0 = 0;")
    w("PORT REAL IN: IniIb0 = 0;")
    w("PORT REAL IN: IniIc0 = 0;")
    w("PORT REAL OUT: Fluxa0 = AM_Fluxa0.I;")
    w("PORT REAL OUT: Fluxb0 = AM_Fluxb0.I;")
    w("PORT REAL OUT: Fluxc0 = AM_Fluxc0.I;")
    w("PORT REAL OUT: Fluxd0 = AMFd.I;")
    w("PORT REAL OUT: Fluxq0 = AMFq.I;")
    w("PORT REAL IN ANGLE[deg]: IniPos = 0;")
    w("PORT REAL OUT ANGLE[deg]: Pos = VM_Mdeg.V;")
    w("")

    # 三相绕组：R → L → AM 串联到相端，EV 注入反电势；另一支路 L-VM-AM 复制该相电流，
    # 再由 II 受控电流源把 d/q/0 磁链按各自角度投影注入。节点编号逐条对齐官方 :587-641。
    #   节点号：(R 出口, L 出口, AM 出口, VM 支路入口, AM_Flux 入口)
    phases = (
        ("a", "A0", "X0", "", 1, 2, 3, 4, 5),
        ("b", "B0", "Y0", "-2*PI/3", 6, 7, 8, 9, 10),
        ("c", "C0", "Z0", "-4*PI/3", 11, 12, 13, 14, 15),
    )
    for ph, hi, lo, shift, n_r, n_l, n_am, n_vm, n_fx in phases:
        w(f"INTERN  R        R{ph}0  N1:={hi}, N2:=N_{n_r}  ( R:=ra0 );")
        w(f"INTERN  L        L{ph}0  N1:=N_{n_r}, N2:=N_{n_l}  ( L:=la0, I0:=IniI{ph}0 );")
        w(f"INTERN  AM       AM{ph}0  N1:=N_{n_l}, N2:=N_{n_am}  ;")
        w(f"INTERN  EV       Em{ph}0  N1:=N_{n_am}, N2:={lo}  ( QUANT:=VM{ph}0.V, FACT:=-1 );")
        w(f"INTERN  L        Lm{ph}0  N1:=N_{n_vm}, N2:=GND  ( L:=1 );")
        w(f"INTERN  VM       VM{ph}0  N1:=N_{n_vm}, N2:=GND  ;")
        w(f"INTERN  AM       AM_Flux{ph}0  N1:=N_{n_fx}, N2:=N_{n_vm}  ;")
        w(f"INTERN  II       Flux{ph}d  N1:=GND, N2:=N_{n_fx}"
          f"  ( QUANT:=AMFd.I, FACT:=cos(VM_Erad.V{shift}) );")
        w(f"INTERN  II       Flux{ph}q  N1:=GND, N2:=N_{n_fx}"
          f"  ( QUANT:=AMFq.I, FACT:=sin(VM_Erad.V{shift}) );")
        w(f"INTERN  II       Flux{ph}o  N1:=GND, N2:=N_{n_fx}  ( QUANT:=AMFo.I, FACT:=1 );")
        w(f"INTERN  II       Flux{ph}0  N1:=GND, N2:=N_{n_fx}  ( QUANT:=AMo.I, FACT:=0 );")
        w("")

    w("INTERN  AM       AMFd  N1:=N_16, N2:=GND  ;")
    w("INTERN  AM       AMFq  N1:=N_17, N2:=GND  ;")
    w("INTERN  AM       AMFo  N1:=N_18, N2:=GND  ;")
    w("")
    w("")

    # Park 变换：三相电流 → d/q/0（Id0/Id1/Id2 按 a/b/c 相排列，编号是序数不是相名）
    for i, (ph, fn, sh) in enumerate((("a", "cos", ""), ("b", "cos", "-2*PI/3"),
                                      ("c", "cos", "-4*PI/3"))):
        w(f"INTERN  II       Id{i}  N1:=GND, N2:=N_19"
          f"  ( QUANT:=AM{ph}0.I, FACT:=2/3*{fn}(VM_Erad.V{sh}) );")
    w("INTERN  AM       AM0  N1:=N_19, N2:=GND  ;")
    for i, (ph, fn, sh) in enumerate((("a", "sin", ""), ("b", "sin", "-2*PI/3"),
                                      ("c", "sin", "-4*PI/3"))):
        w(f"INTERN  II       Iq{i}  N1:=GND, N2:=N_20"
          f"  ( QUANT:=AM{ph}0.I, FACT:=2/3*{fn}(VM_Erad.V{sh}) );")
    w("INTERN  AM       AM1  N1:=N_20, N2:=GND  ;")
    for i, ph in enumerate("abc"):
        w(f"INTERN  II       I0{i}  N1:=GND, N2:=N_21  ( QUANT:=AM{ph}0.I, FACT:=1/3 );")
    w("INTERN  AM       AMo  N1:=N_21, N2:=GND  ;")
    w("")
    # 机械落点：Gx 把转速(V=rad/s)换成 deg/s，Cx 积分成机械角，Ipos→AM2→Rpos(0.0174533·p) 得电角度。
    # Rpos 的阻值 p·π/180 正是「机械角 × 极对数 → 电角度(rad)」的比例。

    # 机械：转速 → 角度积分 → 电角度（Rpos = p·π/180）
    w("INTERN  VM       VM_Speed  N1:=N_23, N2:=N_22  ;")
    w('UMODEL  D2D      D2D1 N1:=N_23, N2:=ROT1 ( NATURE_1:="electrical",'
      ' NATURE_2:="Rotational_V" ) SRC: DLL( File:="Domains.dll");')
    w('UMODEL  D2D      D2D2 N1:=N_22, N2:=ROT2 ( NATURE_1:="electrical",'
      ' NATURE_2:="Rotational_V" ) SRC: DLL( File:="Domains.dll");')
    w("INTERN  IV       Gx  N1:=GND, N2:=N_24  ( QUANT:=VM_Speed.V, FACT:=57.29578 );")
    w("INTERN  C        Cx  N1:=N_24, N2:=GND  ( C:=1, V0:=IniPos );")
    w("INTERN  VM       VM_Mdeg  N1:=N_24, N2:=GND  ;")
    w("INTERN  IV       Ipos  N1:=GND, N2:=N_25  ( QUANT:=VM_Mdeg.V, FACT:=1 );")
    w("INTERN  AM       AM2  N1:=N_25, N2:=N_26  ;")
    w(f"INTERN  R        Rpos  N1:=N_26, N2:=GND  ( R:={0.0174533 * pole_pairs:.7f} );")
    w("INTERN  VM       VM_Erad  N1:=N_26, N2:=GND  ;")
    w("")
    # 查表数据源：3 个输入（d 电流 AM0.I、q 电流 AM1.I、机械角 AM2.I），4 个输出
    # NDSRC 的三段必须用续行符 `\ ` 连成一条记录（官方 :666-672）：
    # 模型定义、QUANT/SRC 头、TableData 内容是同一个语句的三段，
    # 缺了续行符就成了三个残句，Twin Builder 编译必然失败（Import Components 显示 Failed、0 compiled）。
    w(f"INTERN  NDSRC    PECE_{name}  N0:=GND, N1:=N_16, N2:=GND, N3:=N_17,"
      f" N4:=GND, N5:=N_18, N6:=N_22, N7:=N_23 \\ ")
    w(" ( QUANT:={ AM0.I, AM1.I, AM2.I }, SRC:={ isrc, isrc, isrc, isrc }, TableData:=\"\\ ")
    # 表体整段接在 TableData 之后，末尾带续行符，再由下一行收尾（官方 :700-701）
    w(f".MODEL ECE_{name}_table pwl TABLE=({_pwl_body(table, grid)}) LINEAR LINEAR PERIODIC\\ ")
    w(' DEEPSPLINE" );')
    w("}")
    path.write_text(CRLF.join(out) + CRLF, encoding="ascii", newline="")


def _pwl_body(table: LookupTable, grid: GridPlan) -> str:
    r"""拼 pwl 表体。官方 `ece_export_for_twinbuilder.py:665-705`，逐段对齐。

    结构：3 层嵌套（Id × Iq × 位置）。每层先声明本层点数与本层坐标，再一个 `0` 结束该层；
    最内层声明 `4`，随后依次列出 4 个输出量数组——对应 final_table 的第 1..4 行：
    Ψd / Ψq / Ψ0（恒 0）/ 转矩——对应官方 final_table 的第 1..4 行（第 0 行是索引，不写进表）。

    **每个电流对只取自己那 `map_points` 个位置点**。查表是扁平数组，行序为
    (Id, Iq, 位置)，故第 p 个电流对的切片是 `[p*map_points : (p+1)*map_points]`。
    早期版本在这里写成整列，表里填了 `d*q` 倍的数据（8×8 实测 1,079,957 个数字，
    官方只有 17,237 个），Twin Builder 导入直接报 action failed。

    续行记号为 `逗号 + 反斜杠 + 空格 + 换行`（官方每段写 `"\ \n"`，末尾逗号已在上一行），
    Twin Builder 靠反斜杠续行；写法与官方逐字节一致。
    """
    d_vals = np.unique(table.id)
    q_vals = np.unique(table.iq)
    mp = grid.map_points
    out: list[str] = []

    out.append(f" {d_vals.size},")
    out.extend(f" {v}," for v in d_vals)
    out.append("\\ " + CRLF + " 0,")

    pair = 0  # 第几个电流对，决定切片起点
    for _ in range(d_vals.size):
        out.append(f" {q_vals.size},")
        out.extend(f" {v}," for v in q_vals)
        out.append("\\ " + CRLF + " 0,")
        for _q in range(q_vals.size):
            out.append(f" {mp},")
            out.extend(f" {i * grid.mech_step_deg:.3f}," for i in range(mp))
            out.append("\\ " + CRLF + " 4,")
            lo = pair * mp
            hi = lo + mp
            last_pair = pair == d_vals.size * q_vals.size - 1
            for ci, col in enumerate((table.flux_d, table.flux_q, table.flux_0, table.torque)):
                out.extend(f" {v:.6f}," for v in col[lo:hi])
                # 官方最后一列之后直接接 ") LINEAR LINEAR PERIODIC"，不补续行（:700）
                if not (last_pair and ci == 3):
                    out.append("\\ " + CRLF)
            pair += 1

    return "".join(out)


def export_ece(mc: Any, req: ECERequest) -> dict[str, Any]:
    """完整 ECE 导出：反电势 → 饱和图 → 查表 → TXT + SML。返回摘要供日志与验收。"""
    req.output_dir.mkdir(parents=True, exist_ok=True)

    airgap_fixed = ensure_airgap_mesh(mc)

    pole_pairs = float(_get(mc, "Pole_Number")) / 2.0
    if pole_pairs <= 0:
        raise ECEExportError(f"电机参数 | Pole_Number = {_get(mc, 'Pole_Number')} | 极对数须为正")

    # 对齐角要靠反电势算出来，而位置步长又要靠对齐角推导——所以这一环本身就是两轮：
    # ① 先用 30 点/周期的下限跑一次反电势，拿到 DriveOffsetAngleLoad；
    # ② 由它推出正式网格，再按 grid.points_per_cycle 重跑一次反电势。
    # 官方脚本只做 ①（`ece_export_for_twinbuilder.py:296` 之后并未回写该设置），
    # 结果 OPEN_CIRCUIT 结果仍停在 30 点分辨率。这里补做 ②，让反电势结果与饱和图同分辨率。
    alignment = run_back_emf(mc, req, MIN_POINTS_PER_CYCLE)
    grid = derive_grid(alignment, pole_pairs)
    alignment_note = ""

    if grid.points_per_cycle != MIN_POINTS_PER_CYCLE:
        # 重跑时对齐角应保持不变；变了说明第一次算得不稳，按新的再推一次网格
        alignment2 = run_back_emf(mc, req, grid.points_per_cycle)
        if abs(alignment2 - alignment) > 1e-6:
            alignment_note = f"对齐角二次计算有变化：{alignment:.4f} → {alignment2:.4f}，网格按新值推导"
            grid = derive_grid(alignment2, pole_pairs)

    phase_res = float(_get(mc, "ArmatureWindingResistancePh"))
    phase_l = float(_get(mc, "EndWdgInductance_Used"))
    if phase_res <= 0:
        raise ECEExportError(f"电机参数 | ArmatureWindingResistancePh = {phase_res} | 须为正（反电势计算应已刷新）")
    if phase_l < 0:
        raise ECEExportError(f"电机参数 | EndWdgInductance_Used = {phase_l} | 不得为负")

    try:
        mc.save_to_file(str(req.mot_path))
    except Exception as exc:
        raise ECEExportError(f"保存 | {req.mot_path} | {type(exc).__name__}: {exc}") from exc

    run_saturation_map(mc, req, grid)

    try:
        from scipy import io as sio
        mat = sio.loadmat(str(req.map_file))
    except Exception as exc:
        raise ECEExportError(f"读取饱和图 | {req.map_file} | {type(exc).__name__}: {exc}") from exc

    table = build_lookup(mat, grid)
    name = _safe_name(req.base_name)
    write_txt(req.txt_file, table, grid, pole_pairs, phase_res, phase_l)
    write_sml(req.sml_file, table, grid, pole_pairs, phase_res, phase_l, name)

    return {
        "airgap_fixed": airgap_fixed,
        "alignment_note": alignment_note,
        "grid": grid,
        "rows": table.rows(),
        "phase_res": phase_res,
        "phase_l": phase_l,
        "pole_pairs": pole_pairs,
        "map_file": req.map_file,
        "txt_file": req.txt_file,
        "sml_file": req.sml_file,
    }
