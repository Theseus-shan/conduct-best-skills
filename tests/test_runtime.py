"""Executable invariants; synthetic isolated projects, no external services."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/conduct-best-skills/scripts/conduct.py"
spec = importlib.util.spec_from_file_location("conduct", SCRIPT)
conduct = importlib.util.module_from_spec(spec)
spec.loader.exec_module(conduct)


def fixture():
    return {"schema_version": 1, "goal": "Correct total while preserving its scalar API",
            "tasks": [{"id": "repair", "objective": "Fix total", "depends_on": [], "criteria": ["sum"], "needs": ["python"]}],
            "criteria": [{"id": "sum", "requirement": "Empty, signed and normal totals are correct", "kind": "Mandatory",
                          "inputs": ["check.py"], "artifacts": ["total.py"],
                          "check": {"argv": ["{python}", "-B", "check.py"], "timeout_seconds": 5, "max_attempts": 4}}]}


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / "local" / "test-workspaces"
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="conduct-test-", dir=scratch)
        assert Path(self.temp.name).resolve().is_relative_to(scratch.resolve())
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.ws = conduct.Workspace(self.root)
        self.contract = fixture()
        self.write("total.py", "def total(values):\n    return sum(values)\n")
        self.write("check.py", "from total import total\nassert total([]) == 0\nassert total([2, -3, 8]) == 7\n")

    def write(self, name, content):
        (self.root / name).write_text(content, encoding="utf-8")

    def init(self):
        self.ws.initialize(self.contract)

    def test_failure_repair_and_version_drift(self):
        self.write("total.py", "def total(values):\n    return sum(values) + 1\n")
        self.init()
        self.assertEqual(self.ws.verify("sum")["status"], "FAIL")
        self.assertEqual(self.ws.status()["validation_status"], "FAILED")
        self.write("total.py", "def total(values):\n    return sum(values)\n")
        self.assertEqual(self.ws.status()["criteria"][0]["status"], "STALE")
        self.assertEqual(self.ws.verify("sum")["status"], "PASS")
        self.assertEqual(self.ws.status()["task_completion"], "COMPLETE")
        self.write("total.py", "def total(values):\n    return sum(values)\n\n# User addition\ndef product(values):\n    return 42\n")
        self.assertEqual(self.ws.status()["criteria"][0]["status"], "STALE")
        self.ws.verify("sum")
        self.assertIn("def product", (self.root / "total.py").read_text())

    def test_test_code_drift_invalidates_pass(self):
        self.init()
        self.ws.verify("sum")
        self.write("check.py", "raise RuntimeError('new requirement')\n")
        self.assertEqual(self.ws.status()["criteria"][0]["status"], "STALE")

    def test_contract_change_invalidates_pass(self):
        self.init()
        self.ws.verify("sum")
        self.contract["criteria"][0]["requirement"] = "A stronger requirement"
        conduct.atomic_json(self.ws.contract_path, self.contract)
        self.assertEqual(self.ws.status()["criteria"][0]["status"], "STALE")

    def test_tampered_or_missing_log_cannot_pass(self):
        self.init()
        run = self.ws.verify("sum")
        self.write(run["log"], "forged success")
        self.assertEqual(self.ws.status()["criteria"][0]["status"], "INCONCLUSIVE")
        (self.root / run["log"]).unlink()
        self.assertEqual(self.ws.status()["criteria"][0]["status"], "INCONCLUSIVE")

    def test_missing_artifact_cannot_pass(self):
        self.init()
        self.ws.verify("sum")
        (self.root / "total.py").unlink()
        self.assertNotEqual(self.ws.status()["validation_status"], "VERIFIED")

    def test_check_mutates_artifact(self):
        self.write("check.py", "from pathlib import Path\nPath('total.py').write_text('# changed')\n")
        self.init()
        self.assertEqual(self.ws.verify("sum")["status"], "INCONCLUSIVE")
        self.assertNotEqual(self.ws.status()["validation_status"], "VERIFIED")

    def test_timeout_requires_reconciliation(self):
        self.contract["criteria"][0]["check"]["timeout_seconds"] = 1
        self.write("check.py", "import time\ntime.sleep(5)\n")
        self.init()
        self.assertEqual(self.ws.verify("sum")["status"], "INCONCLUSIVE")
        self.assertEqual(self.ws.status()["validation_status"], "BLOCKED")
        with self.assertRaises(conduct.ContractError):
            self.ws.verify("sum")
        op = self.ws.status()["unknown_operations"][0]
        self.ws.operation(op["id"], outcome="NOT_APPLIED", note="Direct process exited; no children or writes")
        self.assertFalse(self.ws.status()["unknown_operations"])

    def test_missing_executable_is_inconclusive(self):
        self.contract["criteria"][0]["check"]["argv"] = ["nonexistent-conduct-test-binary"]
        self.init()
        self.assertEqual(self.ws.verify("sum")["status"], "INCONCLUSIVE")

    def test_unknown_operation_preserves_identity(self):
        self.init()
        self.ws.operation("create-report", task_id="repair", note="Before simulated create")
        with self.assertRaises(conduct.ContractError):
            self.ws.operation("create-report", task_id="repair", note="Duplicate")
        with self.assertRaises(conduct.ContractError):
            self.ws.verify("sum")
        self.ws.operation("create-report", outcome="SUCCEEDED", note="Query found exactly one record")
        self.assertEqual(self.ws.status()["criteria"][0]["status"], "UNTESTED")
        self.assertEqual(self.ws.verify("sum")["status"], "PASS")

    def test_budget_not_reset_by_file_change(self):
        self.contract["criteria"][0]["check"]["max_attempts"] = 1
        self.init()
        self.ws.verify("sum")
        self.write("total.py", "# changed")
        self.assertEqual(self.ws.status()["tasks"][0]["status"], "LIMIT_REACHED")
        with self.assertRaises(conduct.ContractError):
            self.ws.verify("sum")

    def test_lock_and_init_protect_existing_state(self):
        self.init()
        before = self.ws.state_path.read_bytes()
        with self.assertRaises(conduct.ContractError):
            self.ws.initialize(self.contract)
        with self.ws.locked():
            with self.assertRaises(conduct.ContractError):
                self.ws.verify("sum")
        self.assertEqual(before, self.ws.state_path.read_bytes())

    def test_interrupted_check_recovery_does_not_claim_success(self):
        self.init()
        self.ws.verify("sum")
        state = conduct.read_json(self.ws.state_path)
        state["attempts"][0]["status"] = "RUNNING"
        self.ws.save(state)
        with self.assertRaises(conduct.ContractError):
            self.ws.verify("sum")
        self.ws.recover("Process no longer running; no writes observed")
        self.assertEqual(self.ws.status()["criteria"][0]["status"], "INCONCLUSIVE")
        self.assertEqual(self.ws.verify("sum")["status"], "PASS")

    def add_downstream(self):
        self.contract["tasks"].append({"id": "publishable", "objective": "Check derived artifact", "depends_on": ["repair"], "criteria": ["derived"]})
        c = copy.deepcopy(self.contract["criteria"][0])
        c.update(id="derived", inputs=["derived_check.py"], artifacts=["derived.txt"])
        c["check"]["argv"] = ["{python}", "-B", "derived_check.py"]
        self.contract["criteria"].append(c)
        self.write("derived.txt", "result")
        self.write("derived_check.py", "from pathlib import Path\nassert Path('derived.txt').read_text() == 'result'\n")

    def test_dependencies_gate_execution(self):
        self.add_downstream()
        self.init()
        with self.assertRaises(conduct.ContractError):
            self.ws.verify("derived")
        self.ws.verify("sum")
        self.assertEqual(self.ws.verify("derived")["status"], "PASS")

    def test_dependency_mutation_during_check_cannot_pass(self):
        self.add_downstream()
        self.write("derived_check.py", "from pathlib import Path\nPath('total.py').write_text('# upstream changed')\n")
        self.init()
        self.ws.verify("sum")
        self.assertEqual(self.ws.verify("derived")["status"], "INCONCLUSIVE")

    def test_new_operation_invalidates_previous_pass(self):
        self.init()
        self.ws.verify("sum")
        self.ws.operation("new-write", task_id="repair", note="Changing external state")
        self.ws.operation("new-write", outcome="SUCCEEDED", note="Queried expected record")
        self.assertEqual(self.ws.status()["criteria"][0]["status"], "STALE")
        self.assertEqual(self.ws.verify("sum")["status"], "PASS")

    def test_independent_branch_can_continue_when_another_is_unknown(self):
        self.add_downstream()
        self.contract["tasks"][1]["depends_on"] = []
        self.init()
        self.ws.operation("pending-write", task_id="repair", note="Response unknown")
        self.assertEqual(self.ws.verify("derived")["status"], "PASS")
        self.assertEqual(self.ws.status()["validation_status"], "BLOCKED")

    def test_optional_failure_does_not_mask_mandatory_success(self):
        self.add_downstream()
        self.contract["tasks"][0]["criteria"].append("derived")
        self.contract["tasks"].pop()
        self.contract["criteria"][1]["kind"] = "Quality"
        self.write("derived_check.py", "raise AssertionError('optional layout quality')\n")
        self.init()
        self.ws.verify("sum")
        self.ws.verify("derived")
        report = self.ws.status()
        self.assertEqual(report["validation_status"], "VERIFIED")
        self.assertEqual(report["criteria"][1]["status"], "FAIL")

    def test_upstream_reverification_invalidates_downstream(self):
        self.add_downstream()
        self.init()
        self.ws.verify("sum")
        self.ws.verify("derived")
        self.write("total.py", "def total(values):\n    return sum(values)\n# revised\n")
        self.ws.verify("sum")
        rows = {c["id"]: c for c in self.ws.status()["criteria"]}
        self.assertEqual(rows["derived"]["status"], "STALE")

    def test_validation_rejects_cycles_unmapped_and_unsafe_paths(self):
        for mutate in (
            lambda c: c["tasks"][0].update(depends_on=["repair"]),
            lambda c: c["tasks"][0].update(criteria=[]),
            lambda c: c["criteria"][0].update(artifacts=["../secret"]),
            lambda c: c["criteria"][0].update(inputs=["C:\\secret"]),
            lambda c: c["criteria"][0]["check"].update(timeout_seconds=-1),
            lambda c: c["criteria"][0]["check"].update(argv=["powershell", "something"]),
        ):
            contract = copy.deepcopy(self.contract)
            mutate(contract)
            with self.subTest(contract=contract), self.assertRaises(conduct.ContractError):
                conduct.validate(contract, self.root)

    def test_routing_hard_constraints_precede_preference(self):
        def cap(key, **kw):
            return dict(id=key, provides=["python"], effect="READ_ONLY", available=True,
                        constraints_met=True, observation="Local interpreter probe passed", **kw)
        unavailable = cap("favorite", preference=100)
        unavailable["available"] = False
        costly = cap("paid", preference=50)
        costly["effect"] = "HIGH_IMPACT"
        result = conduct.route(self.contract, {"capabilities": [unavailable, costly, cap("local") ]})[0]
        self.assertEqual(result["selected"], "local")
        self.assertEqual(len(result["rejected"]), 2)
        self.assertEqual(conduct.route(self.contract, {"capabilities": []})[0]["status"], "UNAVAILABLE")

    def test_cli_requires_execution_acknowledgement_and_returns_json(self):
        self.init()
        proc = subprocess.run([sys.executable, str(SCRIPT), "--workspace", str(self.root), "verify", "sum"],
                              capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("--execute", json.loads(proc.stderr)["error"])
        self.assertFalse(conduct.read_json(self.ws.state_path)["attempts"])

    def test_report_is_read_only_and_current(self):
        self.init()
        self.ws.verify("sum")
        state = self.ws.state_path.read_bytes()
        self.assertIn("VERIFIED", conduct.markdown(self.ws.status()))
        self.assertEqual(state, self.ws.state_path.read_bytes())
        self.write("total.py", "# stale")
        self.assertIn("STALE", conduct.markdown(self.ws.status()))


if __name__ == "__main__":
    unittest.main()
