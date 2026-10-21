"""命令行入口：给定 `.aedt`，在新建空白 `.slx` 里批量生成已绑定的 AnsoftSFunction 块。

对应设计 `docs/design/simulink-binding.md` §6.1（错误四段式）、§6.2（退出码）、§6.3（F1–F4 验收命令）、
§4.5（每块完成即保存）、§3.4（块名去重）。

用法：
    python scripts/bind_simulink.py --aedt <path.aedt> --dry-run      # 只解析（F1）
    python scripts/bind_simulink.py --aedt <path.aedt> --out <path.slx>

单块流程（设计 §4.1 十四步）：
    建块 → 触发弹窗 → 勾选 → Browse 选 .aedt → 选 design → OK → 读回（索引全 -1）
    → 脚本构造完整 UserData 并写回 → 读回核验 → 保存
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from data_exchange.aedt_parser import ParseError, parse_aedt
from data_exchange.config import Config, ConfigError, load_config
from data_exchange.models import STAGE_SAVE, STAGE_WRITE, BindingResult
from simulink_controller.binder import (
    EngineError,
    MatlabHost,
    bind_block,
    model_name,
    read_userdata,
    save_model,
    write_userdata,
)
from simulink_controller.verifier import Expected, verify_block

EXIT_OK = 0
EXIT_PARTIAL = 1
EXIT_PARSE = 2
EXIT_ENGINE = 3

DEFAULT_OUT_DIR = ".thincoder/tmp/simulink-binding"


def _log(msg: str = "") -> None:
    print(msg, flush=True)


def print_specs(specs) -> None:
    """打印解析结果（F1 的验收读数）。

    同时显示 `instance`（`.aedt` 原文，写进 UserData）与 `block`（Simulink 块名，重名时去重）——
    两者不同时读者才知道为什么块名带 `_2`。
    """
    _log(f"解析结果：{len(specs)} 个 SimulinkData 元件（{specs[0].aedt_path}）")
    for i, spec in enumerate(specs, start=1):
        _log(
            f"[{i}] CompName={spec.comp_name}  design={spec.design}  instance={spec.instance}  "
            f"block={spec.block_name}  id={spec.comp_id}  analysis={spec.analysis}"
        )
        outs = ",".join(p.name for p in spec.out_ports)
        ins = ",".join(p.name for p in spec.in_ports)
        _log(f"    dir0={len(spec.out_ports)}({outs})  dir1={len(spec.in_ports)}({ins})")
        _log(f"    UserData={spec.build_userdata()}")


def print_result_table(results: list[BindingResult]) -> None:
    """F3 的字段比对表：字段 / 期望 / 实际 / 结论（按块逐段打印）。"""
    for res in results:
        if not res.checks:
            continue
        _log()
        _log(f"核验表 Blk={res.instance}（CompName={res.comp_name}）：")
        _log(f"  | {'字段':<20} | {'期望':<50} | {'实际':<50} | 结论 |")
        for field_name, expect, actual, verdict in res.checks:
            _log(f"  | {field_name:<20} | {expect:<50} | {actual:<50} | {verdict} |")


def print_summary(results: list[BindingResult], out_slx: Path | None) -> None:
    ok = [r for r in results if r.ok]
    fail = [r for r in results if not r.ok]
    _log()
    _log(f"结果：通过 {len(ok)} / 失败 {len(fail)}（共 {len(results)} 块）")
    for res in results:
        if res.ok:
            method = f" Browse={res.browse_method}" if res.browse_method else ""
            _log(f"  OK   {res.instance} ({res.comp_name}){method}")
        else:
            _log(f"  FAIL {res.instance} ({res.comp_name})  {res.message}")
    if out_slx is not None:
        _log(f"输出模型：{out_slx}")


def _target_slx(out_dir: Path, spec) -> Path:
    """算出该块的输出文件路径：`{design名}.slx`；撞名时追加 `_2`/`_3`（设计 §4.5）。"""
    illegal = '<>:"/\\|?*'
    base = "".join("_" if ch in illegal else ch for ch in spec.design).strip(" .") or "design"
    path = out_dir / f"{base}.slx"
    i = 1
    while path.exists():
        i += 1
        path = out_dir / f"{base}_{i}.slx"
    return path


def ensure_blank_model(host: MatlabHost, out_slx: Path) -> str:
    """新建空白模型（设计 §7：不修改已有 `.slx`，故同名旧文件直接报错）。"""
    if out_slx.exists():
        raise EngineError(f"建块 | {out_slx} | 输出模型不存在（只新建空白） | 文件已存在，请先删除或换名")
    out_slx.parent.mkdir(parents=True, exist_ok=True)
    host.eval("bdclose('all')", f"{out_slx}", "能关闭已有模型")
    name = model_name(out_slx)
    host.eval(f"new_system('{name}')", f"{out_slx}", "能新建空白模型")
    return name


def run_block(
    host: MatlabHost,
    model: str,
    spec,
    out_slx: Path,
    cfg: Config,
    fault_design: str | None,
) -> tuple[BindingResult, bool]:
    """跑完一个块的十四步，返回 (result, engine_dead)。"""
    blk_path = f"{model}/{spec.block_name}"

    # 步 1–10：建块、触发、窗口操作、关窗
    result, engine_dead = bind_block(host, spec, blk_path, out_slx, cfg)
    if result.status == "failed":
        return result, engine_dead

    # 步 11：读回 UserData（此时末尾索引全为 -1，仅作读数，不作判据）
    try:
        before = read_userdata(host, blk_path)
    except EngineError as exc:
        result.fail(STAGE_WRITE, f"Blk={spec.block_name}", "能读回点 OK 后的 UserData", str(exc))
        return result, False
    result.readback_after_ok = before

    # 步 12：脚本构造完整 UserData 并写回（对话框只读入清单，不建映射）
    userdata = spec.build_userdata()
    try:
        write_userdata(host, blk_path, userdata)
        result.userdata_written = userdata
    except EngineError as exc:
        result.fail(STAGE_WRITE, f"Blk={spec.block_name}", "UserData 可写回", str(exc))
        return result, False

    # 步 13：读回核验
    try:
        after = read_userdata(host, blk_path)
    except EngineError as exc:
        result.fail(STAGE_WRITE, f"Blk={spec.block_name}", "写回后能读回 UserData", str(exc))
        return result, False
    result.userdata_readback = after

    expected = Expected.from_spec(spec)
    if fault_design:
        expected = expected.with_design(fault_design)
    verified = verify_block(spec, after, expected)
    verified.readback_after_ok = before
    verified.userdata_written = userdata
    verified.userdata_readback = after
    if not verified.ok:
        return verified, False

    # 步 14：每块完成即保存（设计 §4.5）
    try:
        save_model(host, model, out_slx)
    except EngineError as exc:
        parts = str(exc).split(" | ")
        verified.fail(
            STAGE_SAVE,
            f"Blk={spec.block_name}",
            parts[2] if len(parts) >= 4 else "save_system 能成功",
            " | ".join(parts[3:]) if len(parts) >= 4 else str(exc),
        )
        return verified, False

    # 保存后核验文件真的落在磁盘上（防止“报成功但无文件”）
    if not out_slx.exists():
        verified.fail(
            STAGE_SAVE,
            f"Blk={spec.block_name}",
            "输出 .slx 已落盘",
            f"{out_slx} 不存在",
        )
        return verified, False

    # 步 15：关闭本块的模型，为下一块腾出干净的模型空间（设计 §4.1）
    try:
        host.eval(f"close_system('{model}', 0)", f"{model}", "能关闭本块模型")
    except EngineError:
        # 关不掉不致命：下一块用不同模型名，不会撞车；但记到结果里
        verified.message = (verified.message or "") + " | 警告：模型未能关闭"

    return verified, False


def run(args: argparse.Namespace, cfg: Config) -> int:
    # 段① 解析
    try:
        specs = parse_aedt(args.aedt)
    except ParseError as exc:
        _log(f"[解析失败] {exc}")
        return EXIT_PARSE
    print_specs(specs)

    if args.dry_run:
        _log("dry-run：只做解析，不启动 MATLAB 引擎、不生成 .slx")
        return EXIT_OK

    out_dir = Path(args.out_dir or DEFAULT_OUT_DIR).expanduser()
    if not out_dir.is_absolute():
        out_dir = (Path.cwd() / out_dir).resolve()
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        _log(f"[输出目录] {out_dir} | 可创建 | {exc}")
        return EXIT_ENGINE

    # 段② 绑定（一块一模型，设计 §4.4）
    host = MatlabHost(cfg)
    results: list[BindingResult] = []
    try:
        try:
            host.start()
        except EngineError as exc:
            _log(f"[引擎失败] {exc}")
            return EXIT_ENGINE

        for spec in specs:
            _log()
            _log(f"── 绑定 {spec.comp_name}（instance={spec.instance} block={spec.block_name} "
                 f"design={spec.design}）")
            t0 = time.monotonic()
            # 每块新建独立模型与独立输出文件
            try:
                out_slx = _target_slx(out_dir, spec)
                model = ensure_blank_model(host, out_slx)
            except EngineError as exc:
                results.append(
                    BindingResult(
                        instance=spec.block_name,
                        comp_name=spec.comp_name,
                        status="failed",
                        stage="建块",
                        message=str(exc),
                    )
                )
                _log(f"   failed  用时 {time.monotonic() - t0:.1f}s  （{exc}）")
                continue
            res, engine_dead = run_block(host, model, spec, out_slx, cfg, args.fault_expected_design)
            results.append(res)
            _log(f"   {res.status}  用时 {time.monotonic() - t0:.1f}s")
            if engine_dead:
                _log(f"   ! 该块令引擎不可信：杀掉重建（累计重启 {host.restarts + 1} 次）")
                try:
                    host.restart()
                except EngineError as exc:
                    _log(f"[引擎失败] {exc}")
                    # 引擎重建失败：余下块无法继续，按已得结果收尾
                    results.extend(
                        BindingResult(
                            instance=s.block_name,
                            comp_name=s.comp_name,
                            status="failed",
                            stage="引擎",
                            message=f"引擎 | Blk={s.block_name} | 引擎可重建 | {exc}",
                        )
                        for s in specs[len(results):]
                    )
                    return EXIT_ENGINE
    finally:
        host.stop()

    print_result_table(results)
    print_summary(results, out_dir)

    if len(results) == len(specs) and all(r.ok for r in results):
        return EXIT_OK

    # 设计 §4.2 的降级口径：未走通的块打印待人工清单，但不标通过
    by_block = {spec.block_name: spec for spec in specs}
    pending = [r for r in results if not r.ok and r.instance in by_block]
    if pending:
        _log()
        _log("以下块未自动绑定成功（不计通过），需人工在 Simplorer Link Assignment Dialog 里完成：")
        for res in pending:
            spec = by_block[res.instance]
            _log(
                f"   - 块 {spec.block_name}（{spec.comp_name}）：勾选 Read link information from file → "
                f"Browse → {spec.aedt_path} → design={spec.design} / analysis={spec.analysis} → OK"
            )
    return EXIT_PARTIAL


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Twin Builder ⇄ Simulink 绑定自动化：给定 .aedt，在新建空白 .slx 里生成已绑定的 AnsoftSFunction 块。",
    )
    parser.add_argument("--aedt", required=True, help="Twin Builder 工程文件路径（只读解析）")
    parser.add_argument("--out-dir", help=f"输出目录（每元件一个 .slx，文件名取 design 名）；缺省 {DEFAULT_OUT_DIR}")
    parser.add_argument("--dry-run", action="store_true", help="只做解析并打印元件与端口，不启动 MATLAB")
    parser.add_argument("--config", help="配置文件路径，缺省 config/base.yaml")
    parser.add_argument(
        "--fault-expected-design",
        help="验收用：把核验期望的 design 改成此值，模拟不一致场景（F3 不一致 / F4-b）",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        cfg = load_config(args.config)
    except ConfigError as exc:
        _log(f"[引擎失败] {exc}")
        return EXIT_ENGINE
    try:
        return run(args, cfg)
    except KeyboardInterrupt:
        _log("[中断] 用户中断")
        return EXIT_ENGINE


if __name__ == "__main__":
    sys.exit(main())
