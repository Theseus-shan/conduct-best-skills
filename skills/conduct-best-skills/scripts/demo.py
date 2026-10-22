"""Run a synthetic repair/recovery demonstration in a new directory."""
import argparse
import json
from pathlib import Path
import sys

from conduct import ContractError, Workspace, atomic_json, digest, markdown, require, route


def run(destination):
    root = Path(destination).absolute()
    require(root.resolve() == root, "Refusing redirected demo destination")
    require(not root.exists(), "Demo output must be a new directory; existing work is never overwritten")
    root.mkdir(parents=True)
    def write(name, content):
        (root / name).write_text(content, encoding="utf-8")
    write("total.py", "def total(values):\n    return sum(values) + 1\n")
    write("check.py", "from total import total\nassert total([]) == 0\nassert total([2, -3, 8]) == 7\nassert isinstance(total([1, 2]), int)\n")
    contract = {"schema_version": 1, "goal": "Repair total, preserve user additions, and verify current evidence",
                "tasks": [{"id": "repair", "objective": "Correct the scalar total API", "needs": ["python"],
                           "depends_on": [], "criteria": ["correctness"]}],
                "criteria": [{"id": "correctness", "kind": "Mandatory", "requirement": "Empty and signed totals preserve the scalar API",
                              "artifacts": ["total.py"], "inputs": ["check.py"],
                              "check": {"argv": ["{python}", "-B", "check.py"], "timeout_seconds": 10, "max_attempts": 4}}]}
    atomic_json(root / "contract.json", contract)
    ws = Workspace(root)
    ws.initialize(contract)
    sequence = []
    def record(step, expected):
        report = ws.status()
        require(report["validation_status"] == expected, f"Unexpected state at {step}: {report['validation_status']}")
        sequence.append({"step": step, "validation_status": report["validation_status"],
                         "criterion_status": report["criteria"][0]["status"]})
    record("Initial unverified task", "PARTIALLY_VERIFIED")
    ws.verify("correctness")
    record("Actual assertion detects the defect", "FAILED")
    write("total.py", "def total(values):\n    return sum(values)\n")
    ws.verify("correctness")
    record("Repair passes the real check", "VERIFIED")
    with (root / "total.py").open("a", encoding="utf-8") as stream:
        stream.write("\n# Simulated user addition must survive recovery.\ndef double(value):\n    return value * 2\n")
    record("User edit makes the old evidence stale", "PARTIALLY_VERIFIED")
    require(ws.status()["criteria"][0]["status"] == "STALE", "Version drift was not detected")
    preserved_hash = digest((root / "total.py").read_bytes())
    ws.operation("report-create", task_id="repair", note="Before synthetic report creation")
    write("remote-record.json", '{"id": "report-create", "count": 1}\n')
    record("Lost response leaves operation unknown", "BLOCKED")
    observed = json.loads((root / "remote-record.json").read_text(encoding="utf-8"))
    require(observed["count"] == 1, "Duplicate simulated record")
    ws.operation("report-create", outcome="SUCCEEDED", note="Queried remote-record.json: exactly one record exists")
    ws.verify("correctness")
    record("Reconciled and reverified without replay or overwrite", "VERIFIED")
    require(digest((root / "total.py").read_bytes()) == preserved_hash, "Recovery changed user files")
    catalog = {"capabilities": [
        {"id": "favorite-but-unavailable", "provides": ["python"], "effect": "READ_ONLY", "available": False,
         "constraints_met": True, "observation": "Synthetic unavailable candidate", "preference": 100},
        {"id": "local-python", "provides": ["python"], "effect": "READ_ONLY", "available": True,
         "constraints_met": True, "observation": "This interpreter executed the demonstration checks", "preference": 0}]}
    atomic_json(root / "catalog.json", catalog)
    routing = route(contract, catalog)
    require(routing[0]["selected"] == "local-python", "Routing bypassed a hard constraint")
    report = ws.status()
    summary = {"schema_version": 1, "scope": "Synthetic deterministic companion demonstration, not an Agent A/B trial",
               "sequence": sequence, "routing": routing, "user_edit_preserved": True, "simulated_records": observed["count"],
               "final_status": report["validation_status"]}
    atomic_json(root / "demo-results.json", summary)
    atomic_json(root / "report.json", report)
    write("report.md", markdown(report))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="A new isolated directory")
    args = parser.parse_args()
    try:
        result = run(args.output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ContractError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
