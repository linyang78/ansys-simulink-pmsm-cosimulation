"""命令行入口：从 Motor-CAD 导出 e11 的 ECE 模型（SML / TXT / MAT 三件套）。

对应设计 `docs/design/e11-control-model.md` §4（ECE 提取流程）与 §4.5（.mot 只读，先复制再算）。

用法：
    python scripts/run_ece_export.py --config config/cases/e11_ece_config.json
    python scripts/run_ece_export.py --config ... --dry-run     # 只校验配置与路径

流程（对应官方 ece_export_for_twinbuilder.py）：
    复制 .mot 副本 → 连 Motor-CAD → 开环反电势拿对齐角 → 推导位置网格
    → 读相电阻/端部电感 → D/Q 饱和图计算 → MAT 展平成查表 → 写 TXT + SML

原 `.mot` 全程只读：脚本只在副本上做 `save_to_file`（设计 §4.5「必须用副本」）。
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from motorcad_controller.ece_exporter import (
    ECEConfigError,
    ECEExportError,
    ECERequest,
    export_ece,
)

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_CONFIG = 2
EXIT_MOTORCAD = 3

REQUIRED_KEYS = (
    "mot_source", "base_name", "output_dir",
    "shaft_speed", "dc_bus_voltage", "machine_temp", "id_max", "current_step",
)


def _log(msg: str = "") -> None:
    print(msg, flush=True)


def load_request(cfg_path: Path) -> tuple[ECERequest, Path]:
    """读 JSON 配置并解析成 `ECERequest`。相对路径按配置文件所在目录解析。"""
    if not cfg_path.is_file():
        raise ECEConfigError(f"配置 | {cfg_path} | 文件存在 | 不存在")
    try:
        raw = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ECEConfigError(f"配置 | {cfg_path} | 合法 JSON | {type(exc).__name__}: {exc}") from exc

    missing = [k for k in REQUIRED_KEYS if k not in raw]
    if missing:
        raise ECEConfigError(f"配置 | {cfg_path} | 含全部必需键 | 缺 {missing}")

    base = cfg_path.parent
    mot_source = (base / raw["mot_source"]).resolve()
    output_dir = (base / raw["output_dir"]).resolve()
    if not mot_source.is_file():
        raise ECEConfigError(f"配置 | mot_source | 指向存在的 .mot | {mot_source} 不存在")

    work_dir = output_dir / "work"
    return ECERequest(
        mot_path=work_dir / mot_source.name,
        output_dir=output_dir,
        base_name=str(raw["base_name"]),
        shaft_speed=float(raw["shaft_speed"]),
        dc_bus_voltage=float(raw["dc_bus_voltage"]),
        machine_temp=float(raw["machine_temp"]),
        id_max=float(raw["id_max"]),
        current_step=float(raw["current_step"]),
    ), mot_source


def connect_motorcad():
    """连接已在运行的 Motor-CAD；没有就起新实例。"""
    try:
        import ansys.motorcad.core as pymotorcad
    except ImportError as exc:
        raise ECEExportError(f"连接 | ansys.motorcad.core | 可导入 | {exc}") from exc

    errors = []
    for open_new in (False, True):
        try:
            mc = pymotorcad.MotorCAD(open_new_instance=open_new)
            _log(f"已连接 Motor-CAD（open_new_instance={open_new}）")
            return mc
        except Exception as exc:  # noqa: BLE001
            errors.append(f"open_new_instance={open_new}: {exc}")
    raise ECEExportError("连接 | Motor-CAD 实例 | 可连上 | " + " ；".join(errors))


def prepare_work_copy(req: ECERequest, mot_source: Path) -> None:
    """把原 `.mot` 复制到工作目录；原文件永不写。"""
    req.mot_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copyfile(mot_source, req.mot_path)
    except OSError as exc:
        raise ECEExportError(f"复制 | {mot_source} → {req.mot_path} | 可复制 | {exc}") from exc


def run(args: argparse.Namespace) -> int:
    cfg_path = Path(args.config).resolve()
    try:
        req, mot_source = load_request(cfg_path)
    except ECEConfigError as exc:
        _log(f"[配置失败] {exc}")
        return EXIT_CONFIG

    _log(f"配置：{cfg_path}")
    _log(f"  源模型  {mot_source}")
    _log(f"  工作副本 {req.mot_path}")
    _log(f"  产物目录 {req.output_dir}")
    _log(f"  工况    {req.shaft_speed:.0f} rpm / {req.dc_bus_voltage:.0f} V / {req.machine_temp:.0f} ℃")
    _log(f"  电流网格 ±{req.id_max:.0f} A，步长 {req.current_step:.2f} A"
         f"（约 {int(2 * req.id_max / req.current_step) + 1} 点/轴）")

    if args.dry_run:
        _log("dry-run：配置与路径已校验，不连 Motor-CAD、不计算")
        return EXIT_OK

    try:
        mc = connect_motorcad()
        mc.set_variable("MessageDisplayState", 2)
    except ECEExportError as exc:
        _log(f"[Motor-CAD 失败] {exc}")
        return EXIT_MOTORCAD

    try:
        prepare_work_copy(req, mot_source)
        _log("已复制工作副本（原文件不动）")
        try:
            mc.load_from_file(str(req.mot_path))
        except Exception as exc:
            raise ECEExportError(f"载入 | {req.mot_path} | 能载入 Motor-CAD | {exc}") from exc

        t0 = time.monotonic()
        summary = export_ece(mc, req)
        elapsed = time.monotonic() - t0
    except ECEExportError as exc:
        _log(f"[导出失败] {exc}")
        return EXIT_FAIL

    grid = summary["grid"]
    _log()
    _log(f"导出完成，用时 {elapsed / 60:.1f} min")
    _log(f"  网格     {grid}")
    _log(f"  极对数   {summary['pole_pairs']:.0f}（{summary['pole_pairs'] * 2:.0f} 极）")
    _log(f"  每相电阻 {summary['phase_res']:.6e} Ω")
    _log(f"  端部电感 {summary['phase_l']:.6e} H")
    _log(f"  查表行数 {summary['rows']}")
    _log(f"  MAT      {summary['map_file']}")
    _log(f"  TXT      {summary['txt_file']}")
    _log(f"  SML      {summary['sml_file']}")

    for key in ("sml_file", "txt_file", "map_file"):
        path = Path(summary[key])
        if not path.is_file() or path.stat().st_size == 0:
            _log(f"[产物缺失] {path} | 应已写出且非空 | 不存在或为 0 字节")
            return EXIT_FAIL
    _log()
    _log("下一步：AEDT → Tools → Project Tools → Import Twin Builder Models → 选上面的 SML")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="从 Motor-CAD 导出 ECE 模型（SML/TXT/MAT），供 Twin Builder 导入。",
    )
    parser.add_argument("--config", required=True, help="ECE 配置 JSON（如 config/cases/e11_ece_config.json）")
    parser.add_argument("--dry-run", action="store_true", help="只校验配置与路径，不连 Motor-CAD")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run(args)
    except KeyboardInterrupt:
        _log("[中断] 用户中断")
        return EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
