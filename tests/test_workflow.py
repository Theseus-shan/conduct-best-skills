"""User-facing startup, resumed checking and portable CLI behavior."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import test_runtime as runtime_tests
from test_runtime import ROOT, SCRIPT, conduct, fixture


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / "local" / "workflow-tests"
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="flow-", dir=scratch)
        assert Path(self.temp.name).resolve().is_relative_to(scratch.resolve())
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.ws = conduct.Workspace(self.root)
        self.contract = fixture()
        self.write("total.py", "def total(values):\n    return sum(values)\n")
        self.write("check.py", "from total import total\nassert total([]) == 0\nassert total([2, -3, 8]) == 7\n")

    write = runtime_tests.RuntimeTests.write
    add_downstream = runtime_tests.RuntimeTests.add_downstream

    def cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), "--workspace", str(self.root), *args],
                              capture_output=True, encoding="utf-8", env=dict(os.environ, PYTHONIOENCODING="ascii"))

    def test_three_command_start_verify_resume_without_handwritten_json(self):
        result = self.cli("start", "--goal", "中文项目 🧪", "--requirement", "求和正确", "--artifact", "total.py",
                          "--input", "check.py", "--", "{python}", "-B", "check.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["goal"], "中文项目 🧪")
        self.assertEqual(self.cli("verify-ready", "--execute").returncode, 0)
        self.assertEqual(self.cli("next").returncode, 0)
        self.assertEqual(len(conduct.read_json(self.ws.state_path)["attempts"]), 1)

    def test_start_missing_check_creates_no_fake_acceptance(self):
        result = self.cli("start", "--goal", "repair", "--requirement", "correct", "--artifact", "total.py", "--input", "check.py")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.ws.folder.exists())

    def test_start_refuses_to_overwrite_existing_project(self):
        self.ws.initialize(self.contract)
        before = self.ws.contract_path.read_bytes()
        result = self.cli("start", "--goal", "new", "--requirement", "new", "--artifact", "total.py", "--input", "check.py", "--", "{python}", "check.py")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.ws.contract_path.read_bytes(), before)

    def test_ready_walks_dependencies_and_skips_current_passes(self):
        self.add_downstream()
        self.contract["tasks"].reverse()
        self.ws.initialize(self.contract)
        result = self.ws.verify_ready()
        self.assertEqual([c["criterion"] for c in result["checks"]], ["sum", "derived"])
        self.assertEqual(result["task_completion"], "COMPLETE")
        self.assertEqual(self.ws.verify_ready()["checks"], [])

    def test_ready_does_not_spin_on_failure_or_run_dependent(self):
        self.add_downstream()
        self.write("total.py", "def total(values):\n    return sum(values) + 1\n")
        self.ws.initialize(self.contract)
        result = self.ws.verify_ready()
        self.assertEqual(len(result["checks"]), 1)
        self.assertEqual(result["validation_status"], "FAILED")
        self.assertEqual(result["criteria"][1]["attempts"], 0)

    def test_ready_continues_an_independent_branch(self):
        self.add_downstream()
        self.contract["tasks"][1]["depends_on"] = []
        self.ws.initialize(self.contract)
        self.ws.operation("pending", task_id="repair", note="Awaiting observation")
        result = self.ws.verify_ready()
        self.assertEqual([c["criterion"] for c in result["checks"]], ["derived"])
        self.assertEqual(result["validation_status"], "BLOCKED")

    def test_ready_respects_budget_and_execution_acknowledgement(self):
        self.contract["criteria"][0]["check"]["max_attempts"] = 1
        self.ws.initialize(self.contract)
        self.assertEqual(self.cli("verify-ready").returncode, 2)
        self.ws.verify_ready()
        self.write("total.py", "# changed")
        result = self.ws.verify_ready()
        self.assertEqual(result["checks"], [])
        self.assertEqual(result["tasks"][0]["status"], "LIMIT_REACHED")

    def test_ready_rechecks_drift_without_overwriting_user_additions(self):
        self.ws.initialize(self.contract)
        self.ws.verify_ready()
        with (self.root / "total.py").open("a") as stream:
            stream.write("\ndef added(value):\n    return value * 2\n")
        content = (self.root / "total.py").read_bytes()
        self.assertIn("STALE", self.cli("next").stdout)
        self.assertEqual(self.ws.verify_ready()["validation_status"], "VERIFIED")
        self.assertEqual(content, (self.root / "total.py").read_bytes())

    def test_missing_artifacts_are_actionable_and_never_pass(self):
        self.ws.initialize(self.contract)
        (self.root / "total.py").unlink()
        result = self.ws.verify_ready()
        self.assertEqual(len(result["refused"]), 1)
        self.assertNotEqual(result["validation_status"], "VERIFIED")
        self.assertIn("missing", self.cli("next").stdout)


if __name__ == "__main__":
    unittest.main()
