"""Explicit host-reported capability history; never a complete tool interceptor."""
from collections import defaultdict
from datetime import datetime, timezone
import json
import os
import uuid

from preferences import safe_path, task_id, atomic_write, require

EVENTS = {"selected", "loaded", "invoked", "succeeded", "failed", "verified", "feedback"}


def read(root):
    path = safe_path(root, ".conduct/activity.json")
    if not path.exists():
        return {"schema_version": 1, "enabled": False, "events": [], "coverage": "host-recorded-partial"}
    data = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(data, dict) and data.get("schema_version") == 1 and type(data.get("enabled")) is bool
            and isinstance(data.get("events"), list), "Invalid activity record")
    for event in data["events"]:
        require(isinstance(event, dict) and event.get("event") in EVENTS
                and all(isinstance(event.get(k), str) and event[k] for k in ("id", "call_id", "task", "kind", "name", "at")),
                "Invalid activity event")
    return data


def mutate(root, change):
    path = safe_path(root, ".conduct/activity.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = safe_path(root, ".conduct/activity.lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError("Activity record is being updated; retry after the current write") from exc
    try:
        os.close(fd)
        data = read(root)
        result = change(data)
        atomic_write(path, data)
        return result
    finally:
        lock.unlink()


def set_enabled(root, enabled):
    def update(data):
        data["enabled"] = enabled
        return {"enabled": enabled, "coverage": "host-recorded-partial"}
    return mutate(root, update)


def record(root, task, kind, name, event, call_id, note="", evidence=None, rating=None, event_id=None, work="default"):
    task_id(task)
    task_id(work)
    require(kind in {"skill", "tool", "mcp", "agent"}, "Invalid capability kind")
    require(event in EVENTS and isinstance(name, str) and name.strip() and isinstance(call_id, str) and call_id.strip(), "Invalid capability event")
    require(isinstance(note, str) and len(note) <= 2000, "Use a concise note, not full prompts or outputs")
    evidence = evidence or []
    require(isinstance(evidence, list) and all(isinstance(x, str) and x.strip() for x in evidence), "Evidence must be reference strings")
    require(event != "verified" or bool(evidence), "Verified events require evidence references")
    require((event == "feedback" and rating in {"helpful", "unhelpful", "mixed", "unknown"}) or (event != "feedback" and rating is None), "Rating belongs to user feedback only")
    payload = {"id": event_id or str(uuid.uuid4()), "call_id": call_id, "task": task, "work": work, "kind": kind,
               "name": name, "event": event, "note": note, "evidence": evidence, "rating": rating}
    def append(data):
        require(data["enabled"], "Project activity recording is disabled")
        for existing in data["events"]:
            if existing["id"] == payload["id"]:
                require(all(existing.get(k) == v for k, v in payload.items()), "Event ID already identifies different content")
                return existing
        earlier = [e for e in data["events"] if e["call_id"] == call_id]
        require(all((e["task"], e["kind"], e["name"], e.get("work", "default")) == (task, kind, name, work) for e in earlier), "Call ID belongs to another capability or task")
        states = {e["event"] for e in earlier}
        if event in {"succeeded", "failed", "verified", "feedback"}:
            require("invoked" in states, "Outcome requires a recorded actual invocation")
        if event == "verified":
            require("succeeded" in states, "Verification requires a recorded successful operation")
        if event in {"succeeded", "failed"}:
            require(not states.intersection({"succeeded", "failed"}), "Each invocation has one terminal outcome; retries need a new call ID")
        if event != "feedback":
            require(event not in states, "Duplicate lifecycle event; reuse the original event ID for retries")
        from harness import binding
        invocation = next((e for e in earlier if e['event'] == 'invoked'), None)
        payload['brief_revision'] = invocation.get('brief_revision', 'missing') if invocation else binding(root, task)
        payload["at"] = datetime.now(timezone.utc).isoformat()
        data["events"].append(payload)
        return payload
    return mutate(root, append)


def feedback(root, call_id, rating, note=""):
    events = [e for e in read(root)["events"] if e["call_id"] == call_id]
    require(bool(events), "No recorded invocation with this call ID")
    first = events[0]
    return record(root, first["task"], first["kind"], first["name"], "feedback", call_id, note, rating=rating, work=first.get("work", "default"))


def report(root, task=None):
    data = read(root)
    if task is not None:
        task_id(task)
    grouped = defaultdict(list)
    for event in data["events"]:
        if task is None or event["task"] == task:
            grouped[event["call_id"]].append(event)
    calls = []
    for key, events in grouped.items():
        first, states = events[0], {e["event"] for e in events}
        reviews = [e for e in events if e["event"] == "feedback"]
        outcome = "verified" if "verified" in states else "failed" if "failed" in states else "succeeded" if "succeeded" in states else "unknown"
        invocation = next((e for e in events if e['event'] == 'invoked'), first)
        calls.append({"call_id": key, "brief_revision": invocation.get('brief_revision', 'missing'), "work": first.get("work", "default"), "task": first["task"], "kind": first["kind"], "name": first["name"],
                      "invoked": "invoked" in states, "outcome": outcome, "states": list(dict.fromkeys(e["event"] for e in events)),
                      "rating": reviews[-1]["rating"] if reviews else "unknown", "feedback": reviews[-1]["note"] if reviews else "",
                      "evidence": list(dict.fromkeys(x for e in events for x in e.get("evidence", []))),
                      "notes": [e["note"] for e in events if e.get("note") and e["event"] != "feedback"]})
    summaries = {}
    for call in calls:
        key = (call["kind"], call["name"])
        summary = summaries.setdefault(key, {"kind": key[0], "name": key[1], "invocations": 0, "verified": 0, "failed": 0,
                                             "helpful": 0, "unhelpful": 0, "mixed": 0, "unknown_feedback": 0, "tasks": set()})
        if call["invoked"]:
            summary["invocations"] += 1
            summary["tasks"].add(call["task"])
            if call["outcome"] in {"verified", "failed"}:
                summary[call["outcome"]] += 1
            summary["unknown_feedback" if call["rating"] == "unknown" else call["rating"]] += 1
    for item in summaries.values():
        item["tasks"] = sorted(item["tasks"])
    return {"enabled": data["enabled"], "coverage": "host-recorded-partial", "calls": calls,
            "capabilities": list(summaries.values()), "recorded_events": sum(len(es) for es in grouped.values()),
            "limits": "Only explicitly recorded events; outcomes and evidence locators are host-reported. No causal quality ranking or complete capture is claimed."}


def markdown(result):
    def cell(value):
        return str(value).replace("|", "\\|").replace("\n", " ")
    rows = ["# 项目调用与复盘", "", "覆盖范围：仅 Agent 明确记录的事件；无记录不等于没有调用。验证结论需复核所列证据。", "",
            "| 工作 | 任务 | 能力 | 实际调用 | 结果 | 用户反馈 | 证据 |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for call in result["calls"]:
        rows.append("| " + " | ".join(map(cell, [call["work"], call["task"], call["kind"] + ": " + call["name"], "是" if call["invoked"] else "仅选择/加载",
                                                   call["outcome"], call["rating"] + (": " + call["feedback"] if call["feedback"] else ""), "; ".join(call["evidence"])])) + " |")
    rows.extend(["", "复盘时结合任务目标、失败原因、证据范围与用户反馈；调用频率不代表好用，运行成功不代表用户满意。", "偏好调整先作为建议，不自动改写项目默认，不迁移到其他项目。"])
    return "\n".join(rows) + "\n"


def add_arguments(parser):
    parser.add_argument("action", choices=["enable", "disable", "record", "feedback", "report"])
    parser.add_argument("--task")
    parser.add_argument("--work", default="default")
    parser.add_argument("--kind", choices=["skill", "tool", "mcp", "agent"])
    parser.add_argument("--name")
    parser.add_argument("--event", choices=sorted(EVENTS - {"feedback"}))
    parser.add_argument("--call-id")
    parser.add_argument("--event-id")
    parser.add_argument("--note", default="")
    parser.add_argument("--evidence", action="append", default=[])
    parser.add_argument("--rating", choices=["helpful", "unhelpful", "mixed", "unknown"])
    parser.add_argument("--format", choices=["json", "markdown"], default="json")


def execute(args):
    if args.action in {"enable", "disable"}:
        return set_enabled(args.workspace, args.action == "enable")
    if args.action == "record":
        return record(args.workspace, args.task, args.kind, args.name, args.event, args.call_id,
                      args.note, args.evidence, event_id=args.event_id, work=args.work)
    if args.action == "feedback":
        return feedback(args.workspace, args.call_id, args.rating, args.note)
    result = report(args.workspace, args.task)
    return markdown(result) if args.format == "markdown" else result
