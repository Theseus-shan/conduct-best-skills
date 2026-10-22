"""Local evidence and recovery companion. Python 3.10+, standard library only.

This is not a command sandbox or an agent. Commands run only via `verify`;
the host must review the contract and authorize each command's actual effects.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time


class ContractError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ContractError(message)


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def atomic_json(path, value):
    fd, name = tempfile.mkstemp(prefix=".conduct-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def local_path(root, relative):
    require(isinstance(relative, str) and relative.strip(), "Path must be a nonempty relative string")
    # Both separators are checked on every platform for portable contracts.
    parts = relative.replace("\\", "/").split("/")
    require(not relative.startswith(("/", "\\")) and not re.match(r"^[A-Za-z]:", relative)
            and ".." not in parts and ":" not in relative, f"Unsafe relative path: {relative}")
    path = root.joinpath(*parts)
    require(path.resolve().is_relative_to(root), f"Path escapes workspace: {relative}")
    require(path.resolve() == path.absolute(), f"Redirected path is unsupported: {relative}")
    return path


def strings(value, label, nonempty=False):
    require(isinstance(value, list) and all(isinstance(x, str) and x.strip() for x in value),
            f"{label} must be a list of nonempty strings")
    require(len(value) == len(set(value)), f"{label} contains duplicates")
    require(not nonempty or bool(value), f"{label} cannot be empty")


def identifiers(items, label):
    require(isinstance(items, list) and items, f"{label} must be a nonempty list")
    found = set()
    for item in items:
        require(isinstance(item, dict), f"Invalid {label} entry")
        key = item.get("id")
        require(isinstance(key, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", key),
                f"Invalid {label} ID: {key}")
        require(key not in found, f"Duplicate {label} ID: {key}")
        found.add(key)
    return found


def validate(contract, root):
    require(isinstance(contract, dict) and contract.get("schema_version") == 1, "Expected schema_version 1")
    require(isinstance(contract.get("goal"), str) and contract["goal"].strip(), "Missing goal")
    tasks, criteria = contract.get("tasks"), contract.get("criteria")
    task_ids, criterion_ids = identifiers(tasks, "task"), identifiers(criteria, "criterion")
    require(any(c.get("kind", "Mandatory") == "Mandatory" for c in criteria), "At least one Mandatory criterion is required")
    for c in criteria:
        require(isinstance(c.get("requirement"), str) and c["requirement"].strip(), "Missing criterion requirement")
        require(c.get("kind", "Mandatory") in {"Mandatory", "Quality", "Aspirational"}, "Invalid criterion kind")
        check = c.get("check", {})
        require(isinstance(check, dict), "check must be an object")
        argv = check.get("argv")
        require(isinstance(argv, list) and argv and all(isinstance(x, str) and x for x in argv), "check.argv must be a nonempty argument list")
        require(argv[0].lower() not in {"cmd", "cmd.exe", "powershell", "pwsh", "sh", "bash"},
                "Use a direct executable or a reviewed script, not an inline shell")
        for key, default, maximum in (("timeout_seconds", 60, 3600), ("max_attempts", 3, 100)):
            n = check.get(key, default)
            require(type(n) is int and 1 <= n <= maximum, f"Invalid {key}")
        for field in ("artifacts", "inputs"):
            strings(c.get(field), f"{c['id']}.{field}", nonempty=True)
            for relative in c[field]:
                local_path(root, relative)
    covered = set()
    for task in tasks:
        require(isinstance(task.get("objective"), str) and task["objective"].strip(), "Missing task objective")
        for key in ("depends_on", "criteria", "needs"):
            strings(task.get(key, []), f"{task['id']}.{key}", nonempty=key == "criteria")
        require(set(task.get("depends_on", [])) <= task_ids, "Unknown task dependency")
        require(set(task["criteria"]) <= criterion_ids, "Unknown criterion mapping")
        require(not covered.intersection(task["criteria"]), "Each criterion must have exactly one owning task")
        covered.update(task["criteria"])
    require(covered == criterion_ids, "Every criterion must be mapped to a task")
    pending = {t["id"]: set(t.get("depends_on", [])) for t in tasks}
    done = set()
    while pending:
        ready = [k for k, deps in pending.items() if deps <= done]
        require(ready, "Task dependency cycle")
        for key in ready:
            done.add(key)
            del pending[key]
    return contract


def starter_contract(goal, requirement, artifacts, inputs, argv, timeout=60, attempts=3):
    """Build a real one-task contract from explicit facts, without placeholder checks."""
    command = list(argv)
    if command and command[0] == "--":
        command.pop(0)
    require(command, "Provide the real check command after --; no default passing check is generated")
    return {"schema_version": 1, "goal": goal,
            "tasks": [{"id": "work", "objective": goal, "depends_on": [], "criteria": ["acceptance"]}],
            "criteria": [{"id": "acceptance", "kind": "Mandatory", "requirement": requirement,
                          "artifacts": artifacts, "inputs": inputs,
                          "check": {"argv": command, "timeout_seconds": timeout, "max_attempts": attempts}}]}


class Workspace:
    def __init__(self, root):
        self.root = Path(root).resolve()
        require(self.root.is_dir(), "Workspace must exist")
        self.folder = local_path(self.root, ".conduct")
        self.state_path = local_path(self.root, ".conduct/state.json")
        self.contract_path = local_path(self.root, ".conduct/contract.json")

    @contextmanager
    def locked(self):
        require(self.folder.is_dir(), "Run init first")
        lock = local_path(self.root, ".conduct/lock")
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            raise ContractError("Workspace is locked. Inspect the recorded PID and running process before removing a stale lock.")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(json.dumps({"pid": os.getpid(), "created_at": timestamp()}))
            yield
        finally:
            lock.unlink()

    def initialize(self, contract):
        validate(contract, self.root)
        require(not self.folder.exists(), ".conduct already exists; initialization never overwrites it")
        self.folder.mkdir()
        atomic_json(self.contract_path, contract)
        atomic_json(self.state_path, {"schema_version": 1, "attempts": [], "operations": {}, "events": []})

    def load(self):
        contract = validate(read_json(self.contract_path), self.root)
        state = read_json(self.state_path)
        require(isinstance(state, dict) and state.get("schema_version") == 1
                and isinstance(state.get("attempts"), list) and isinstance(state.get("operations"), dict)
                and isinstance(state.get("events"), list), "Invalid state file")
        return contract, state

    def save(self, state):
        atomic_json(self.state_path, state)

    def snapshot(self, criterion):
        result = {}
        for relative in sorted(set(criterion["inputs"] + criterion["artifacts"])):
            path = local_path(self.root, relative)
            result[relative] = digest(path.read_bytes()) if path.is_file() else None
        return result

    def dependency_signature(self, contract, state, criterion_id):
        tasks = {t["id"]: t for t in contract["tasks"]}
        owner = next(t for t in tasks.values() if criterion_id in t["criteria"])
        ancestors, pending = set(), list(owner.get("depends_on", []))
        while pending:
            key = pending.pop()
            if key not in ancestors:
                ancestors.add(key)
                pending.extend(tasks[key].get("depends_on", []))
        ids = {c for t in ancestors for c in tasks[t]["criteria"]}
        signature = {}
        for c in contract["criteria"]:
            if c["id"] not in ids:
                continue
            previous = [a for a in state["attempts"] if a["criterion"] == c["id"]]
            last = previous[-1] if previous else None
            log = local_path(self.root, last["log"]) if last else None
            signature[c["id"]] = {"files": self.snapshot(c), "attempt": digest(canonical(last)),
                                   "log": digest(log.read_bytes()) if log and log.is_file() else None}
        return signature

    def operation_signature(self, contract, state, criterion_id):
        owner = next(t["id"] for t in contract["tasks"] if criterion_id in t["criteria"])
        return digest(canonical({k: op for k, op in state["operations"].items() if op["task"] == owner}))

    def evaluate(self, contract, state):
        rows = []
        contract_hash = digest(canonical(contract))
        for c in contract["criteria"]:
            attempts = [a for a in state["attempts"] if a["criterion"] == c["id"]]
            last = attempts[-1] if attempts else None
            status, reason = "UNTESTED", "No executed check"
            current = self.snapshot(c)
            if last:
                status, reason = last["status"], last["reason"]
                if last["contract_hash"] != contract_hash or last["after"] != current:
                    status, reason = "STALE", "Contract or tracked files changed; rerun the check"
                elif last.get("dependencies") != self.dependency_signature(contract, state, c["id"]):
                    status, reason = "STALE", "Upstream files or verification evidence changed; rerun the dependent check"
                elif last.get("operations") != self.operation_signature(contract, state, c["id"]):
                    status, reason = "STALE", "Operation state changed since verification; check the resulting artifact"
                elif status == "RUNNING":
                    status, reason = "INCONCLUSIVE", "Interrupted check; inspect effects before recovery"
                else:
                    log = last.get("log")
                    log_path = local_path(self.root, log) if log else None
                    if not log_path or not log_path.is_file() or digest(log_path.read_bytes()) != last.get("log_hash"):
                        status, reason = "INCONCLUSIVE", "Evidence log missing or modified"
            if any(v is None for v in current.values()):
                status, reason = "UNTESTED", "Tracked input or artifact is missing"
            rows.append({"id": c["id"], "requirement": c["requirement"], "kind": c.get("kind", "Mandatory"),
                         "status": status, "reason": reason, "attempts": len(attempts),
                         "remaining_attempts": max(0, c["check"].get("max_attempts", 3) - len(attempts)),
                         "evidence": last.get("log") if last else None, "files": current,
                         "method": last.get("argv") if last else None,
                         "returncode": last.get("returncode") if last else None,
                         "elapsed_seconds": last.get("elapsed_seconds") if last else None})
        return rows

    def status(self):
        contract, state = self.load()
        rows = self.evaluate(contract, state)
        by_id = {r["id"]: r for r in rows}
        mandatory = [r for r in rows if r["kind"] == "Mandatory"]
        unknown = [op for op in state["operations"].values() if op["status"] == "UNKNOWN"]
        overall = ("FAILED" if any(r["status"] == "FAIL" for r in mandatory) else
                   "VERIFIED" if all(r["status"] == "PASS" for r in mandatory) else "PARTIALLY_VERIFIED")
        tasks, done = [], set()
        pending = list(contract["tasks"])
        while pending:
            task = next(t for t in pending if set(t.get("depends_on", [])) <= {x["id"] for x in tasks})
            pending.remove(task)
            checks = [by_id[k] for k in task["criteria"] if by_id[k]["kind"] == "Mandatory"]
            if not checks:
                checks = [by_id[k] for k in task["criteria"]]
            deps = set(task.get("depends_on", []))
            unresolved = [op["id"] for op in unknown if op["task"] == task["id"]]
            if unresolved:
                value, action = "BLOCKED", "Reconcile unknown operations: " + ", ".join(unresolved)
            elif not deps <= done:
                value, action = "WAITING", "Complete dependencies: " + ", ".join(sorted(deps - done))
            elif all(r["status"] == "PASS" for r in checks):
                value, action = "VERIFIED", "No action required"
                done.add(task["id"])
            elif any(r["remaining_attempts"] == 0 and r["status"] != "PASS" for r in checks):
                value, action = "LIMIT_REACHED", "Inspect evidence; revise the approved recovery plan before further attempts"
            else:
                value, action = "READY", "Implement or repair, then verify: " + ", ".join(r["id"] for r in checks if r["status"] != "PASS")
            tasks.append({"id": task["id"], "objective": task["objective"], "status": value, "next_action": action})
        if unknown:
            overall = "BLOCKED"
        return {"goal": contract["goal"], "validation_status": overall,
                "task_completion": "COMPLETE" if all(t["status"] == "VERIFIED" for t in tasks) else "INCOMPLETE",
                "criteria": rows, "tasks": tasks, "unknown_operations": unknown}

    def verify(self, criterion_id):
        with self.locked():
            contract, state = self.load()
            criterion = next((c for c in contract["criteria"] if c["id"] == criterion_id), None)
            require(criterion is not None, f"Unknown criterion: {criterion_id}")
            report = self.status()
            owners = [t for t in contract["tasks"] if criterion_id in t["criteria"]]
            task_status = {t["id"]: t["status"] for t in report["tasks"]}
            require(all(task_status[t["id"]] not in {"WAITING", "BLOCKED"} for t in owners),
                    "Check is blocked by a dependency or unknown operation")
            existing = [a for a in state["attempts"] if a["criterion"] == criterion_id]
            require(len(existing) < criterion["check"].get("max_attempts", 3), "Attempt budget exhausted")
            require(not any(a["status"] == "RUNNING" for a in existing),
                    "Interrupted check must be reconciled with recover before rerunning")
            before = self.snapshot(criterion)
            require(all(v is not None for v in before.values()), "All tracked files must exist before verification")
            argv = [sys.executable if x == "{python}" else x for x in criterion["check"]["argv"]]
            number = len(state["attempts"]) + 1
            log_name = f".conduct/check-{number:04d}.log"
            log_path = local_path(self.root, log_name)
            require(not log_path.exists(), "Evidence log already exists; inspect state before recovery")
            record = {"criterion": criterion_id, "contract_hash": digest(canonical(contract)),
                      "dependencies": self.dependency_signature(contract, state, criterion_id),
                      "operations": self.operation_signature(contract, state, criterion_id),
                      "before": before, "after": before, "argv": argv, "started_at": timestamp(),
                      "status": "RUNNING", "reason": "Check started", "log": log_name}
            state["attempts"].append(record)
            self.save(state)  # Checkpoint precedes execution, so an interruption cannot be replayed silently.
            start = time.monotonic()
            returncode, timeout, error = None, False, None
            with log_path.open("xb") as output:
                try:
                    result = subprocess.run(argv, cwd=self.root, stdout=output, stderr=subprocess.STDOUT,
                                            stdin=subprocess.DEVNULL, shell=False,
                                            timeout=criterion["check"].get("timeout_seconds", 60))
                    returncode = result.returncode
                except subprocess.TimeoutExpired:
                    timeout = True
                    output.write(b"\n[conduct] Direct process timed out. Inspect any child processes and side effects.\n")
                except OSError as exc:
                    error = str(exc)
                    output.write(("\n[conduct] " + error + "\n").encode("utf-8"))
            after = self.snapshot(criterion)
            same_contract = digest(canonical(read_json(self.contract_path))) == record["contract_hash"]
            if timeout or error:
                outcome, reason = "INCONCLUSIVE", "Timeout; reconcile effects before retry" if timeout else "Could not execute check"
            elif (before != after or not same_contract or
                  record["dependencies"] != self.dependency_signature(contract, state, criterion_id)):
                outcome, reason = "INCONCLUSIVE", "Tracked files, dependencies or contract changed during verification"
            elif returncode == 0:
                outcome, reason = "PASS", "Configured check passed on unchanged tracked files"
            else:
                outcome, reason = "FAIL", f"Configured check exited {returncode}"
            record.update(status=outcome, reason=reason, after=after, returncode=returncode,
                          elapsed_seconds=round(time.monotonic() - start, 4), ended_at=timestamp(),
                          log_hash=digest(log_path.read_bytes()))
            if timeout:
                for task in owners:
                    key = f"timeout-{number}-{task['id']}"
                    state["operations"][key] = {"id": key, "task": task["id"], "status": "UNKNOWN",
                                                "note": "Check timeout; confirm process termination and effects", "created_at": timestamp()}
            self.save(state)
            return record

    def operation(self, key, task_id=None, outcome=None, note=None):
        require(bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,127}", key)), "Invalid operation ID")
        require(isinstance(note, str) and note.strip(), "A factual note or observation is required")
        with self.locked():
            contract, state = self.load()
            if outcome is None:
                require(task_id in {t["id"] for t in contract["tasks"]}, "Unknown task")
                require(key not in state["operations"], "Operation ID already recorded; inspect it instead of replaying")
                state["operations"][key] = {"id": key, "task": task_id, "status": "UNKNOWN", "note": note, "created_at": timestamp()}
            else:
                require(outcome in {"SUCCEEDED", "NOT_APPLIED", "FAILED"}, "Invalid observed outcome")
                require(key in state["operations"] and state["operations"][key]["status"] == "UNKNOWN", "No matching unknown operation")
                state["operations"][key].update(status=outcome, observation=note, reconciled_at=timestamp())
            state["events"].append({"type": "operation", "id": key, "outcome": outcome or "UNKNOWN", "at": timestamp()})
            self.save(state)
            return state["operations"][key]

    def verify_ready(self):
        """Check each eligible non-PASS criterion at most once; do not retry failures."""
        attempted, records, refused = set(), [], []
        while True:
            contract, _ = self.load()
            report = self.status()
            tasks = {t["id"]: t["status"] for t in report["tasks"]}
            rows = {c["id"]: c for c in report["criteria"]}
            selected = None
            for task in contract["tasks"]:
                if tasks[task["id"]] in {"BLOCKED", "WAITING"}:
                    continue
                for key in task["criteria"]:
                    row = rows[key]
                    if key not in attempted and row["status"] != "PASS" and row["remaining_attempts"] > 0:
                        selected = key
                        break
                if selected:
                    break
            if selected is None:
                break
            attempted.add(selected)
            try:
                records.append(self.verify(selected))
            except ContractError as exc:
                refused.append({"criterion": selected, "reason": str(exc)})
        current = self.status()
        return {"checks": records, "refused": refused, "validation_status": current["validation_status"],
                "task_completion": current["task_completion"], "tasks": current["tasks"], "criteria": current["criteria"]}

    def recover(self, note):
        require(isinstance(note, str) and note.strip(), "Recovery requires an observation of process/effect state")
        with self.locked():
            _, state = self.load()
            count = 0
            for attempt in state["attempts"]:
                if attempt["status"] == "RUNNING":
                    attempt.update(status="INCONCLUSIVE", reason="Interrupted check reconciled: " + note)
                    log = local_path(self.root, attempt["log"])
                    attempt["log_hash"] = digest(log.read_bytes()) if log.is_file() else None
                    count += 1
            state["events"].append({"type": "recover", "note": note, "count": count, "at": timestamp()})
            self.save(state)
            return {"recovered_checks": count, "note": note}


def route(contract, catalog):
    """Pure routing of host-observed facts; never probes, installs, or calls a tool."""
    require(isinstance(catalog, dict), "Catalog must be an object")
    capabilities = catalog.get("capabilities", [])
    if capabilities:
        identifiers(capabilities, "capability")
    else:
        require(capabilities == [], "capabilities must be a list")
    allowed = catalog.get("allowed_effects", ["READ_ONLY"])
    strings(allowed, "allowed_effects")
    for cap in capabilities:
        strings(cap.get("provides", []), "provides")
        require(cap.get("effect") in {"READ_ONLY", "MUTATING", "HIGH_IMPACT"}, "Invalid capability effect")
        score = cap.get("preference", 0)
        require(type(score) in (int, float) and math.isfinite(score), "Preference must be finite")
    result = []
    for task in contract["tasks"]:
        needs = set(task.get("needs", []))
        candidates, rejected = [], []
        for cap in capabilities:
            reasons = []
            if cap.get("available") is not True:
                reasons.append("availability not confirmed")
            if not isinstance(cap.get("observation"), str) or not cap["observation"].strip():
                reasons.append("missing host observation")
            if cap["effect"] not in allowed:
                reasons.append("effect outside declared allowance")
            if cap.get("constraints_met") is not True:
                reasons.append("hard constraints not confirmed")
            if not needs <= set(cap.get("provides", [])):
                reasons.append("missing required capabilities")
            if reasons:
                rejected.append({"id": cap["id"], "reasons": reasons})
            else:
                candidates.append(cap)
        candidates.sort(key=lambda c: (-c.get("preference", 0), c["id"]))
        result.append({"task": task["id"], "selected": candidates[0]["id"] if candidates and needs else None,
                       "status": "SELECTED" if candidates and needs else "NATIVE" if not needs else "UNAVAILABLE",
                       "eligible": [c["id"] for c in candidates], "rejected": rejected})
    return result


def markdown(report):
    def clean(value):
        return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")
    lines = ["# Task evidence report", "", clean(report["goal"]), "",
             f"Validation: **{report['validation_status']}** · Task: **{report['task_completion']}**", "",
             "| Criterion | Status | Attempts left | Evidence | Reason |", "| --- | --- | ---: | --- | --- |"]
    for r in report["criteria"]:
        lines.append(f"| {r['id']}: {clean(r['requirement'])} | {r['status']} | {r['remaining_attempts']} | {clean(r['evidence'] or 'none')} | {clean(r['reason'])} |")
    lines += ["", "## Next actions", ""]
    lines += [f"- {t['id']} ({t['status']}): {clean(t['next_action'])}" for t in report["tasks"]]
    lines += ["", "## Current file versions", "", "| Criterion | File | SHA-256 |", "| --- | --- | --- |"]
    for row in report["criteria"]:
        lines += [f"| {row['id']} | {clean(path)} | {sha or 'MISSING'} |" for path, sha in row["files"].items()]
    lines += ["", "## Evidence scope", "", "PASS applies only to the configured checks and tracked files. Review test coverage and all untracked external inputs separately.", ""]
    return "\n".join(lines)


def next_steps(report):
    lines = [report["goal"], f"{report['validation_status']} / {report['task_completion']}"]
    for task in report["tasks"]:
        if task["status"] != "VERIFIED":
            lines.append(f"- {task['id']}: {task['next_action']}")
    for row in report["criteria"]:
        if row["status"] != "PASS":
            lines.append(f"  {row['id']} [{row['kind']}, {row['status']}]: {row['reason']} "
                         f"(attempts left: {row['remaining_attempts']}; evidence: {row['evidence'] or 'none'})")
    if report["task_completion"] == "COMPLETE":
        lines.append("Required work is complete; deliver within the recorded evidence scope.")
    return "\n".join(lines)


def main(argv=None):
    # Machine-readable reports must round-trip non-ASCII projects on Windows too.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=".", help="Project root; state is stored in .conduct/")
    sub = parser.add_subparsers(dest="command", required=True)
    discovery_parser = sub.add_parser("discover", help="Discover Skill metadata without installing or executing candidates")
    from discovery import add_arguments as discovery_arguments, execute as discover_execute
    from discovery_core import DiscoveryError
    discovery_arguments(discovery_parser)
    init = sub.add_parser("init", help="Validate and save a local contract; never overwrite")
    init.add_argument("--contract", required=True)
    start = sub.add_parser("start", help="Create a one-task contract from a goal, tracked files and a real check")
    start.add_argument("--goal", required=True)
    start.add_argument("--requirement", required=True)
    start.add_argument("--artifact", action="append", required=True)
    start.add_argument("--input", action="append", required=True)
    start.add_argument("--timeout", type=int, default=60)
    start.add_argument("--attempts", type=int, default=3)
    start.add_argument("check", nargs=argparse.REMAINDER, help="The reviewed check argv after --")
    sub.add_parser("status", help="Rehash files and return current evidence and next actions")
    next_parser = sub.add_parser("next", help="Show a compact, freshly checked recovery point")
    next_parser.add_argument("--format", choices=["text", "json"], default="text")
    ready = sub.add_parser("verify-ready", help="Run eligible non-PASS checks once in dependency order")
    ready.add_argument("--execute", action="store_true")
    check = sub.add_parser("verify", help="Execute a reviewed check, recording version-bound evidence")
    check.add_argument("criterion")
    check.add_argument("--execute", action="store_true", help="Required acknowledgement that the command was reviewed")
    routing = sub.add_parser("route", help="Filter and rank host-observed capabilities")
    routing.add_argument("--catalog", required=True)
    begin = sub.add_parser("begin", help="Record an operation identity before an external write")
    begin.add_argument("id")
    begin.add_argument("--task", required=True)
    begin.add_argument("--note", required=True)
    resolve = sub.add_parser("reconcile", help="Record observed outcome; does not repeat an operation")
    resolve.add_argument("id")
    resolve.add_argument("--outcome", choices=["SUCCEEDED", "NOT_APPLIED", "FAILED"], required=True)
    resolve.add_argument("--note", required=True)
    recovery = sub.add_parser("recover", help="Reconcile interrupted checks after checking process/effect state")
    recovery.add_argument("--note", required=True)
    report_parser = sub.add_parser("report", help="Print a fresh report without modifying files")
    report_parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    args = parser.parse_args(argv)
    try:
        ws = Workspace(args.workspace)
        if args.command == "discover":
            try:
                return discover_execute(args)
            except DiscoveryError as exc:
                raise ContractError(f"{exc.code}: {exc}") from exc
        elif args.command == "init":
            ws.initialize(read_json(Path(args.contract)))
            result = ws.status()
        elif args.command == "start":
            ws.initialize(starter_contract(args.goal, args.requirement, args.artifact, args.input,
                                           args.check, args.timeout, args.attempts))
            result = ws.status()
        elif args.command == "verify-ready":
            require(args.execute, "Review all configured checks and effects, then supply --execute within existing authorization")
            result = ws.verify_ready()
        elif args.command == "verify":
            require(args.execute, "Review the command and its effects, then supply --execute within existing authorization")
            result = ws.verify(args.criterion)
        elif args.command == "route":
            contract, _ = ws.load()
            result = route(contract, read_json(Path(args.catalog)))
        elif args.command == "begin":
            result = ws.operation(args.id, task_id=args.task, note=args.note)
        elif args.command == "reconcile":
            result = ws.operation(args.id, outcome=args.outcome, note=args.note)
        elif args.command == "recover":
            result = ws.recover(args.note)
        else:
            result = ws.status()
            if args.command == "next" and args.format == "text":
                print(next_steps(result))
                return 0 if result["validation_status"] == "VERIFIED" and result["task_completion"] == "COMPLETE" else 1
            if args.command == "report" and args.format == "markdown":
                print(markdown(result))
                return 0 if result["validation_status"] == "VERIFIED" and result["task_completion"] == "COMPLETE" else 1
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.command == "verify":
            return 0 if result["status"] == "PASS" else 1
        if args.command in {"status", "report", "next", "verify-ready"}:
            return 0 if result["validation_status"] == "VERIFIED" and result["task_completion"] == "COMPLETE" else 1
        return 0
    except (ContractError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
