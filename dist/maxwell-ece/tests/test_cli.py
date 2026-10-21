import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from maxwell_ece_pkg.cli import _batch_progress_snapshot, _worker_result
from maxwell_ece_pkg.core import ECEError, validate_batch_inputs


class MaxwellEceCliTests(unittest.TestCase):
    def test_worker_result_uses_last_result_object_after_native_log(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "worker.log"
            path.write_text('PyAEDT INFO: {"message":"diagnostic"}\n{"status":"solved","live":true}\n', encoding="utf-8")
            self.assertEqual(_worker_result(path)["status"], "solved")

    def test_batch_progress_snapshot_prefers_running_job(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "old").mkdir()
            (root / "new").mkdir()
            (root / "old" / "progress.json").write_text(json.dumps({"status": "complete"}), encoding="utf-8")
            (root / "new" / "progress.json").write_text(json.dumps({"status": "running", "stage": "nativeSolve"}), encoding="utf-8")
            path, value = _batch_progress_snapshot(root)
            self.assertEqual(path, root / "new" / "progress.json")
            self.assertEqual(value["stage"], "nativeSolve")

    def test_batch_scheduler_keeps_core_budget_gate(self):
        with self.assertRaisesRegex(ECEError, "total_cores"):
            validate_batch_inputs([{"cores": 2}, {"cores": 2}], max_parallel=2, total_cores=2)


if __name__ == "__main__":
    unittest.main()
