"""Run runtime regressions and optionally save a portable, source-bound result."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RecordedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.records.append({"id": test.id(), "status": "PASS"})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.records.append({"id": test.id(), "status": "FAIL"})

    def addError(self, test, err):
        super().addError(test, err)
        self.records.append({"id": test.id(), "status": "ERROR"})

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.records.append({"id": test.id(), "status": "SKIP", "reason": reason})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="Optional JSON result path")
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    result = unittest.TextTestRunner(verbosity=2, resultclass=RecordedResult).run(suite)
    paths = sorted({"scripts/validate_runtime.py"} | {
        p.relative_to(ROOT).as_posix()
        for folder in (ROOT / "tests", ROOT / "skills/conduct-best-skills")
        for p in folder.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix in {".py", ".md", ".yaml"}
    })
    report = {"schema_version": 1, "run_at_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "Deterministic local companion regressions; not the 204 Agent behavior cases or A/B evaluation",
              "environment": {"python": platform.python_version(), "system": platform.system()},
              "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
              "skipped": len(result.skipped), "successful": result.wasSuccessful(), "cases": result.records,
              "source_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in paths}}
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
