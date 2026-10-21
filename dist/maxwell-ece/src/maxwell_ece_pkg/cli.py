"""Command line entry point for the Maxwell ECE workflow."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from .core import (
    ECEError,
    batch_run,
    draft_config,
    inspect_project,
    parse_native_counter_dir,
    prepare_project,
    run_project,
    validate_batch_inputs,
    validate_config,
)


def _process_snapshot() -> tuple[set[int], set[int]]:
    """Return existing AEDT and Maxwell solver PIDs for ownership fencing."""

    try:
        import psutil
    except ImportError:  # pragma: no cover - pmsm runtime supplies psutil
        return set(), set()
    desktops: set[int] = set()
    solvers: set[int] = set()
    for process in psutil.process_iter(["pid", "name"]):
        try:
            name = str(process.info.get("name") or "").lower()
            if name == "ansysedt.exe":
                desktops.add(int(process.info["pid"]))
            elif name == "solver2d.exe":
                solvers.add(int(process.info["pid"]))
        except (psutil.Error, OSError, TypeError, ValueError):
            continue
    return desktops, solvers


def _new_processes(before: set[int], name: str) -> list[tuple[int, str]]:
    """Read newly-created process command lines, fail-closed on ambiguity."""

    try:
        import psutil
    except ImportError:  # pragma: no cover - pmsm runtime supplies psutil
        return []
    found: list[tuple[int, str]] = []
    for process in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if int(process.info["pid"]) in before:
                continue
            if str(process.info.get("name") or "").lower() != name.lower():
                continue
            command = " ".join(str(part) for part in (process.info.get("cmdline") or []))
            found.append((int(process.info["pid"]), command))
        except (psutil.Error, OSError, TypeError, ValueError):
            continue
    return found


def _owned_native_dir(new_solver: list[tuple[int, str]]) -> tuple[int | None, Path | None]:
    """Resolve one newly-created solver PID and its native .pjt directory."""

    if len(new_solver) != 1:
        return None, None
    pid, command = new_solver[0]
    match = next((part.strip('"') for part in command.split() if part.lower().endswith(".pjt")), None)
    if not match:
        return pid, None
    native_dir = Path(match).expanduser().resolve()
    return pid, native_dir if native_dir.is_dir() else None


def _write_progress_json(path: Path | None, value: dict) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    # Windows can briefly deny replacement while an indexer/reader has the
    # destination open.  Retry the atomic update, then fall back to a direct
    # write so telemetry cannot terminate the live supervisor.
    for attempt in range(4):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 3:
                path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
                try:
                    temporary.unlink()
                except OSError:
                    pass
                return
            time.sleep(0.05 * (attempt + 1))


def _run_worker(config_path: str) -> int:
    """Execute a live job in the child process used by the supervised CLI."""

    result = run_project(_read_json(config_path), live=True, progress_callback=None)
    _dump(result)
    return 0 if result.get("status") in {"prepared", "solved"} else 2


def _run_supervised(config_path: str, *, progress_path: Path | None = None, interval: float = 1.0) -> int:
    """Run live AEDT in a child while the parent renders independent heartbeats."""

    config = _read_json(config_path)
    output_dir = Path(str(config.get("output_dir", ""))).expanduser().resolve()
    before_desktops, before_solvers = _process_snapshot()
    command = [sys.executable, "-m", "maxwell_ece_pkg.cli", "run-worker", str(Path(config_path).expanduser().resolve())]
    child = subprocess.Popen(command, cwd=str(Path(__file__).resolve().parents[1]))
    owned_desktop_pid: int | None = None
    owned_solver_pid: int | None = None
    native_dir: Path | None = None
    last_progress: dict = {"status": "starting", "stage": "initializing", "elapsed_seconds": 0.0}
    progress_bar = _ProgressBar()
    try:
        while True:
            progress_files = list(output_dir.rglob("progress.json")) if output_dir.is_dir() else []
            active: Path | None = None
            running: list[tuple[Path, dict]] = []
            loaded: list[tuple[Path, dict]] = []
            for candidate in progress_files:
                try:
                    data = _read_json(str(candidate))
                except (OSError, json.JSONDecodeError):
                    continue
                loaded.append((candidate, data))
                if data.get("status") == "running":
                    running.append((candidate, data))
            if running:
                active, last_progress = max(running, key=lambda item: item[0].stat().st_mtime)
            elif loaded:
                active, last_progress = max(loaded, key=lambda item: item[0].stat().st_mtime)
            if owned_desktop_pid is None:
                new_desktops = _new_processes(before_desktops, "ansysedt.exe")
                if len(new_desktops) == 1:
                    owned_desktop_pid = new_desktops[0][0]
            if owned_solver_pid is None:
                owned_solver_pid, candidate_native = _owned_native_dir(_new_processes(before_solvers, "solver2d.exe"))
                if candidate_native is not None:
                    native_dir = candidate_native
            progress = _monitor_once(active) if active is not None else dict(last_progress)
            last_progress = progress
            native = parse_native_counter_dir(native_dir) if native_dir is not None else {}
            view = dict(progress)
            view["elapsed_seconds"] = progress.get("live_elapsed_seconds", progress.get("elapsed_seconds", 0.0))
            if native.get("percent_provable"):
                view.update({"percent_provable": True, "percent": native.get("percent"), "eta_seconds": native.get("remaining_seconds")})
            progress_bar(view)
            _write_progress_json(
                progress_path,
                {
                    "schema": "maxwell-ece-supervised-progress-v1",
                    "captured_at": datetime.now(UTC).isoformat(timespec="milliseconds"),
                    "progress_path": str(active) if active is not None else None,
                    "progress": progress,
                    "owned_desktop_pid": owned_desktop_pid,
                    "owned_solver_pid": owned_solver_pid,
                    "owned_native_dir": str(native_dir) if native_dir is not None else None,
                    "native": native,
                },
            )
            if child.poll() is not None:
                break
            time.sleep(interval)
    finally:
        if child.poll() is None:
            child.wait()
    final_status = str(last_progress.get("status", "failed"))
    return 0 if final_status in {"solved", "prepared"} and child.returncode == 0 else (child.returncode or 2)


def _worker_result(log_path: Path) -> dict:
    """Decode the final JSON object emitted by a run-worker log."""

    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {"status": "failed", "reason": "worker log could not be read"}
    decoder = json.JSONDecoder()
    candidates: list[dict] = []
    for offset, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[offset:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "status" in value:
            candidates.append(value)
    return candidates[-1] if candidates else {"status": "failed", "reason": "worker emitted no result JSON"}


def _process_details(before: set[int], name: str, assigned: set[int]) -> list[tuple[int, float, str]]:
    """Return newly-created process metadata, excluding already-owned PIDs."""

    try:
        import psutil
    except ImportError:  # pragma: no cover - pmsm runtime supplies psutil
        return []
    found: list[tuple[int, float, str]] = []
    for process in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
        try:
            pid = int(process.info["pid"])
            if pid in before or pid in assigned:
                continue
            if str(process.info.get("name") or "").lower() != name.lower():
                continue
            command = " ".join(str(part) for part in (process.info.get("cmdline") or []))
            found.append((pid, float(process.info.get("create_time") or time.time()), command))
        except (psutil.Error, OSError, TypeError, ValueError):
            continue
    return sorted(found, key=lambda item: (item[1], item[0]))


def _batch_progress_snapshot(output_dir: Path) -> tuple[Path | None, dict]:
    """Select the newest active progress file below one job output directory."""

    if not output_dir.is_dir():
        return None, {}
    candidates: list[tuple[Path, dict]] = []
    for path in output_dir.rglob("progress.json"):
        try:
            data = _read_json(str(path))
        except (OSError, json.JSONDecodeError):
            continue
        candidates.append((path, data))
    if not candidates:
        return None, {}
    running = [item for item in candidates if item[1].get("status") == "running"]
    return max(running or candidates, key=lambda item: item[0].stat().st_mtime)


def _batch_supervised(
    config_paths: list[str], *, max_parallel: int, total_cores: int | None, progress_path: str | None, interval: float = 1.0
) -> list[dict]:
    """Supervise one independent worker process per live Maxwell job.

    Each worker owns exactly one PyAEDT invocation.  The parent only reads
    progress files and native counters, allowing multiple blocking
    ``analyze_setup`` calls to run concurrently without threads or a shared
    AEDT session.
    """

    configs = [_read_json(path) for path in config_paths]
    payloads, budget = validate_batch_inputs(configs, max_parallel=max_parallel, total_cores=total_cores)
    aggregate_path = Path(progress_path).expanduser().resolve() if progress_path else None
    before_desktops, before_solvers = _process_snapshot()
    assigned_desktops: set[int] = set()
    assigned_solvers: set[int] = set()
    evidence_started = datetime.now(UTC)
    aggregate = {
        "schema": "maxwell-ece-batch-supervision-v1",
        "status": "running",
        "started_at": evidence_started.isoformat(timespec="milliseconds"),
        "max_parallel": max_parallel,
        "total_cores": budget,
        "jobs": [
            {
                "index": index,
                "config_path": str(Path(config_paths[index]).expanduser().resolve()),
                "output_dir": config.get("output_dir"),
                "status": "queued",
            }
            for index, config in enumerate(payloads)
        ],
    }
    if aggregate_path:
        _write_progress_json(aggregate_path, aggregate)

    active: dict[int, dict] = {}
    results: list[dict | None] = [None] * len(payloads)
    next_index = 0
    progress_bar = _ProgressBar()
    log_root = (aggregate_path.parent / (aggregate_path.stem + "-workers")) if aggregate_path else None
    while next_index < len(payloads) or active:
        while next_index < len(payloads) and len(active) < max_parallel:
            index = next_index
            config_path = Path(config_paths[index]).expanduser().resolve()
            output_dir = Path(str(payloads[index].get("output_dir", ""))).expanduser().resolve()
            log_path = (log_root if log_root is not None else output_dir) / f"batch-worker-{index}.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_handle = log_path.open("w", encoding="utf-8")
            started = datetime.now(UTC)
            command = [sys.executable, "-m", "maxwell_ece_pkg.cli", "run-worker", str(config_path)]
            child = subprocess.Popen(
                command,
                cwd=str(Path(__file__).resolve().parents[1]),
                stdout=log_handle,
                stderr=subprocess.STDOUT,
            )
            log_handle.close()
            active[index] = {
                "child": child,
                "output_dir": output_dir,
                "log_path": log_path,
                "started": started,
                "worker_pid": child.pid,
                "aedt_pid": None,
                "aedt_started_at": None,
                "solver_pid": None,
                "solver_started_at": None,
                "native_dir": None,
                "progress_path": None,
                "last_progress": {"status": "starting", "stage": "initializing", "elapsed_seconds": 0.0},
            }
            aggregate["jobs"][index].update({"status": "running", "worker_pid": child.pid, "worker_started_at": started.isoformat(timespec="milliseconds"), "log_path": str(log_path)})
            next_index += 1

        for index, state in list(active.items()):
            progress_file, progress = _batch_progress_snapshot(state["output_dir"])
            if progress_file is not None:
                state["progress_path"] = progress_file
                state["last_progress"] = progress
            worker_start = state["started"].timestamp()
            if state["aedt_pid"] is None:
                candidates = [item for item in _process_details(before_desktops, "ansysedt.exe", assigned_desktops) if item[1] >= worker_start]
                if candidates:
                    pid = candidates[0][0]
                    state["aedt_pid"] = pid
                    state["aedt_started_at"] = datetime.fromtimestamp(candidates[0][1], UTC).isoformat(timespec="milliseconds")
                    assigned_desktops.add(pid)
            if state["solver_pid"] is None:
                candidates = [item for item in _process_details(before_solvers, "solver2d.exe", assigned_solvers) if item[1] >= worker_start]
                if candidates:
                    pid, _, command_line = candidates[0]
                    state["solver_pid"] = pid
                    state["solver_started_at"] = datetime.fromtimestamp(candidates[0][1], UTC).isoformat(timespec="milliseconds")
                    assigned_solvers.add(pid)
                    match = next((part.strip('"') for part in command_line.split() if part.lower().endswith(".pjt")), None)
                    if match:
                        candidate_native = Path(match).expanduser().resolve()
                        if candidate_native.is_dir():
                            state["native_dir"] = candidate_native
            progress_view = _monitor_once(progress_file) if progress_file is not None else dict(state["last_progress"])
            state["last_progress"] = progress_view
            native = parse_native_counter_dir(state["native_dir"]) if state["native_dir"] is not None else {}
            view = dict(progress_view)
            view["elapsed_seconds"] = progress_view.get("live_elapsed_seconds", progress_view.get("elapsed_seconds", 0.0))
            if native.get("percent_provable"):
                view.update({"percent_provable": True, "percent": native.get("percent"), "eta_seconds": native.get("remaining_seconds")})
            progress_bar(view)
            job_view = aggregate["jobs"][index]
            job_view.update(
                {
                    "progress_path": str(state["progress_path"]) if state["progress_path"] else None,
                    "aedt_pid": state["aedt_pid"],
                    "aedt_started_at": state["aedt_started_at"],
                    "solver_pid": state["solver_pid"],
                    "solver_started_at": state["solver_started_at"],
                    "native_dir": str(state["native_dir"]) if state["native_dir"] else None,
                    "progress": progress_view,
                    "native": native,
                }
            )
            if state["child"].poll() is not None:
                finished = datetime.now(UTC)
                result = _worker_result(state["log_path"])
                result.setdefault("worker_pid", state["worker_pid"])
                result.setdefault("worker_started_at", state["started"].isoformat(timespec="milliseconds"))
                result["worker_finished_at"] = finished.isoformat(timespec="milliseconds")
                result["worker_returncode"] = state["child"].returncode
                results[index] = result
                job_view.update({"status": result.get("status", "failed"), "worker_finished_at": result["worker_finished_at"], "worker_returncode": state["child"].returncode, "result": result})
                active.pop(index)
        if aggregate_path:
            _write_progress_json(aggregate_path, aggregate)
        if active:
            time.sleep(interval)

    evidence_finished = datetime.now(UTC)
    intervals = []
    for job in aggregate["jobs"]:
        if job.get("worker_started_at") and job.get("worker_finished_at"):
            start = datetime.fromisoformat(job["worker_started_at"])
            end = datetime.fromisoformat(job["worker_finished_at"])
            intervals.append((start, end))
    overlap_seconds = 0.0
    if len(intervals) >= 2:
        overlap_start = max(start for start, _ in intervals)
        overlap_end = min(end for _, end in intervals)
        overlap_seconds = max(0.0, (overlap_end - overlap_start).total_seconds())
    aggregate.update({"status": "completed", "completion_time": evidence_finished.isoformat(timespec="milliseconds"), "overlap_evidence": {"job_count": len(intervals), "overlap_seconds": round(overlap_seconds, 3), "overlap_observed": overlap_seconds > 0.0}})
    if aggregate_path:
        _write_progress_json(aggregate_path, aggregate)
    return [result or {"status": "failed", "reason": "missing batch result"} for result in results]


class _ProgressBar:
    """Small terminal renderer; unknown native percentages stay explicitly unknown."""

    def __init__(self):
        self._spinner = 0

    def __call__(self, state: dict) -> None:
        self._spinner += 1
        elapsed = float(state.get("elapsed_seconds") or 0.0)
        stage = str(state.get("stage", ""))
        percent = state.get("stage_percent")
        if stage == "nativeSolve" and state.get("percent_provable"):
            percent = state.get("percent")
        if percent is None:
            display = "?%"
            eta = "ETA unavailable"
        else:
            display = f"{float(percent):5.1f}%"
            eta_seconds = state.get("eta_seconds")
            eta = f"ETA {float(eta_seconds):.1f}s" if eta_seconds is not None else "ETA unavailable"
        spinner = "|/-\\"[self._spinner % 4]
        print(f"\r[{spinner}] {stage:12s} {display} elapsed {elapsed:.1f}s {eta}", end="", flush=True)
        if state.get("status") in {"solved", "prepared", "failed", "blocked"}:
            print()


def _read_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _dump(value: object) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def _monitor_once(path: Path) -> dict:
    """Read-only live view; never updates the run's progress file."""

    data = _read_json(str(path))
    started_text = data.get("started_at")
    elapsed = data.get("elapsed_seconds")
    if data.get("status") == "running" and isinstance(started_text, str):
        try:
            started = datetime.fromisoformat(started_text)
            if started.tzinfo is None:
                started = started.replace(tzinfo=UTC)
            elapsed = max(0.0, (datetime.now(UTC) - started.astimezone(UTC)).total_seconds())
        except ValueError:
            pass
    return {**data, "live_elapsed_seconds": round(float(elapsed or 0.0), 3)}


def _native_monitor_snapshot(progress_path: Path, native_dir: Path, snapshot_out: Path) -> dict:
    """Read native counters and persist an independent evidence snapshot."""

    native = parse_native_counter_dir(native_dir)
    snapshot = {
        "schema": "maxwell-ece-native-monitor-snapshot-v1",
        "captured_at": datetime.now(UTC).isoformat(timespec="milliseconds"),
        "read_only_source": True,
        "progress": _monitor_once(progress_path),
        "native": native,
    }
    snapshot_out.parent.mkdir(parents=True, exist_ok=True)
    snapshot_out.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    # Preserve the initial native counter file once for later evidence review;
    # never write into the AEDT temporary directory.
    initial_source = native_dir / "extnlckt.par_0"
    initial_copy_dir = snapshot_out.parent / (snapshot_out.stem + "-initial-native")
    initial_copy = initial_copy_dir / initial_source.name
    if initial_source.is_file() and not initial_copy.exists():
        initial_copy_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(initial_source, initial_copy)
        snapshot["initial_native_snapshot"] = str(initial_copy)
        snapshot_out.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return snapshot


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Maxwell2D -> Twin Builder native ECE workflow")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("inspect", help="offline list Maxwell2D designs, setups, windings and motion")
    p.add_argument("project")
    p.add_argument("--write", metavar="JSON", help="write inspection JSON")

    p = sub.add_parser("draft", help="write a reviewable draft configuration")
    p.add_argument("project")
    p.add_argument("--design", required=False)
    p.add_argument("--setup", required=False)
    p.add_argument("--output-dir")
    p.add_argument("--write", required=True, metavar="JSON")
    p.add_argument("--reviewed", action="store_true", help="explicitly close human review gate")

    p = sub.add_parser("validate", help="validate a draft/prepared JSON")
    p.add_argument("config")
    p.add_argument("--inspection")

    p = sub.add_parser("prepare", help="copy source into an isolated work directory")
    p.add_argument("config")
    p.add_argument("--destination")

    p = sub.add_parser("run", help="run the reviewed prepared copy")
    p.add_argument("config")
    p.add_argument("--offline", action="store_true", help="prepare only; do not start AEDT")
    p.add_argument("--progress-json", metavar="JSON", help="parent-owned supervised progress and native counter JSON")
    p.add_argument("--heartbeat-interval", type=float, default=1.0, help="parent heartbeat interval during live run")

    p = sub.add_parser("run-worker", help=argparse.SUPPRESS)
    p.add_argument("config")

    p = sub.add_parser("batch", help="run independent JSON jobs with spawn processes")
    p.add_argument("configs", nargs="+", metavar="CONFIG")
    p.add_argument("--max-parallel", type=int, default=1)
    p.add_argument("--total-cores", type=int)
    p.add_argument("--progress-json", metavar="JSON", help="write aggregate batch progress/timing JSON")
    p.add_argument("--offline", action="store_true")
    p.add_argument("--heartbeat-interval", type=float, default=1.0, help="parent heartbeat interval during live batch")

    p = sub.add_parser("monitor", help="read-only live elapsed/stage view for an existing progress.json")
    p.add_argument("progress_json", metavar="PROGRESS_JSON")
    p.add_argument("--interval", type=float, default=1.0, help="poll interval in seconds")
    p.add_argument("--once", action="store_true", help="print one snapshot and exit")
    p.add_argument("--native-dir", help="explicit AEDT temporary directory containing extnlckt.par counters")
    p.add_argument(
        "--snapshot-out",
        default="work/monitor-snapshot.json",
        help="independent JSON snapshot path when --native-dir is supplied",
    )

    sub.add_parser("mcp", help="serve the local thin MCP interface over stdio")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "inspect":
            result = inspect_project(args.project)
            if args.write:
                Path(args.write).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
            _dump(result)
            return 0
        if args.command == "draft":
            inspection = inspect_project(args.project)
            config = draft_config(inspection, design=args.design, setup=args.setup, output_dir=args.output_dir)
            if args.reviewed:
                config["reviewed"] = True
            Path(args.write).write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
            _dump(config)
            return 0
        if args.command == "validate":
            config = _read_json(args.config)
            inspection = _read_json(args.inspection) if args.inspection else None
            result = validate_config(config, inspection)
            _dump(result)
            return 0 if result["valid"] else 2
        if args.command == "prepare":
            result = prepare_project(_read_json(args.config), destination=args.destination, progress_callback=_ProgressBar())
            _dump(result)
            return 0
        if args.command == "run":
            if args.heartbeat_interval <= 0:
                raise ECEError("heartbeat interval must be positive")
            if args.offline:
                result = run_project(_read_json(args.config), live=False, progress_callback=_ProgressBar())
                _dump(result)
                return 0 if result.get("status") in {"prepared", "solved"} else 2
            return _run_supervised(args.config, progress_path=Path(args.progress_json).expanduser().resolve() if args.progress_json else None, interval=args.heartbeat_interval)
        if args.command == "run-worker":
            return _run_worker(args.config)
        if args.command == "batch":
            if args.heartbeat_interval <= 0:
                raise ECEError("heartbeat interval must be positive")
            if args.offline:
                configs = [_read_json(path) for path in args.configs]
                result = batch_run(
                    configs,
                    max_parallel=args.max_parallel,
                    total_cores=args.total_cores,
                    live=False,
                    progress_path=args.progress_json,
                )
            else:
                result = _batch_supervised(
                    args.configs,
                    max_parallel=args.max_parallel,
                    total_cores=args.total_cores,
                    progress_path=args.progress_json,
                    interval=args.heartbeat_interval,
                )
            _dump(result)
            return 0 if all(item.get("status") in {"prepared", "solved"} for item in result) else 2
        if args.command == "monitor":
            if args.interval <= 0:
                raise ECEError("monitor interval must be positive")
            progress_path = Path(args.progress_json).expanduser().resolve()
            native_dir = Path(args.native_dir).expanduser().resolve() if args.native_dir else None
            snapshot_out = Path(args.snapshot_out).expanduser().resolve()
            if args.once:
                snapshot = _native_monitor_snapshot(progress_path, native_dir, snapshot_out) if native_dir else _monitor_once(progress_path)
                _dump(snapshot)
                return 0
            while True:
                snapshot = _native_monitor_snapshot(progress_path, native_dir, snapshot_out) if native_dir else _monitor_once(progress_path)
                native = snapshot.get("native", {}) if native_dir else {}
                status = str(snapshot.get("status", "unknown"))
                progress = snapshot.get("progress", snapshot)
                status = str(progress.get("status", status))
                stage = str(progress.get("stage", "unknown"))
                percent = native.get("percent") if native.get("percent_provable") else progress.get("percent") if progress.get("percent_provable") else progress.get("stage_percent")
                display = "?%" if percent is None else f"{float(percent):.1f}%"
                eta = native.get("remaining_seconds") if native_dir else progress.get("eta_seconds")
                eta_text = f" ETA~{float(eta) / 3600.0:.2f}h" if eta is not None else " ETA unavailable"
                print(
                    f"\r[monitor] {status:8s} {stage:12s} {display:>6s} "
                    f"elapsed {progress['live_elapsed_seconds']:.1f}s{eta_text}",
                    end="",
                    flush=True,
                )
                if status in {"solved", "prepared", "failed", "blocked"}:
                    print()
                    return 0 if status in {"solved", "prepared"} else 2
                time.sleep(args.interval)
        if args.command == "mcp":
            from .mcp_server import serve

            serve()
            return 0
    except (ECEError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
