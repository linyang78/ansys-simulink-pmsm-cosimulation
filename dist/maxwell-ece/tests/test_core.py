import copy
import json
import os
import sys
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from maxwell_ece_pkg.core import (
    ECEError,
    _native_monitor,
    _ProgressTracker,
    _sml_valid,
    draft_config,
    estimate_base_point_count,
    inspect_project,
    parse_native_counter_dir,
    parse_native_progress_log,
    prepare_project,
    run_project,
    validate_config,
    write_ece_netlist,
)

# 本文件位于 <包根>/tests/ —— parents[1] 即包根
PKG = Path(__file__).resolve().parents[1]           # dist/maxwell-ece
HERE = PKG
ROOT = HERE
HEALTHY = PKG / "models" / "e11_PMSM_IPM.aedt"
ACTUAL = HEALTHY


class MaxwellEceCoreTests(unittest.TestCase):
    def test_parse_existing_native_log_reports_facts_without_fake_counter(self):
        logs = sorted((HERE / "tests" / "fixtures").rglob("logfile"))
        self.assertTrue(logs, "repository must contain a real native ECE logfile fixture")
        facts = parse_native_progress_log(logs[0])
        self.assertIn(facts["state"], {"model_setup_observed", "cleanup_observed", "progress_observed", "text_observed"})
        self.assertFalse(facts["percent_provable"])
        self.assertIsNone(facts["counter"])
        self.assertGreaterEqual(facts["line_count"], 20)
        ecer = next((values for name, values in facts["models"].items() if name.endswith("_ECER")), None)
        self.assertIsNotNone(ecer)
        self.assertIn(ecer["RAngN"], {"3", "12", "24", "1440"})

    def test_explicit_native_counter_is_the_only_percentage_source(self):
        with tempfile.TemporaryDirectory() as temp:
            log = Path(temp) / "logfile"
            log.write_text("native Point 12/48\n", encoding="utf-8")
            facts = parse_native_progress_log(log)
        self.assertTrue(facts["percent_provable"])
        self.assertEqual(facts["counter"], {"completed": 12, "total": 48, "source": "explicit_native_log"})
        self.assertEqual(facts["percent"], 25.0)

    def test_native_counter_directory_uses_explicit_total_remaining_and_table_rows(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            par0 = "B_TIME\n step 0.0001\n position0 0\n sweepRest 100\nE_TIME\n"
            par1 = "B_TIME\n step 0.0001\n position 0.25\n sweepRest 99\nE_TIME\n"
            current = "B_TIME\n step 0.0001\n position 7.5\n sweepRest 70\nE_TIME\n"
            for name, text, stamp in (("extnlckt.par_0", par0, 1000), ("extnlckt.par_1", par1, 1010), ("extnlckt.par", current, 1020)):
                path = root / name
                path.write_text(text, encoding="utf-8")
                os.utime(path, (stamp, stamp))
            (root / "ece_table_out.txt").write_text("".join(f" {i} 0 0 0 0\n" for i in range(30)), encoding="utf-8")
            facts = parse_native_counter_dir(root)
        self.assertEqual(facts["total_sweeps"], 100)
        self.assertEqual(facts["remaining_sweeps"], 70)
        self.assertEqual(facts["completed_sweeps"], 30)
        self.assertEqual(facts["percent"], 30.0)
        self.assertEqual(facts["table"]["row_count"], 30)
        self.assertTrue(facts["table"]["rows_match_completed_counter"])
        self.assertEqual(facts["remaining_seconds_kind"], "estimate_from_explicit_native_counter_rate")
        self.assertGreater(facts["remaining_seconds"], 0.0)

    def test_full_dq_estimate_is_labeled_and_does_not_claim_native_denominator(self):
        config = {"ece": {"current_sweeps": ["0A", "21.65A", "43.3A", "108.25A", "216.5A", "324.75A", "433A"], "ph_ang_intervals": 2, "rot_ang_intervals": 1440}}
        estimate = estimate_base_point_count(config)
        self.assertEqual(estimate["value"], (2 * 7 - 1) ** 2 * (1440 + 1))
        self.assertEqual(estimate["label"], "estimated_base")
        self.assertFalse(estimate["native_counter_denominator"])

    def test_prepare_writes_machine_readable_progress_and_timing(self):
        config = draft_config(inspect_project(HEALTHY), design="PMSM_Healthy", setup="Setup1")
        config["reviewed"] = True
        with tempfile.TemporaryDirectory() as temp:
            result = prepare_project(config, destination=temp)
            run_dir = Path(result["prepared_dir"])
            progress = json.loads((run_dir / "progress.json").read_text(encoding="utf-8"))
            timing = json.loads((run_dir / "timing-result.json").read_text(encoding="utf-8"))
        self.assertEqual(progress["status"], "prepared")
        self.assertEqual(progress["stage"], "complete")
        self.assertIsNotNone(progress["completion_time"])
        self.assertEqual(timing["status"], "prepared")
        self.assertIsNotNone(timing["completion_time"])
        self.assertGreaterEqual(timing["duration_seconds"], 0.0)

    def test_native_monitor_heartbeat_advances_elapsed_without_log_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            tracker = _ProgressTracker(root, config={"ece": {"current_sweeps": ["0A"], "ph_ang_intervals": 2, "rot_ang_intervals": 3}})
            stop = threading.Event()
            monitor = threading.Thread(target=_native_monitor, args=(stop, (root,), tracker), daemon=True)
            monitor.start()
            time.sleep(1.25)
            stop.set()
            monitor.join(timeout=2.0)
            progress = json.loads((root / "progress.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(progress["elapsed_seconds"], 1.0)
        self.assertEqual(progress["stage"], "nativeSolve")
        self.assertFalse(progress["percent_provable"])

    def test_sml_valid_accepts_current_modeldef_and_legacy_smldef_headers(self):
        with tempfile.TemporaryDirectory() as temp:
            current = Path(temp) / "current.sml"
            current.write_text("MODELDEF ECE_Model1_ECER\nPORT WindingA\n", encoding="utf-8")
            legacy = Path(temp) / "legacy.sml"
            legacy.write_text("SMLDEF model\nINTERN WindingA\n", encoding="utf-8")
            embedded = Path(temp) / "embedded.sml"
            embedded.write_text("diagnostic MODELDEF ECE_Model1_ECER\nPORT WindingA\n", encoding="utf-8")
            self.assertTrue(_sml_valid(current))
            self.assertTrue(_sml_valid(legacy))
            self.assertFalse(_sml_valid(embedded))

    def test_offline_inspect_finds_exact_healthy_contract(self):
        snapshot = inspect_project(HEALTHY)
        self.assertEqual(len(snapshot["designs"]), 2)  # 真实工程含 PMSM_Healthy + PMSM_UD
        design = snapshot["designs"][0]
        self.assertEqual(design["name"], "PMSM_Healthy")
        self.assertEqual(design["solution_type"], "Transient")
        self.assertEqual([x["name"] for x in design["setups"]], ["Setup1", "Setup2"])  # 真实工程每个 design 含两个 setup
        self.assertEqual(len(design["winding_groups"]), 3)
        self.assertEqual([x["name"] for x in design["motion_setups"]], ["MotionSetup1"])
        self.assertEqual(design["variables"]["NumPoles"], "8")

    def test_actual_two_design_snapshot_requires_explicit_setup(self):
        snapshot = inspect_project(ACTUAL)
        self.assertEqual([d["name"] for d in snapshot["designs"]], ["PMSM_Healthy", "PMSM_UD"])
        for design in snapshot["designs"]:
            self.assertEqual([s["name"] for s in design["setups"]], ["Setup1", "Setup2"])
            self.assertEqual(len(design["winding_groups"]), 3)
            self.assertEqual(len(design["motion_setups"]), 1)
        draft = draft_config(snapshot, design="PMSM_Healthy")
        self.assertIsNone(draft["setup"])
        self.assertIn("phasor_angle", draft["snapshot_candidates"])

    def test_dq_point_budget_is_rejected(self):
        config = draft_config(inspect_project(HEALTHY), design="PMSM_Healthy", setup="Setup1")
        config["ece"]["output"] = 2
        config["ece"]["rot_ang_intervals"] = 10000
        self.assertFalse(validate_config(config)["valid"])

    def test_slots_zero_disables_cog_refinement_and_poles_stay_even(self):
        config = draft_config(inspect_project(HEALTHY), design="PMSM_Healthy", setup="Setup1")
        config["ece"]["slots"] = "0"
        self.assertTrue(validate_config(config)["valid"])
        config["ece"]["poles"] = "7"
        self.assertFalse(validate_config(config)["valid"])

    def test_validate_malformed_json_inputs_are_reports_not_exceptions(self):
        base = draft_config(inspect_project(HEALTHY), design="PMSM_Healthy", setup="Setup1")
        malformed = [
            None,
            ["not", "an", "object"],
            {**copy.deepcopy(base), "ece": {**base["ece"], "ph_ang_intervals": None, "rot_ang_intervals": "oops"}},
            {**copy.deepcopy(base), "winding_groups": [{}, "B", "C"]},
        ]
        for candidate in malformed:
            with self.subTest(candidate=candidate):
                report = validate_config(candidate)
                self.assertFalse(report["valid"])
                self.assertIsInstance(report["errors"], list)

    def test_draft_is_blocked_until_review_and_template_lists_windings(self):
        snapshot = inspect_project(HEALTHY)
        config = draft_config(snapshot, design="PMSM_Healthy", setup="Setup1")
        self.assertFalse(config["reviewed"])
        report = validate_config(config, snapshot)
        self.assertTrue(report["valid"])
        with tempfile.TemporaryDirectory() as temp:
            path = write_ece_netlist(config, Path(temp) / "model.sph")
            text = path.read_text()
            self.assertIn("Windings=WG_Ph1_P1,WG_Ph2_P1,WG_Ph3_P1", text)
            self.assertIn("DQOutput=0", text)
            self.assertIn("EDeg=false", text)
        self.assertEqual(run_project(config, live=False)["status"], "blocked")

    def test_prepare_is_unique_and_offline_run_does_not_start_aedt(self):
        snapshot = inspect_project(HEALTHY)
        config = draft_config(snapshot, design="PMSM_Healthy", setup="Setup1", output_dir=tempfile.gettempdir())
        config["reviewed"] = True
        with tempfile.TemporaryDirectory() as temp:
            a = prepare_project(config, destination=temp)
            b = prepare_project(config, destination=temp)
            self.assertNotEqual(a["prepared_dir"], b["prepared_dir"])
            self.assertEqual(run_project(a["config"], live=False)["status"], "prepared")
            self.assertEqual(HEALTHY.read_bytes(), Path(config["source_project"]).read_bytes())

    def test_live_rejects_prepared_manifest_mismatch(self):
        config = draft_config(inspect_project(HEALTHY), design="PMSM_Healthy", setup="Setup1")
        config["reviewed"] = True
        with tempfile.TemporaryDirectory() as temp:
            prepared = prepare_project(config, destination=temp)
            manifest_path = Path(prepared["prepared_dir"]) / "ece-config.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["prepared_source_hash"] = "tampered"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(ECEError):
                from maxwell_ece_pkg.core import _run_live
                _run_live(prepared["config"])

    def test_fake_live_updates_external_props_exports_and_releases(self):
        snapshot = inspect_project(HEALTHY)
        config = draft_config(snapshot, design="PMSM_Healthy", setup="Setup1")
        config["reviewed"] = True
        calls = {}

        class Boundary:
            def __init__(self, name):
                self.name, self.bound_type, self.props = name, "Winding Group", {}
            def update(self):
                calls.setdefault("updated", []).append(self.name)
                return True

        class FakeAnalysis:
            def ExportECEData(self, args):
                calls["export_args"] = args
                export_dir = Path(args[args.index("Export Directory:=") + 1])
                (export_dir / "model.sml").write_text("SMLDEF model\nPORT A X\n", encoding="utf-8")

        class FakeMaxwell:
            def __init__(self, **kwargs):
                calls["constructor"] = kwargs
                self.solution_type = "Transient"
                self.setup_names = ["Setup1"]
                self.project_name = "prepared"
                self.design_name = "healthy"
                self.odesign = types.SimpleNamespace(GetNominalVariation=lambda: "Nominal")
                self.boundaries = [Boundary(v) for v in config["winding_groups"]]
                self.omodelsetup = types.SimpleNamespace(GetMotionSetupNames=lambda: ["MotionSetup1"])
                self.oanalysis = FakeAnalysis()
                self.desktop_class = types.SimpleNamespace(odesktop=types.SimpleNamespace(GetMessages=lambda *args: []))
            def edit_external_circuit(self, **kwargs):
                calls["edit"] = kwargs
                return True
            def change_design_settings(self, settings):
                calls["settings"] = settings
                return True
            def save_project(self):
                calls["save"] = True
                return True
            def analyze_setup(self, *args, **kwargs):
                calls["analyze"] = (args, kwargs)
                return True
            def release_desktop(self, **kwargs):
                calls["release"] = kwargs
                return True

        modules = {name: sys.modules.get(name) for name in ("ansys", "ansys.aedt", "ansys.aedt.core")}
        sys.modules["ansys"] = types.ModuleType("ansys")
        sys.modules["ansys.aedt"] = types.ModuleType("ansys.aedt")
        sys.modules["ansys.aedt.core"] = types.SimpleNamespace(Maxwell2d=FakeMaxwell)
        try:
            with tempfile.TemporaryDirectory() as temp:
                prepared = prepare_project(config, destination=temp)
                result = run_project(prepared["config"], live=True)
            self.assertEqual(result["status"], "solved")
            self.assertEqual(calls["constructor"]["new_desktop"], True)
            self.assertEqual(calls["constructor"]["close_on_exit"], True)
            self.assertEqual(calls["settings"], {"EnableTranTranLinkWithSimplorer": False})
            self.assertEqual(calls["edit"]["netlist_file_path"].lower().endswith(".sph"), True)
            self.assertEqual(calls["export_args"][calls["export_args"].index("Design Variation:=") + 1], "Nominal")
            self.assertEqual(result["status"], "solved")
            self.assertTrue(calls["save"])
            self.assertTrue(calls["analyze"])
            self.assertTrue(calls["release"]["close_projects"])
        finally:
            for name, module in modules.items():
                if module is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = module

    def test_live_requires_save_project_and_releases_on_failure(self):
        config = draft_config(inspect_project(HEALTHY), design="PMSM_Healthy", setup="Setup1")
        config["reviewed"] = True
        calls = {"released": False}

        class Boundary:
            def __init__(self, name):
                self.name, self.props = name, {"Type": "External"}
            def update(self):
                raise AssertionError("already External boundaries must not be updated")

        class FakeWithoutSave:
            def __init__(self, **kwargs):
                self.solution_type = "Transient"
                self.setup_names = ["Setup1"]
                self.boundaries = [Boundary(v) for v in config["winding_groups"]]
                self.omodelsetup = types.SimpleNamespace(GetMotionSetupNames=lambda: ["MotionSetup1"])
            def edit_external_circuit(self, **kwargs):
                return True
            def change_design_settings(self, settings):
                return True
            def release_desktop(self, **kwargs):
                calls["released"] = True
                return True

        modules = {name: sys.modules.get(name) for name in ("ansys", "ansys.aedt", "ansys.aedt.core")}
        sys.modules["ansys"] = types.ModuleType("ansys")
        sys.modules["ansys.aedt"] = types.ModuleType("ansys.aedt")
        sys.modules["ansys.aedt.core"] = types.SimpleNamespace(Maxwell2d=FakeWithoutSave)
        try:
            with tempfile.TemporaryDirectory() as temp:
                prepared = prepare_project(config, destination=temp)
                with self.assertRaises(ECEError):
                    run_project(prepared["config"], live=True)
            self.assertTrue(calls["released"])
        finally:
            for name, module in modules.items():
                if module is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = module


if __name__ == "__main__":
    unittest.main()
