"""Core Maxwell ECE workflow.

Stages are intentionally explicit:

``inspect -> draft -> validate -> prepare -> run``

Inspection and drafting only read an AEDT file.  Preparation copies the source
to an isolated directory.  The live stage starts its own PyAEDT desktop and
never opens or edits the source project.
"""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import math
import os
import re
import shutil
import sys
import threading
import time
import uuid
from collections.abc import Iterable, Mapping
from collections.abc import Mapping as ABCMapping
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PACKAGE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = PACKAGE_DIR / "work"
ALLOWED_DQ_OUTPUT = {0, 1, 2}


def _timestamp() -> str:
    """Return a stable, timezone-aware timestamp for machine-readable evidence."""

    return datetime.now(UTC).isoformat(timespec="milliseconds")


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(_jsonable(value), indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    temporary.replace(path)


class ECEError(ValueError):
    """A user-correctable ECE workflow error."""


class ReviewRequiredError(ECEError):
    """The human review gate was not closed."""


@dataclass(frozen=True)
class AEDTBlock:
    name: str
    start: int
    end: int
    body: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_stable(path: Path) -> tuple[str, str]:
    """Read text and hash from one stable byte snapshot."""

    for _ in range(3):
        before = path.stat()
        data = path.read_bytes()
        after = path.stat()
        if before.st_size == after.st_size and before.st_mtime_ns == after.st_mtime_ns:
            return data.decode("utf-8", errors="replace"), hashlib.sha256(data).hexdigest()
    raise ECEError(f"source changed while being read: {path}")


def _jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def estimate_base_point_count(config: Mapping[str, Any]) -> dict[str, Any]:
    """Return the conservative ECE grid estimate without pretending it is native progress.

    For the full DQ grid (``PhAngIntervals=2``), Maxwell's current grid has
    ``(2m-1)^2`` points, where ``m`` is the number of current magnitudes.  The
    rotation sweep contributes ``Ntheta + 1`` samples.  The result is labelled
    as an estimate because native ECE may refine or otherwise alter the grid.
    """

    ece = config.get("ece", {}) if isinstance(config, Mapping) else {}
    sweeps = ece.get("current_sweeps", []) if isinstance(ece, Mapping) else []
    m = len(sweeps) if isinstance(sweeps, list) else 0
    theta = ece.get("rot_ang_intervals") if isinstance(ece, Mapping) else None
    intervals = ece.get("ph_ang_intervals") if isinstance(ece, Mapping) else None
    if not isinstance(theta, int) or isinstance(theta, bool) or theta < 0 or not isinstance(intervals, int):
        return {
            "value": None,
            "label": "estimated_base",
            "basis": "unavailable: incomplete current/angle grid",
            "native_counter_denominator": False,
        }
    if intervals == 2:
        current_points = max(2 * m - 1, 0) ** 2
        basis = "(2m-1)^2*(Ntheta+1), full DQ current grid"
    elif intervals == 0:
        current_points = m * m
        basis = "m^2*(Ntheta+1), native PhAngIntervals=0 grid"
    elif intervals == 1:
        current_points = max(2 * m - 1, 0) * m
        basis = "(2m-1)*m*(Ntheta+1), native PhAngIntervals=1 grid"
    elif intervals == 3:
        current_points = max(2 * m - 1, 0) ** 2
        basis = "(2m-1)^2*(Ntheta+1), alpha-beta grid estimate"
    else:
        current_points = m * (intervals + 1)
        basis = "m*(PhAngIntervals+1)*(Ntheta+1), amplitude/angle estimate"
    return {
        "value": current_points * (theta + 1),
        "label": "estimated_base",
        "basis": basis,
        "m_current_sweep_values": m,
        "n_theta_intervals": theta,
        "native_counter_denominator": False,
    }


def parse_native_progress_log(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Parse facts from a Maxwell native ECE logfile.

    Existing AEDT ECE logs expose model-card parsing and cleanup markers but
    generally do not expose a point counter.  This parser reports those facts,
    and only reports percentage/counts when a line contains an explicit,
    internally consistent counter.  It never derives a native percentage from
    the estimated grid.
    """

    log_path = Path(path).expanduser()
    result: dict[str, Any] = {
        "path": str(log_path),
        "exists": log_path.is_file(),
        "state": "missing",
        "observed_events": [],
        "models": {},
        "counter": None,
        "percent_provable": False,
    }
    if not log_path.is_file():
        return result
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        result["state"] = "unreadable"
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result
    events = result["observed_events"]
    if re.search(r"(?im)^\s*Begin ECE model setup", text):
        events.append("model_setup_started")
    if re.search(r"(?im)^\s*End ECE model setup", text):
        events.append("model_setup_completed")
    if re.search(r"(?im)^\s*Start arrays delete\.", text):
        events.append("cleanup_started")
    if re.search(r"(?im)^\s*\w+ arrays deleted\.", text):
        events.append("cleanup_arrays_deleted")
    # Capture the actual native model card values from the log, preserving text.
    for model_name, card in re.findall(r"(?im)^Begin ECE model setup:\s*\.MODEL\s+([^\s]+)\s+\w+\s*\(([^\n]+)", text):
        values = {}
        for key, value in re.findall(r"([A-Za-z][A-Za-z0-9_]*)=([^\s\)]+)", card):
            values[key] = value.rstrip(",")
        result["models"][model_name] = values
    # Accept only explicit native-looking counters.  A random percentage in a
    # diagnostic line is not progress evidence, so require point/step context.
    counter_patterns = (
        r"(?i)\b(?:point|step|sample)\s*(\d+)\s*(?:/|of)\s*(\d+)\b",
        r"(?i)\b(\d+)\s*/\s*(\d+)\s*(?:points|steps|samples)\b",
    )
    counters = []
    for pattern in counter_patterns:
        counters.extend((int(a), int(b)) for a, b in re.findall(pattern, text))
    if counters:
        done, total = counters[-1]
        if total > 0 and 0 <= done <= total:
            result["counter"] = {"completed": done, "total": total, "source": "explicit_native_log"}
            result["percent_provable"] = True
            result["percent"] = round(done * 100.0 / total, 3)
    if result["percent_provable"]:
        result["state"] = "progress_observed"
    elif "cleanup_started" in events:
        result["state"] = "cleanup_observed"
    elif "model_setup_completed" in events:
        result["state"] = "model_setup_observed"
    else:
        result["state"] = "text_observed"
    result["line_count"] = len(text.splitlines())
    return result


def parse_native_counter_dir(directory: str | os.PathLike[str]) -> dict[str, Any]:
    """Read Maxwell's explicit external-circuit sweep counters read-only.

    AEDT writes ``extnlckt.par_0`` with the initial ``sweepRest`` total and
    ``extnlckt.par`` with the latest remaining count.  The ECE table's leading
    integer column is retained as an independent observed row count.  No
    estimate is used as a denominator when these native counters are present.
    """

    root = Path(directory).expanduser().resolve()
    result: dict[str, Any] = {
        "schema": "maxwell-ece-native-counter-v1",
        "native_dir": str(root),
        "status": "missing",
        "counter_source": "explicit_extnlckt_par",
        "percent_provable": False,
        "remaining_seconds": None,
        "remaining_seconds_kind": None,
    }
    if not root.is_dir():
        return result

    def parse_par(path: Path) -> dict[str, Any] | None:
        try:
            text, digest = _read_stable(path)
            stat = path.stat()
        except (OSError, ECEError):
            return None
        def number(name: str) -> float | None:
            match = re.search(rf"(?im)^\s*{re.escape(name)}\s+([-+0-9.eE]+)\s*$", text)
            return float(match.group(1)) if match else None
        sweep = number("sweepRest")
        if sweep is None or not sweep.is_integer() or sweep < 0:
            return None
        return {
            "path": str(path),
            "sha256": digest,
            "mtime": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(timespec="milliseconds"),
            "mtime_epoch": stat.st_mtime,
            "sweep_remaining": int(sweep),
            "position": number("position"),
            "step": number("step"),
            "speed": number("speed"),
        }

    initial = parse_par(root / "extnlckt.par_0")
    current = parse_par(root / "extnlckt.par")
    first_after = parse_par(root / "extnlckt.par_1")
    snapshots = [item for item in (initial, first_after, current) if item is not None]
    result["par_snapshots"] = snapshots
    if initial is None or current is None:
        result["status"] = "counter_incomplete"
        return result

    table_path = root / "ece_table_out.txt"
    rows: list[int] = []
    table_sha = None
    if table_path.is_file():
        try:
            table_text, table_sha = _read_stable(table_path)
            for line in table_text.splitlines():
                match = re.match(r"^\s*(-?\d+)\s+[-+0-9.eE]+(?:\s+[-+0-9.eE]+){3,}", line)
                if match:
                    rows.append(int(match.group(1)))
        except (OSError, ECEError):
            rows = []
    total = initial["sweep_remaining"]
    remaining = current["sweep_remaining"]
    completed = total - remaining if remaining <= total else None
    result.update({
        "status": "progress_observed",
        "total_sweeps": total,
        "remaining_sweeps": remaining,
        "completed_sweeps": completed,
        "percent": round(completed * 100.0 / total, 6) if completed is not None and total else None,
        "percent_provable": completed is not None and total > 0,
        "position": current.get("position"),
        "step": current.get("step"),
        "speed": current.get("speed"),
        "table": {
            "path": str(table_path),
            "sha256": table_sha,
            "row_count": len(rows),
            "first_index": rows[0] if rows else None,
            "last_index": rows[-1] if rows else None,
            "indices_monotonic": rows == sorted(rows) if rows else None,
            "rows_match_completed_counter": len(rows) == completed if completed is not None else False,
        },
    })
    # Estimate ETA only from two explicit native counter snapshots.  It is
    # labelled as an estimate and is never presented as a guaranteed duration.
    rate_samples = []
    for before, after in itertools.pairwise(snapshots):
        dt = float(after["mtime_epoch"] - before["mtime_epoch"])
        dc = int(before["sweep_remaining"] - after["sweep_remaining"])
        if dt > 0 and dc > 0:
            rate_samples.append((dc / dt, dt, dc))
    if rate_samples and remaining > 0:
        rate, window, count = rate_samples[-1]
        result["throughput_sweeps_per_second"] = rate
        result["rate_window_seconds"] = window
        result["rate_window_sweeps"] = count
        result["remaining_seconds"] = remaining / rate
        result["remaining_seconds_kind"] = "estimate_from_explicit_native_counter_rate"
    return result


class _ProgressTracker:
    """Thread-safe progress/evidence writer used by prepare and live runs."""

    def __init__(self, directory: Path, *, callback: Any = None, config: Mapping[str, Any] | None = None):
        self.directory = directory
        self.path = directory / "progress.json"
        self.timing_path = directory / "timing-result.json"
        self.callback = callback
        self.started_monotonic = time.monotonic()
        self.started_at = _timestamp()
        self.lock = threading.Lock()
        self.state: dict[str, Any] = {
            "schema": "maxwell-ece-progress-v1",
            "status": "running",
            "stage": "initializing",
            "stage_percent": None,
            "percent_provable": False,
            "eta_seconds": None,
            "started_at": self.started_at,
            "completion_time": None,
            "elapsed_seconds": 0.0,
            "estimated_base": estimate_base_point_count(config or {}),
            "native_counter": None,
            "native_log": None,
            "events": [],
        }
        self._flush()

    def _flush(self) -> None:
        with self.lock:
            self.state["elapsed_seconds"] = round(time.monotonic() - self.started_monotonic, 3)
            snapshot = dict(self.state)
            _write_json(self.path, snapshot)
        if self.callback is not None:
            self.callback(snapshot)

    def update(self, stage: str, *, stage_percent: float | None = None, percent: float | None = None, event: str | None = None, **facts: Any) -> None:
        with self.lock:
            self.state["stage"] = stage
            self.state["stage_percent"] = stage_percent
            if percent is not None and 0.0 <= percent <= 100.0:
                self.state["percent"] = round(float(percent), 3)
                self.state["percent_provable"] = True
                elapsed = max(time.monotonic() - self.started_monotonic, 0.001)
                self.state["eta_seconds"] = round(elapsed * (100.0 / float(percent) - 1.0), 3) if percent > 0 else None
            if event:
                self.state.setdefault("events", []).append({"time": _timestamp(), "event": event})
            self.state.update(facts)
        self._flush()

    def finish(self, status: str, *, error: str | None = None, **facts: Any) -> None:
        with self.lock:
            self.state["status"] = status
            self.state["stage"] = "complete" if status in {"solved", "prepared"} else "blocked" if status == "blocked" else "failed"
            self.state["stage_percent"] = 100.0 if status in {"solved", "prepared"} else self.state.get("stage_percent")
            self.state["completion_time"] = _timestamp()
            self.state["completiontime"] = self.state["completion_time"]
            self.state["elapsed_seconds"] = round(time.monotonic() - self.started_monotonic, 3)
            self.state["eta_seconds"] = 0.0 if status in {"solved", "prepared"} else None
            if error:
                self.state["error"] = error
            self.state.update(facts)
            snapshot = dict(self.state)
            _write_json(self.path, snapshot)
            timing = {
                "schema": "maxwell-ece-timing-v1",
                "status": status,
                "started_at": self.started_at,
                "completion_time": self.state["completion_time"],
                "completiontime": self.state["completion_time"],
                "timestamp": self.state["completion_time"],
                "duration_seconds": self.state["elapsed_seconds"],
                "progress_path": str(self.path),
                "error": error,
            }
            _write_json(self.timing_path, timing)
        if self.callback is not None:
            self.callback(snapshot)


def _native_monitor(stop: threading.Event, roots: tuple[Path, ...], tracker: _ProgressTracker) -> None:
    """Tail known Maxwell logs during synchronous analyze_setup."""

    seen: dict[str, int] = {}
    latest_facts: dict[str, Any] | None = None
    next_scan = 0.0
    next_heartbeat = 0.0
    while not stop.wait(0.1):
        now = time.monotonic()
        # AEDT's native logfile is sparse.  Scan at most once per second, while
        # keeping the tracker heartbeat at the same cadence so elapsed wall
        # time remains observable even when the file is unchanged.
        if now >= next_scan:
            next_scan = now + 1.0
            for root in roots:
                if not root.is_dir():
                    continue
                for path in root.rglob("logfile"):
                    try:
                        size = path.stat().st_size
                        if seen.get(str(path)) == size:
                            continue
                        seen[str(path)] = size
                        latest_facts = parse_native_progress_log(path)
                    except OSError:
                        continue
                    tracker.update(
                        "nativeSolve",
                        percent=latest_facts.get("percent") if latest_facts.get("percent_provable") else None,
                        native_log=latest_facts,
                        native_counter=latest_facts.get("counter"),
                        event="native_log_observed",
                    )
        if now >= next_heartbeat:
            next_heartbeat = now + 1.0
            heartbeat_facts = {"native_log": latest_facts} if latest_facts is not None else {}
            if latest_facts is not None:
                heartbeat_facts["native_counter"] = latest_facts.get("counter")
            tracker.update("nativeSolve", **heartbeat_facts)


def _iter_blocks(text: str) -> Iterable[AEDTBlock]:
    """Yield balanced AEDT blocks without evaluating expressions.

    AEDT's textual format contains nested ``oa``/``sa``/``ta`` values that
    make a generic keyword loader lossy.  This scanner only tracks the file's
    explicit ``$begin``/``$end`` records, so quoted expressions remain raw.
    """

    begin_re = re.compile(r"^\s*\$begin(?:\s+'([^']*)')?", re.IGNORECASE)
    end_re = re.compile(r"^\s*\$end(?:\s+'([^']*)')?", re.IGNORECASE)
    lines = text.splitlines(keepends=True)
    stack: list[tuple[str, int, int]] = []
    offset = 0
    for line in lines:
        begin = begin_re.match(line)
        if begin:
            stack.append((begin.group(1) or "", offset, offset + len(line)))
        end = end_re.match(line)
        if end and stack:
            name, start, body_start = stack.pop()
            yield AEDTBlock(name, start, offset + len(line), text[body_start:offset])
        offset += len(line)


def _quoted_value(body: str, key: str) -> str | None:
    match = re.search(r"(?m)^\s*(?:'" + re.escape(key) + r"'|" + re.escape(key) + r")\s*=\s*'([^']*)'", body)
    return match.group(1) if match else None


def _variables(body: str) -> dict[str, str]:
    # Deliberately capture only the first four quoted VariableProp fields.
    # Expressions are returned verbatim and are never eval'ed.
    pattern = re.compile(
        r"VariableProp\(\s*'([^']+)'\s*,\s*'[^']*'\s*,\s*'[^']*'\s*,\s*'([^']*)'"
    )
    return {name: value for name, value in pattern.findall(body)}


def _within(block: AEDTBlock, outer: AEDTBlock) -> bool:
    return outer.start <= block.start and block.end <= outer.end


def _model_summary(text: str, model: AEDTBlock, blocks: list[AEDTBlock]) -> dict[str, Any]:
    child = [b for b in blocks if b is not model and _within(b, model)]
    name = _quoted_value(model.body, "Name") or ""
    setups = []
    for block in child:
        if block.name not in {"AnalysisSetup", "SolveSetups"} and _quoted_value(block.body, "SetupType"):
            setups.append(
                {
                    "name": block.name,
                    "setup_type": _quoted_value(block.body, "SetupType"),
                    "enabled": re.search(r"(?m)^\s*Enabled\s*=\s*(true|false)", block.body, re.IGNORECASE).group(1).lower() == "true"
                    if re.search(r"(?m)^\s*Enabled\s*=\s*(true|false)", block.body, re.IGNORECASE)
                    else None,
                }
            )
    windings = []
    motions = []
    for block in child:
        if "$begin" not in block.body and re.search(r"(?m)^\s*BoundType\s*=\s*'Winding Group'", block.body, re.IGNORECASE):
            windings.append({"name": block.name, "type": "Winding Group"})
        motion_type = _quoted_value(block.body, "MotionType")
        if "$begin" not in block.body and motion_type and motion_type.lower() in {"band", "rotating"}:
            motions.append(
                {
                    "name": block.name,
                    "motion_type": _quoted_value(block.body, "MotionType"),
                    "move_type": _quoted_value(block.body, "Move Type"),
                    "axis": _quoted_value(block.body, "Axis"),
                    "angular_velocity": _quoted_value(block.body, "Angular Velocity"),
                }
            )
    return {
        "name": name or None,
        "solution_type": _quoted_value(model.body, "SolutionType"),
        "geometry_mode": _quoted_value(model.body, "GeometryMode"),
        "setups": setups,
        "winding_groups": windings,
        "motion_setups": motions,
        "variables": _variables(model.body),
        "source_range": {"start": model.start, "end": model.end},
    }


def inspect_project(project: str | os.PathLike[str]) -> dict[str, Any]:
    """Read a project textually and list all Maxwell2D designs.

    This function never imports PyAEDT and never creates an AEDT desktop.
    """

    path = Path(project).expanduser().resolve()
    if not path.is_file():
        raise ECEError(f"AEDT project does not exist: {path}")
    text, source_hash = _read_stable(path)
    blocks = list(_iter_blocks(text))
    models = [b for b in blocks if b.name.lower() == "maxwell2dmodel"]
    designs = [_model_summary(text, model, blocks) for model in models]
    # A project can contain a Maxwell2D block whose Name is omitted in damaged
    # files.  Preserve it in the listing so selection remains explicit.
    return {
        "schema": "maxwell-ece-inspection-v1",
        "project": str(path),
        "source_hash": source_hash,
        "file_size": path.stat().st_size,
        "parser": "balanced-aedt-text-v1",
        "designs": designs,
        "warnings": [
            "变量表达式仅按原文提取，未执行求值。",
            "winding polarity and mechanical-axis convention require human review.",
            "fault/asymmetric models default to 360 mechanical degrees; no symmetry was inferred.",
        ],
    }


def _find_design(inspection: Mapping[str, Any], design: str) -> Mapping[str, Any]:
    for item in inspection.get("designs", []):
        if item.get("name") == design:
            return item
    raise ECEError(f"design {design!r} was not found in the inspected project")


def draft_config(
    inspection: Mapping[str, Any],
    *,
    design: str | None = None,
    setup: str | None = None,
    output_dir: str | os.PathLike[str] | None = None,
    overrides: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate a reviewable configuration from an inspection result."""

    designs = inspection.get("designs", [])
    if not designs:
        raise ECEError("inspection found no Maxwell2DModel designs")
    if design is None and len(designs) != 1:
        raise ECEError("multiple Maxwell2DModel designs found; choose --design explicitly")
    chosen_design = design or designs[0].get("name")
    selected = _find_design(inspection, chosen_design)
    setup_names = [s["name"] for s in selected.get("setups", [])]
    if setup is None and len(setup_names) > 1:
        chosen_setup = None
    else:
        chosen_setup = setup or (setup_names[0] if setup_names else None)
    values = selected.get("variables", {})
    winding_names = [w["name"] for w in selected.get("winding_groups", [])]
    # These are suggestions, not safety limits or accepted operating points.
    suggestions = {
        "poles": values.get("NumPoles"),
        "slots": values.get("SlotNumber_Stator"),
        "current_sweeps": ["0A", "1A", "2A"],
        "suggested_current_limit_source": values.get("IPeak"),
        "resistance": values.get("Rphase", "0ohm"),
        "inductance": values.get("Lend", "0H"),
        "rot_ang_max": "360deg",
        "in_electrical_degrees": False,
        "rot_ang_intervals": 360,
        "skew_angle": "0deg",
        "ph_ang_intervals": 2,
        "output": 0,
    }
    config: dict[str, Any] = {
        "schema": "maxwell-ece-config-v1",
        "source_project": inspection["project"],
        "source_hash": inspection.get("source_hash"),
        "design": chosen_design,
        "setup": chosen_setup,
        "variation": "",
        "aedt_version": None,
        "non_graphical": True,
        "keep_desktop_on_error": False,
        "output_dir": str(Path(output_dir or DEFAULT_OUTPUT).expanduser()),
        "winding_groups": winding_names,
        "ece": {
            "device_name": "ECE_Model1",
            "current_sweeps": suggestions["current_sweeps"],
            "suggested_current_limit_source": suggestions["suggested_current_limit_source"],
            "ph_ang_intervals": suggestions["ph_ang_intervals"],
            "resistance": suggestions["resistance"],
            "inductance": suggestions["inductance"],
            "rot_ang_max": suggestions["rot_ang_max"],
            "in_electrical_degrees": suggestions["in_electrical_degrees"],
            "rot_ang_intervals": suggestions["rot_ang_intervals"],
            "skew_angle": suggestions["skew_angle"],
            "poles": suggestions["poles"],
            "slots": suggestions["slots"],
            "output": suggestions["output"],
        },
        "human_review_required": True,
        "reviewed": False,
        "review_notes": [
            "确认 design/setup 选择、绕组顺序和电流/转矩/角度/DC 电流极性。",
            "确认 ECE 扫描点不是额定点上限；确认非对称故障使用的机械周期。",
            "确认 Output=0 ABC 或 Output=1 DQ0 与下游接口一致。",
        ],
        "suggestion_sources": {
            "source_project_hash": inspection.get("source_hash"),
            "variables": ["NumPoles", "SlotNumber_Stator", "IPeak", "Rphase", "Lend"],
            "unconfirmed": True,
        },
        "snapshot_candidates": {
            "phase_advance": values.get("PhaseAdvance"),
            "phasor_angle": values.get("PhasorAngle"),
            "initial_position": values.get("InitialPositionMD"),
            "angular_velocity": next((m.get("angular_velocity") for m in selected.get("motion_setups", []) if m.get("angular_velocity")), None),
        },
    }
    if chosen_setup is None and len(setup_names) > 1:
        config["review_notes"].insert(0, f"存在多个 setup ({', '.join(setup_names)})，必须人工选择后再 prepare/run。")
    if overrides:
        # Overrides are a user-owned review edit.  Shallow top-level fields and
        # nested ece fields are intentionally supported, without eval/merging
        # arbitrary objects.
        for key, value in overrides.items():
            if key == "ece" and isinstance(value, Mapping):
                config["ece"].update(value)
            else:
                config[key] = value
    return config


def validate_config(config: Mapping[str, Any], inspection: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Validate a configuration and return a report instead of raising."""

    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(config, Mapping):
        return {"valid": False, "errors": ["config must be a JSON object"], "warnings": []}
    if inspection is not None and not isinstance(inspection, Mapping):
        errors.append("inspection must be a JSON object")
        inspection = None
    required = ("source_project", "design", "setup", "winding_groups", "ece")
    for key in required:
        if key not in config or config[key] in (None, "", []):
            errors.append(f"missing required field: {key}")
    raw_ece = config.get("ece", {})
    if raw_ece not in ({}, None) and not isinstance(raw_ece, Mapping):
        errors.append("ece must be a JSON object")
    ece = raw_ece if isinstance(raw_ece, Mapping) else {}
    if not isinstance(config.get("reviewed", False), bool):
        errors.append("reviewed must be a boolean")
    if not isinstance(config.get("human_review_required", True), bool):
        errors.append("human_review_required must be a boolean")
    output = ece.get("output")
    if isinstance(output, bool) or output not in ALLOWED_DQ_OUTPUT:
        errors.append("ece.output must be 0 (ABC), 1 (DQ0), or 2 (LdLqFm)")
    intervals = ece.get("ph_ang_intervals")
    if isinstance(intervals, bool) or not isinstance(intervals, int) or intervals < 0 or (4 <= intervals < 12):
        errors.append("ece.ph_ang_intervals must be 0, 1, 2, 3, or >=12")
    windings = config.get("winding_groups", [])
    if not isinstance(windings, list) or len(windings) != 3:
        errors.append("exactly three winding_groups are required")
    elif any(not isinstance(v, str) or not v.strip() for v in windings) or len(set(windings)) != 3:
        errors.append("winding_groups must contain three distinct non-empty names")

    def unit_number(value: Any, units: tuple[str, ...], label: str) -> float | None:
        if not isinstance(value, (int, float, str)) or isinstance(value, bool):
            errors.append(f"{label} must be a finite value with unit {units[0]}")
            return None
        match = re.fullmatch(r"\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*([A-Za-z]+)\s*", str(value))
        if not match:
            errors.append(f"{label} must include a numeric value and unit {units[0]}")
            return None
        number = float(match.group(1))
        scales = {"a": 1.0, "ma": 1e-3, "ohm": 1.0, "h": 1.0, "mh": 1e-3, "uh": 1e-6, "deg": 1.0}
        unit = match.group(2).lower()
        if not math.isfinite(number) or unit not in {u.lower() for u in units}:
            errors.append(f"{label} is not finite or has the wrong unit")
            return None
        return number * scales[unit]

    rot_max = unit_number(ece.get("rot_ang_max"), ("deg",), "rot_ang_max")
    if rot_max is not None and rot_max <= 0:
        errors.append("rot_ang_max must be positive")
    rot_intervals = ece.get("rot_ang_intervals")
    rot_intervals_valid = isinstance(rot_intervals, int) and not isinstance(rot_intervals, bool) and rot_intervals >= 1
    if not rot_intervals_valid:
        errors.append("rot_ang_intervals must be a positive integer")
    unit_number(ece.get("skew_angle"), ("deg",), "skew_angle")
    if not isinstance(ece.get("in_electrical_degrees", False), bool):
        errors.append("in_electrical_degrees must be a boolean")
    unit_number(ece.get("resistance"), ("ohm",), "resistance")
    unit_number(ece.get("inductance"), ("H", "uH", "mH"), "inductance")
    poles_value = ece.get("poles")
    if isinstance(poles_value, bool) or not re.fullmatch(r"\d+", str(poles_value or "")) or int(poles_value) <= 0 or int(poles_value) % 2:
        errors.append("ece.poles must be a positive even integer")
    slots_value = ece.get("slots")
    slots_valid = not isinstance(slots_value, bool) and bool(re.fullmatch(r"\d+", str(slots_value or ""))) and int(slots_value) >= 0
    if not slots_valid:
        errors.append("ece.slots must be a non-negative integer")
    elif int(slots_value) > 0:
        warnings.append("slots>0 may trigger native cog refinement and additional Maxwell samples; point budget is only a base estimate")
    sweeps = ece.get("current_sweeps")
    sweep_numbers: list[float] = []
    if not isinstance(sweeps, list) or not sweeps:
        errors.append("ece.current_sweeps must be a non-empty list")
    else:
        for value in sweeps:
            number = unit_number(value, ("A", "mA"), "current_sweeps")
            if number is not None:
                if number < 0:
                    errors.append("current_sweeps must contain non-negative points")
                sweep_numbers.append(number)
        if sweep_numbers != sorted(sweep_numbers) or len(set(sweep_numbers)) != len(sweep_numbers):
            errors.append("current_sweeps must be strictly ascending without duplicates")
        if not sweep_numbers or sweep_numbers[0] != 0:
            errors.append("current_sweeps must include a zero-current point")
    intervals_valid = isinstance(intervals, int) and not isinstance(intervals, bool) and intervals >= 0 and not (4 <= intervals < 12)
    if sweep_numbers and intervals_valid and rot_intervals_valid:
        n = len(sweep_numbers)
        rot_points = rot_intervals + 1
        if intervals == 0:
            phase_points = n * n
        elif intervals == 1:
            phase_points = (2 * n - 1) * n
        elif intervals in (2, 3):
            phase_points = max(2 * n - 1, 0) ** 2
        else:
            phase_points = n * (intervals + 1)
        estimated_points = phase_points * rot_points
        point_budget = config.get("max_estimated_points", 100000)
        if isinstance(point_budget, bool) or not isinstance(point_budget, int) or point_budget < 1:
            errors.append("max_estimated_points must be a positive integer")
        elif estimated_points > point_budget:
            errors.append(f"ECE point budget exceeded: {estimated_points} > {point_budget}")
    source = Path(str(config.get("source_project", ""))).expanduser()
    if not source.is_file():
        errors.append(f"source_project does not exist: {source}")
    if source.is_file() and config.get("source_hash") and _sha256(source) != config.get("source_hash"):
        errors.append("source_hash does not match source_project")
    if inspection:
        try:
            selected = _find_design(inspection, str(config.get("design")))
            if selected.get("solution_type", "").lower() != "transient":
                errors.append("selected design solution_type is not Transient")
            setup_names = {s.get("name") for s in selected.get("setups", [])}
            if config.get("setup") not in setup_names:
                errors.append("selected setup is not present in the inspected design")
            found_windings = [w.get("name") for w in selected.get("winding_groups", [])]
            if sorted(windings) != sorted(found_windings):
                warnings.append("winding_groups differ from the offline snapshot; live validation will decide")
            if not selected.get("motion_setups"):
                errors.append("selected design has no rotation motion setup")
        except ECEError as exc:
            errors.append(str(exc))
    if config.get("human_review_required", True) and config.get("reviewed") is not True:
        warnings.append("reviewed=false: run is intentionally blocked until a human reviews the draft")
    if ece.get("rot_ang_max") == "360deg":
        warnings.append("360deg is a conservative default; confirm the mechanical periodicity")
    return {"valid": not errors, "errors": errors, "warnings": warnings}


def _copy_project(source: Path, destination_dir: Path) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / source.name
    if destination.resolve() == source.resolve():
        raise ECEError("output directory must be separate from source project")
    if destination.exists():
        raise ECEError(f"refusing to overwrite prepared project: {destination}")
    shutil.copy2(source, destination)
    return destination


def prepare_project(config: Mapping[str, Any], *, destination: str | os.PathLike[str] | None = None, progress_callback: Any = None) -> dict[str, Any]:
    """Copy the source project and write a reproducible prepared manifest."""

    if progress_callback is not None:
        config = dict(config)
        config["progress_callback"] = progress_callback
    source = Path(str(config["source_project"])).expanduser().resolve()
    report = validate_config(config)
    if report["errors"]:
        raise ECEError("configuration invalid: " + "; ".join(report["errors"]))
    _, precopy_hash = _read_stable(source)
    if config.get("source_hash") and precopy_hash != config["source_hash"]:
        raise ECEError("source changed since draft; inspect again before prepare")
    root = Path(destination or config.get("output_dir") or DEFAULT_OUTPUT).expanduser().resolve()
    tracker = _ProgressTracker(root, callback=config.get("progress_callback"), config=config)
    try:
        tracker.update("prepare", stage_percent=0.0, event="prepare_started")
        run_dir = root / f"{config['design']}-{config['setup']}-prepared-{uuid.uuid4().hex[:12]}"
        prepared = _copy_project(source, run_dir)
        tracker.update("prepare", stage_percent=50.0, event="source_copied")
        _, postcopy_hash = _read_stable(source)
        prepared_hash = _sha256(prepared)
        if precopy_hash != postcopy_hash or prepared_hash != postcopy_hash:
            raise ECEError("source changed during copy; discard the incomplete prepared directory")
        prepared_config = copy.deepcopy(dict(config))
        prepared_config.pop("progress_callback", None)
        prepared_config["source_hash"] = postcopy_hash
        prepared_config["prepared_project"] = str(prepared)
        prepared_config["prepared_dir"] = str(run_dir)
        prepared_config["prepared_source_hash"] = prepared_hash
        prepared_config["prepare_status"] = "prepared"
        (run_dir / "ece-config.json").write_text(json.dumps(_jsonable(prepared_config), indent=2, ensure_ascii=False), encoding="utf-8")
        # Keep a per-job progress/timing pair beside the prepared project.  The
        # root progress file remains a short prepare record for CLI callers.
        job_tracker = _ProgressTracker(run_dir, config=prepared_config)
        job_tracker.update("prepare", stage_percent=100.0, event="prepare_completed")
        job_tracker.finish("prepared")
        tracker.finish("prepared", prepared_dir=str(run_dir), prepared_project=str(prepared))
        return {
            "status": "prepared",
            "prepared_project": str(prepared),
            "prepared_dir": str(run_dir),
            "source_hash": postcopy_hash,
            "prepared_hash": prepared_config["prepared_source_hash"],
            "config": prepared_config,
        }
    except Exception as exc:
        tracker.finish("failed", error=f"{type(exc).__name__}: {exc}")
        raise


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def write_ece_netlist(config: Mapping[str, Any], path: str | os.PathLike[str]) -> Path:
    """Write the vendor ECE3/ECER native template as a ``.sph`` file."""

    ece = config.get("ece", {})
    device = str(ece.get("device_name", "ECE_Model1"))
    sweeps = ece.get("current_sweeps", ["1A"])
    sweep_text = ",".join(_fmt(v) for v in sweeps) if isinstance(sweeps, list) else _fmt(sweeps)
    winding_text = ",".join(str(v) for v in config.get("winding_groups", []))
    lines = [
        "* Generated by maxwell_ece; review before live execution.",
        "* ECE3/ECER syntax follows Dedicated Elements.aclb and vendor example.",
        f".MODEL {device}_ECE3 ECE3 (Windings={winding_text} Sweeps={sweep_text} PAngN={_fmt(ece.get('ph_ang_intervals', 2))} Res={_fmt(ece.get('resistance', '0ohm'))} Ind={_fmt(ece.get('inductance', '0H'))})",
        f".MODEL {device}_ECER ECER (RAngM={_fmt(ece.get('rot_ang_max', '360deg'))} EDeg={_fmt(ece.get('in_electrical_degrees', False))} RAngN={_fmt(ece.get('rot_ang_intervals', 360))} Skew={_fmt(ece.get('skew_angle', '0deg'))} Poles={_fmt(ece.get('poles'))} Slots={_fmt(ece.get('slots'))} DQOutput={_fmt(ece.get('output', 0))})",
        ".end",
    ]
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def _sml_valid(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    upper = text.upper()
    # Maxwell 2026 R1 emits ``MODELDEF ECE_Model1_ECER`` while older
    # vendor examples use ``SMLDEF``.  Require the declaration at the start
    # of a line so an incidental word in a diagnostic does not validate an
    # unrelated file.
    has_model_definition = re.search(r"(?m)^\s*(?:MODELDEF|SMLDEF)\b", upper) is not None
    has_interface = re.search(r"\b(?:PORT|INTERN)\b", upper) is not None
    return bool(text.strip()) and has_model_definition and has_interface


def _manifest(directory: Path) -> list[dict[str, Any]]:
    files = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name != "ece-output-manifest.json":
            files.append({"path": str(path.relative_to(directory)), "size": path.stat().st_size, "sha256": _sha256(path)})
    return files


def _run_live(config: Mapping[str, Any]) -> dict[str, Any]:
    """Run PyAEDT on a prepared copy.  Import is delayed for offline use."""

    prepared_path = Path(str(config.get("prepared_project", ""))).resolve()
    if not prepared_path.is_file():
        raise ECEError("run requires a prepared_project produced by prepare_project")
    if prepared_path.resolve() == Path(str(config["source_project"])).expanduser().resolve():
        raise ECEError("refusing to run on source project")
    prepared_dir = Path(str(config.get("prepared_dir", ""))).resolve()
    if not prepared_dir.is_dir() or not prepared_path.is_relative_to(prepared_dir):
        raise ECEError("prepared_project must be inside prepared_dir")
    if not (prepared_dir / "ece-config.json").is_file():
        raise ECEError("prepared directory is missing the tool manifest")
    expected_hash = config.get("prepared_source_hash")
    if not expected_hash or _sha256(prepared_path) != expected_hash:
        raise ECEError("prepared_source_hash does not match the prepared project")
    try:
        manifest = json.loads((prepared_dir / "ece-config.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ECEError(f"invalid prepared manifest: {exc}") from exc
    if not isinstance(manifest, ABCMapping):
        raise ECEError("prepared manifest must be a JSON object")
    if Path(str(manifest.get("prepared_project", ""))).expanduser().resolve() != prepared_path:
        raise ECEError("prepared manifest project does not match config")
    if Path(str(manifest.get("prepared_dir", ""))).expanduser().resolve() != prepared_dir:
        raise ECEError("prepared manifest directory does not match config")
    if manifest.get("prepared_source_hash") != expected_hash or _sha256(prepared_path) != manifest.get("prepared_source_hash"):
        raise ECEError("prepared manifest hash does not match the prepared project")
    output_dir = prepared_dir / f"ece-export-{uuid.uuid4().hex[:12]}"
    output_dir.mkdir(parents=True, exist_ok=True)
    # Keep telemetry beside the isolated job directory so a run has one stable
    # machine-readable location even though native export artifacts live in a
    # separate per-attempt directory.
    tracker = _ProgressTracker(prepared_dir, callback=config.get("progress_callback"), config=config)
    try:
        from ansys.aedt.core import Maxwell2d
    except ImportError as exc:  # pragma: no cover - depends on local AEDT env
        reason = f"PyAEDT unavailable: {exc}"
        tracker.finish("blocked", error=reason)
        return {"status": "blocked", "reason": reason, "live": False, "output_dir": str(output_dir)}
    sph = write_ece_netlist(config, output_dir / f"{config.get('design', 'design')}.sph")
    before = {p.resolve() for p in output_dir.rglob("*") if p.is_file()}
    m2d = None
    release_failed = False
    tracker_finished = False
    keep_desktop_on_error = bool(config.get("keep_desktop_on_error", False))
    try:
        tracker.update("launch", stage_percent=0.0, event="launch_started")
        constructor = {
            "project": str(prepared_path),
            "design": config["design"],
            "new_desktop": True,
            "close_on_exit": not keep_desktop_on_error,
        }
        if config.get("aedt_version"):
            constructor["version"] = config["aedt_version"]
        if config.get("non_graphical") is not None:
            constructor["non_graphical"] = bool(config["non_graphical"])
        m2d = Maxwell2d(**constructor)
        tracker.update("launch", stage_percent=100.0, event="launch_completed")
        disable_link = getattr(m2d, "change_design_settings", None)
        if not callable(disable_link):
            raise ECEError("live Maxwell exposes no change_design_settings API")
        if disable_link({"EnableTranTranLinkWithSimplorer": False}) is False:
            raise ECEError("failed to disable transient Twin Builder link on prepared design")
        # Read actual design metadata when exposed by this PyAEDT version.
        actual_solution = str(getattr(m2d, "solution_type", ""))
        if actual_solution and actual_solution.lower() != "transient":
            raise ECEError(f"live design solution_type is {actual_solution!r}, expected Transient")
        setup_names = getattr(m2d, "setup_names", None)
        if setup_names is None:
            get_setups = getattr(m2d, "GetSetups", None)
            if not callable(get_setups):
                raise ECEError("live Maxwell exposes no setup readback API")
            setup_names = get_setups()
        if config["setup"] not in {str(name) for name in (setup_names or [])}:
            raise ECEError(f"live Maxwell setup {config['setup']!r} was not found")
        motion_api = getattr(getattr(m2d, "omodelsetup", None), "GetMotionSetupNames", None)
        if not callable(motion_api):
            raise ECEError("live Maxwell exposes no motion setup readback API")
        motion_names = list(motion_api() or [])
        if not motion_names:
            raise ECEError("live Maxwell readback found no motion setup")
        boundaries = list(getattr(m2d, "boundaries", []) or [])
        selected = []
        wanted = set(config.get("winding_groups", []))
        for boundary in boundaries:
            name = str(getattr(boundary, "name", ""))
            if name in wanted:
                selected.append(boundary)
        if len(selected) != 3:
            raise ECEError(f"live Maxwell boundary readback found {len(selected)} selected windings, expected 3")
        for boundary in selected:
            props = getattr(boundary, "props", None)
            if not isinstance(props, ABCMapping):
                raise ECEError(f"boundary {getattr(boundary, 'name', '')} exposes no editable props")
            if str(props.get("Type", "")).lower() != "external":
                try:
                    props["Type"] = "External"
                except (KeyError, TypeError) as exc:
                    raise ECEError(f"boundary {getattr(boundary, 'name', '')} props are not editable") from exc
                if not hasattr(boundary, "update"):
                    raise ECEError(f"boundary {getattr(boundary, 'name', '')} has no update API")
                if boundary.update() is False:
                    raise ECEError(f"failed to update winding boundary {getattr(boundary, 'name', '')}")
        if not hasattr(m2d, "edit_external_circuit"):
            raise ECEError("installed PyAEDT has no edit_external_circuit API")
        if m2d.edit_external_circuit(netlist_file_path=str(sph)) is False:
            raise ECEError("edit_external_circuit returned False")
        if not hasattr(m2d, "save_project"):
            raise ECEError("live Maxwell exposes no save_project API")
        if m2d.save_project() is False:  # save only the prepared copy
            raise ECEError("save_project returned False")
        if not hasattr(m2d, "analyze_setup"):
            raise ECEError("installed PyAEDT has no analyze_setup API")
        cores = int(config.get("cores", 1))
        tracker.update("nativeSolve", stage_percent=None, event="native_solve_started", cores=cores)
        stop_monitor = threading.Event()
        monitor = threading.Thread(
            target=_native_monitor,
            args=(stop_monitor, (prepared_dir, output_dir), tracker),
            name="maxwell-ece-log-monitor",
            daemon=True,
        )
        monitor.start()
        try:
            # PyAEDT's analyze_setup is intentionally called synchronously.  A
            # background tailer supplies observed native facts while it blocks;
            # no unverified nonblocking/native API is guessed here.
            solve_result = m2d.analyze_setup(config["setup"], cores=cores)
        finally:
            stop_monitor.set()
            monitor.join(timeout=2.0)
        if solve_result is False:
            raise ECEError("analyze_setup returned False")
        observed_logs = []
        for native_log_path in tuple(prepared_dir.rglob("logfile")) + tuple(output_dir.rglob("logfile")):
            facts = parse_native_progress_log(native_log_path)
            if facts.get("exists"):
                observed_logs.append(facts)
        if observed_logs:
            tracker.update(
                "nativeSolve",
                native_log=observed_logs[-1],
                native_logs=observed_logs,
                native_counter=next((item.get("counter") for item in reversed(observed_logs) if item.get("counter")), None),
                event="native_logs_read",
            )
        tracker.update("nativeSolve", stage_percent=100.0, event="native_solve_completed")
        if m2d.save_project() is False:
            raise ECEError("save_project after analyze returned False")
        if not hasattr(m2d, "oanalysis") or not hasattr(m2d.oanalysis, "ExportECEData"):
            raise ECEError("installed Maxwell oanalysis has no ExportECEData API")
        variation = config.get("variation", "")
        if variation in (None, ""):
            nominal_api = getattr(getattr(m2d, "odesign", None), "GetNominalVariation", None)
            if not callable(nominal_api):
                raise ECEError("live Maxwell exposes no GetNominalVariation API")
            variation = nominal_api()
        export_args = [
            "NAME:Export Data",
            "Design Variation:=", variation,
            "Solve Setup Name:=", config["setup"],
            "Export Directory:=", str(output_dir),
        ]
        # ExportECEData may return None on success; filesystem evidence is the
        # authority, so its return value is intentionally ignored.
        tracker.update("export", stage_percent=0.0, event="export_started")
        m2d.oanalysis.ExportECEData(export_args)
        tracker.update("export", stage_percent=100.0, event="export_completed")
    except Exception as exc:
        diagnostics: dict[str, Any] = {"error": str(exc), "exception_type": type(exc).__name__}
        desktop_class = getattr(m2d, "desktop_class", None)
        desktop = getattr(desktop_class, "odesktop", None)
        diagnostics["pid"] = getattr(desktop_class, "aedt_process_id", None)
        diagnostics["port"] = getattr(desktop_class, "port", None)
        project_name = prepared_path.stem
        design_name = config["design"]
        if desktop is not None:
            try:
                diagnostics["project_list"] = [str(v) for v in list(desktop.GetProjectList())]
            except Exception as message_error:
                diagnostics["project_list_error"] = f"{type(message_error).__name__}: {message_error}"
            try:
                diagnostics["active_project"] = str(desktop.GetActiveProject())
            except Exception as message_error:
                diagnostics["active_project_error"] = f"{type(message_error).__name__}: {message_error}"
            try:
                diagnostics["messages"] = [
                    str(message)
                    for level in (2, 0)
                    for message in list(desktop.GetMessages(project_name, design_name, level))
                ]
            except Exception as message_error:
                diagnostics["message_read_error"] = f"{type(message_error).__name__}: {message_error}"
        (output_dir / "runtime-error.json").write_text(
            json.dumps(diagnostics, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
        )
        tracker.finish("failed", error=f"{type(exc).__name__}: {exc}", native_diagnostics=diagnostics)
        tracker_finished = True
        raise ECEError(
            f"live Maxwell failed: {exc}; native diagnostics: {diagnostics.get('messages', diagnostics.get('message_read_error', 'unavailable'))}"
        ) from exc
    finally:
        if m2d is not None and not (keep_desktop_on_error and sys.exc_info()[0] is not None):
            main_error_active = sys.exc_info()[0] is not None
            release_api = getattr(m2d, "release_desktop", None)
            if not callable(release_api):
                if not main_error_active:
                    release_failed = True
            else:
                try:
                    release_failed = release_api(close_projects=True, close_desktop=True) is False
                except Exception:
                    if not main_error_active:
                        release_failed = True
        m2d = None
    if release_failed:
        if not tracker_finished:
            tracker.finish("failed", error="release_desktop returned False")
        return {"status": "failed", "reason": "release_desktop returned False", "live": True, "output_dir": str(output_dir)}
    created = [p for p in output_dir.rglob("*") if p.is_file() and p.resolve() not in before]
    sml = [p for p in created if p.suffix.lower() == ".sml" and p.stat().st_size > 0 and _sml_valid(p)]
    if not sml:
        if not tracker_finished:
            tracker.finish("failed", error="no new valid MODELDEF/SMLDEF with PORT/INTERN file was exported")
        return {"status": "failed", "reason": "no new valid MODELDEF/SMLDEF with PORT/INTERN file was exported", "live": True, "output_dir": str(output_dir)}
    manifest = _manifest(output_dir)
    (output_dir / "ece-output-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if not tracker_finished:
        tracker.finish("solved", output_dir=str(output_dir), sml=[str(p) for p in sml])
    return {"status": "solved", "live": True, "output_dir": str(output_dir), "sml": [str(p) for p in sml], "manifest": manifest}


def run_project(config: Mapping[str, Any], *, live: bool = True, progress_callback: Any = None) -> dict[str, Any]:
    """Validate review state and execute a prepared isolated copy."""

    if progress_callback is not None:
        config = dict(config)
        config["progress_callback"] = progress_callback
    report = validate_config(config)
    if report["errors"]:
        return {"status": "blocked", "stage": "validate", "validation": report}
    if config.get("human_review_required", True) and config.get("reviewed") is not True:
        return {"status": "blocked", "stage": "review", "reason": "reviewed must be true after human review"}
    if not config.get("prepared_project"):
        prepared = prepare_project(config)
        config = dict(prepared["config"])
        if progress_callback is not None:
            config["progress_callback"] = progress_callback
    if not live:
        return {"status": "prepared", "live": False, "prepared_project": config.get("prepared_project")}
    return _run_live(config)


def _batch_job(config: dict[str, Any], live: bool) -> dict[str, Any]:
    try:
        return run_project(config, live=live)
    except Exception as exc:  # each job reports its own failure to the batch caller
        return {"status": "failed", "reason": f"{type(exc).__name__}: {exc}"}


def validate_batch_inputs(
    configs: list[Mapping[str, Any]], *, max_parallel: int = 1, total_cores: int | None = None
) -> tuple[list[dict[str, Any]], int]:
    """Validate batch scheduling controls without starting a job.

    The CLI live supervisor uses this same gate as :func:`batch_run` so that
    process supervision cannot accidentally change the established resource
    and duplicate-output semantics.
    """

    if isinstance(max_parallel, bool) or not isinstance(max_parallel, int) or max_parallel < 1:
        raise ECEError("max_parallel must be >= 1")
    payloads = [dict(c) for c in configs]
    if total_cores is None:
        budget = os.cpu_count() or 1
    elif isinstance(total_cores, bool) or not isinstance(total_cores, int) or total_cores < 1:
        raise ECEError("total_cores must be >= 1")
    else:
        budget = total_cores
    job_cores = [c.get("cores", 1) for c in payloads]
    if any(isinstance(c, bool) or not isinstance(c, int) or c < 1 for c in job_cores):
        raise ECEError("each job cores value must be >= 1")
    if max_parallel * max(job_cores, default=1) > budget:
        raise ECEError("max_parallel * maximum job cores exceeds total_cores")
    canonical = lambda value: os.path.normcase(str(Path(value).expanduser().resolve()))
    prepared_projects = [canonical(c["prepared_project"]) for c in payloads if c.get("prepared_project")]
    prepared_dirs = [canonical(c["prepared_dir"]) for c in payloads if c.get("prepared_dir")]
    if len(set(prepared_projects)) != len(prepared_projects) or len(set(prepared_dirs)) != len(prepared_dirs):
        raise ECEError("batch contains duplicate prepared_project or prepared_dir")
    return payloads, budget


def batch_run(
    configs: list[Mapping[str, Any]], *, max_parallel: int = 1, total_cores: int | None = None, live: bool = True,
    progress_path: str | os.PathLike[str] | None = None,
) -> list[dict[str, Any]]:
    """Run independent jobs with spawn processes and no shared AEDT session."""

    payloads, budget = validate_batch_inputs(configs, max_parallel=max_parallel, total_cores=total_cores)
    aggregate_path = Path(progress_path).expanduser().resolve() if progress_path else None
    aggregate = {
        "schema": "maxwell-ece-batch-progress-v1",
        "status": "running",
        "started_at": _timestamp(),
        "max_parallel": max_parallel,
        "total_cores": budget,
        "jobs": [
            {"index": index, "output_dir": c.get("output_dir"), "progress_path": str(Path(c.get("output_dir", "")) / "progress.json") if c.get("output_dir") else None, "status": "queued"}
            for index, c in enumerate(payloads)
        ],
    }
    if aggregate_path:
        _write_json(aggregate_path, aggregate)
    if max_parallel == 1:
        results = []
        for index, payload in enumerate(payloads):
            aggregate["jobs"][index]["status"] = "running"
            if aggregate_path:
                _write_json(aggregate_path, aggregate)
            result = _batch_job(payload, live)
            results.append(result)
            aggregate["jobs"][index].update({"status": result.get("status", "unknown"), "result": result})
            if aggregate_path:
                _write_json(aggregate_path, aggregate)
        aggregate["status"] = "completed"
        aggregate["completion_time"] = _timestamp()
        if aggregate_path:
            _write_json(aggregate_path, aggregate)
        return results
    import multiprocessing as mp

    with ProcessPoolExecutor(max_workers=max_parallel, mp_context=mp.get_context("spawn")) as pool:
        futures = {pool.submit(_batch_job, payload, live): index for index, payload in enumerate(payloads)}
        for index in range(len(payloads)):
            aggregate["jobs"][index]["status"] = "running"
        if aggregate_path:
            _write_json(aggregate_path, aggregate)
        results: list[dict[str, Any] | None] = [None] * len(payloads)
        for future in as_completed(futures):
            index = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                result = {"status": "failed", "reason": f"{type(exc).__name__}: {exc}"}
            results[index] = result
            aggregate["jobs"][index].update({"status": result.get("status", "unknown"), "result": result})
            if aggregate_path:
                _write_json(aggregate_path, aggregate)
    aggregate["status"] = "completed"
    aggregate["completion_time"] = _timestamp()
    if aggregate_path:
        _write_json(aggregate_path, aggregate)
    return [result or {"status": "failed", "reason": "missing batch result"} for result in results]
