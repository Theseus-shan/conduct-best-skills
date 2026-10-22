"""Workspace-local explicit preferences and live view; no skill execution."""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import tempfile
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit


class PreferenceError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise PreferenceError(message)


def task_id(value):
    require(isinstance(value, str) and re.fullmatch(r"\w[\w-]{0,63}", value),
            "任务名称可使用 1–64 个中英文字、数字、下划线或连字符")
    require(value.upper().split('.')[0] not in {"CON", "PRN", "AUX", "NUL", *[f"{p}{n}" for p in ("COM", "LPT") for n in range(1, 10)]}, "Reserved task ID")
    return value


def safe_path(root, relative):
    root = Path(root).resolve()
    require(root.is_dir(), "Workspace must exist")
    path = root / relative
    require(path.resolve().is_relative_to(root) and path.resolve() == path.absolute(),
            "Preference path must stay inside this workspace without redirection")
    return path


def location(root, task=None):
    return safe_path(root, f".conduct/tasks/{task_id(task)}/preferences.json" if task is not None else ".conduct/preferences.json")


def empty():
    return {"schema_version": 1, "workflow": {}, "rules": []}


def validate(data):
    require(isinstance(data, dict) and data.get("schema_version") == 1, "Expected preference schema_version 1")
    require(set(data) <= {"schema_version", "workflow", "rules"}, "Unknown preference fields")
    workflow = data.get("workflow", {})
    require(isinstance(workflow, dict) and all(isinstance(k, str) and k.strip() and isinstance(v, str) for k, v in workflow.items()), "workflow must map names to text")
    require(isinstance(data.get("rules", []), list), "rules must be a list")
    ids = set()
    for rule in data.get("rules", []):
        require(isinstance(rule, dict) and set(rule) <= {"id", "when", "skills", "instruction", "enabled", "sentence"}, "Unknown rule fields")
        key = rule.get("id")
        require(isinstance(key, str) and key.strip() and key not in ids, "Rule IDs must be nonempty and unique")
        ids.add(key)
        require(type(rule.get("enabled", True)) is bool, "enabled must be boolean")
        for field in ("when", "skills"):
            values = rule.get(field, [])
            require(isinstance(values, list) and all(isinstance(v, str) and v.strip() for v in values), f"{field} must be a text list")
        if rule.get("enabled", True):
            require(bool(rule.get("when")), "Enabled rules require task types in when")
            require(bool(rule.get("skills") or rule.get("instruction")), "Enabled rules need skills or an instruction")
        require(isinstance(rule.get("instruction", ""), str), "instruction must be text")
        require(isinstance(rule.get("sentence", ""), str), "sentence must be text")
    return data


TYPE_LABELS = {"paper-writing": "写论文", "simulation": "跑仿真", "coding": "写代码", "literature-review": "查文献", "figure": "画图", "*": "做任何工作"}


def rule_sentence(rule):
    if rule.get("sentence"):
        return rule["sentence"]
    condition = "、".join(TYPE_LABELS.get(t, t) for t in rule.get("when", [])) or "处理这项工作"
    skills = " 和 ".join(rule.get("skills", []))
    instruction = rule.get("instruction", "")
    return f"{condition}时，默认使用 {skills}" + (f"，并{instruction}" if instruction else "")


def parse_sentence(sentence, identity):
    require(isinstance(sentence, str) and 0 < len(sentence.strip()) <= 3000, "请写一条不超过 3000 字的工作偏好。")
    sentence = sentence.strip().rstrip('。')
    # Deliberately bounded grammar: unsupported requests remain unsaved, never guessed.
    match = re.fullmatch(r"(?:我希望|我想|请)?\s*(?:当我|当|在)?(.+?)(?:的时候|过程中|任务中|时)[，,：:\s]*(?:请|我希望)?\s*(?:默认|优先)?\s*(?:调用|使用|用)\s*(.+)", sentence)
    require(match is not None, "请按自然语言写清场景和能力，例如：写论文时，默认使用 Anti-Defensive Writing 和 nature-writing，并保留必要局限。也可直接在 Codex 中描述更复杂的偏好。")
    condition, tail = match.groups()
    parts = re.split(r"[，,；;]\s*(?:并且|并|同时|要求)\s*", tail, maxsplit=1)
    skills_text, instruction = parts[0], parts[1] if len(parts) > 1 else ""
    require(not re.search(r"(?:不要|不用|不调用|不使用|时[，,]?\s*(?:默认)?(?:使用|调用|用))", skills_text), "一条卡片只描述一种工作偏好；停用请用卡片开关，另一种工作请另加一条。")
    require(not re.search(r"(?:时|的时候)[，,]?\s*(?:默认)?(?:使用|调用|用)", instruction), "检测到多个工作场景，请分别添加偏好卡片。")
    skills = [s.strip().lstrip('$') for s in re.split(r"\s*(?:以及|和|及|、|，|,|\s+&\s+)\s*", skills_text) if s.strip()]
    require(skills and all(len(s) <= 150 for s in skills), "请填写希望调用的技能或能力名称。")
    known = [(r"论文|写作|文章", "paper-writing"), (r"仿真|模拟实验", "simulation"), (r"代码|编程|软件开发", "coding"),
             (r"文献|检索", "literature-review"), (r"画图|绘图|图表", "figure"), (r"任何工作|所有工作|全部任务", "*")]
    matches = [kind for pattern, kind in known if re.search(pattern, condition)]
    require(len(matches) <= 1, "这条偏好包含多个可能的工作类型，请拆成卡片，或在 Codex 中确认具体适用范围。")
    return {"id": identity, "when": matches or [condition.strip()], "skills": list(dict.fromkeys(skills)),
            "instruction": instruction.strip(), "enabled": True, "sentence": sentence}


def edit_rule(root, body):
    import uuid
    task = body.get("task")
    document = read(root, task)
    require(document["revision"] == body.get("revision"), "偏好已被其他地方修改，请重新载入后再保存。")
    data = document["data"]
    identity = body.get("id") or 'rule-' + uuid.uuid4().hex[:12]
    require(isinstance(identity, str) and identity.strip(), "无效偏好标识")
    existing = next((r for r in data.get("rules", []) if r["id"] == identity), None)
    if body.get("action") == "toggle":
        require(existing is not None, "请先选择该范围内已有的偏好。")
        require(type(body.get("enabled")) is bool, "请指定启用或停用。")
        existing["enabled"] = body["enabled"]
    else:
        require(body.get("action") == "save", "未知偏好操作")
        rule = parse_sentence(body.get("sentence"), identity)
        if "enabled" in body:
            require(type(body["enabled"]) is bool, "请指定启用或停用。")
            rule["enabled"] = body["enabled"]
        if existing:
            if "enabled" not in body:
                rule["enabled"] = existing.get("enabled", True)
            existing.clear()
            existing.update(rule)
        else:
            data.setdefault("rules", []).append(rule)
    return save(root, data, task, body["revision"])


def revision(raw):
    return hashlib.sha256(raw).hexdigest()


def read(root, task=None):
    path = location(root, task)
    if not path.exists():
        return {"path": path.relative_to(Path(root).resolve()).as_posix(), "revision": "missing", "data": empty()}
    raw = path.read_bytes()
    require(len(raw) <= 256_000, "Preference file exceeds 256 KB")
    return {"path": path.relative_to(Path(root).resolve()).as_posix(), "revision": revision(raw),
            "data": validate(json.loads(raw.decode("utf-8-sig")))}


def atomic_write(path, data):
    fd, temporary = tempfile.mkstemp(prefix=".preferences-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def save(root, data, task=None, expected=None):
    validate(data)
    require(len(json.dumps(data, ensure_ascii=False).encode("utf-8")) <= 256_000, "Preference file exceeds 256 KB")
    path = location(root, task)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = safe_path(root, ".conduct/preferences.lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise PreferenceError("Preferences are being edited; retry after the current save") from exc
    try:
        os.close(fd)
        current = read(root, task)
        require(expected is not None and current["revision"] == expected, "Preferences changed since loading; reload before saving")
        atomic_write(path, data)
    finally:
        lock.unlink()
    return read(root, task)


def initialize(root, task=None):
    current = read(root, task)
    if current["revision"] != "missing":
        return current
    return save(root, empty(), task, expected="missing")


def normalized(value):
    return re.sub(r"[\W_]", "", value.casefold())


def resolve(root, task=None, types=(), excluded=()):
    root = Path(root).resolve()
    project = read(root)
    overlay = read(root, task) if task else None
    workflow, rules, overridden = {}, {}, []
    for source, document in (("project", project), ("task", overlay)):
        if document is None:
            continue
        for key, value in document["data"].get("workflow", {}).items():
            workflow[key] = {"value": value, "source": source}
        for rule in document["data"].get("rules", []):
            if rule["id"] in rules:
                overridden.append({**rules[rule["id"]], "status": "overridden"})
            rules[rule["id"]] = {**rule, "source": source, "path": document["path"]}
    requested, omitted = [], {normalized(s) for s in excluded}
    for rule in rules.values():
        rule["sentence"] = rule_sentence(rule)
        matching = "*" in rule.get("when", []) or bool(set(types) & set(rule.get("when", [])))
        state = "disabled" if not rule.get("enabled", True) else "configured" if not types else "active" if matching else "not_matched"
        rule["status"] = state
        rule["selected_skills"], rule["excluded_skills"] = [], []
        if state == "active":
            for skill in rule.get("skills", []):
                if normalized(skill) in omitted:
                    rule["excluded_skills"].append(skill)
                else:
                    rule["selected_skills"].append(skill)
                    if normalized(skill) not in {normalized(x) for x in requested}:
                        requested.append(skill)
            if rule["excluded_skills"]:
                rule["status"] = "partially_excluded" if rule["selected_skills"] else "prompt_excluded"
    tasks = safe_path(root, ".conduct/tasks")
    available = []
    if tasks.is_dir():
        for folder in sorted(tasks.iterdir()):
            if folder.is_symlink() or not folder.is_dir():
                continue
            try:
                path = location(root, folder.name)
                if path.is_file():
                    available.append(folder.name)
            except PreferenceError:
                continue
    return {"workspace": str(root), "project": project, "task": task, "overlay": overlay,
            "task_types": list(types), "prompt_exclusions": list(excluded), "workflow": workflow,
            "rules": list(rules.values()), "overridden": overridden, "requested_skills": requested,
            "tasks": available, "invocation_status": "NOT_CHECKED", "scope": "workspace-only"}


def context(root, task=None, types=(), excluded=()):
    result = resolve(root, task, types, excluded)
    path = safe_path(root, ".conduct/preferences-context.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(path, {"task": task, "task_types": list(types), "prompt_exclusions": list(excluded),
                        "recorded_at": datetime.now(timezone.utc).isoformat()})
    return result


def view(root, selected=None, types=None):
    path = safe_path(root, ".conduct/preferences-context.json")
    current = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    task = current.get("task") if selected is None else selected or None
    same_task = task == current.get("task")
    active_types = current.get("task_types", []) if types is None and same_task else types or []
    excluded = current.get("prompt_exclusions", []) if same_task else []
    require(isinstance(active_types, list) and all(isinstance(x, str) for x in active_types), "Invalid context task types")
    require(isinstance(excluded, list) and all(isinstance(x, str) for x in excluded), "Invalid context exclusions")
    result = resolve(root, task, active_types, excluded)
    result["context_updated_at"] = current.get("recorded_at") if same_task else None
    from activity import report
    result["activity"] = report(root)
    from harness import dashboard, tasks, execution
    result['harness'] = dashboard(root, task, result['activity']['calls'])
    result['execution'] = execution(root)
    result["tasks"] = sorted(set(result["tasks"]) | set(tasks(root)) | {c["task"] for c in result['activity']["calls"]} | ({task} if task else set()))
    return result


def make_server(root, port=0, home=None):
    root = Path(root).resolve()
    token = secrets.token_urlsafe(24)
    page = Path(__file__).resolve().parent.parent / "assets/preferences.html"

    class Handler(BaseHTTPRequestHandler):
        def workspace(self, query):
            selected = query.get("project", [None])[0]
            if home is None:
                require(selected is None, "This viewer only serves its own workspace")
                return root
            from workbench import project_root, load
            if selected is None:
                selected = next((p["id"] for p in load(home)["projects"] if p["root"] == str(root)), None)
            return project_root(home, selected)

        def log_message(self, *_args):
            pass

        def send(self, status, data, content_type="application/json; charset=utf-8"):
            raw = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(raw)

        def authorized(self):
            return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}" and urlsplit(self.path).path.startswith(f"/{token}/")

        def do_GET(self):
            if not self.authorized():
                return self.send(403, {"error": "Local workspace URL required"})
            parts = urlsplit(self.path)
            try:
                if parts.path == f"/{token}/":
                    return self.send(200, page.read_bytes(), "text/html; charset=utf-8")
                if parts.path not in {f"/{token}/api/preferences", f"/{token}/api/reflection"}:
                    return self.send(404, {"error": "Not found"})
                query = parse_qs(parts.query, keep_blank_values=True)
                workspace = self.workspace(query)
                if parts.path.endswith('/reflection'):
                    from activity import report, markdown
                    return self.send(200, markdown(report(workspace, query.get("task", [None])[0] or None)).encode('utf-8'), "text/markdown; charset=utf-8")
                result = view(workspace, query.get("task", [None])[0], query.get("type"))
                if home is not None:
                    from workbench import overview, load
                    result["projects"] = overview(home)
                    result["project_id"] = next(p["id"] for p in result["projects"] if p["root"] == str(workspace))
                    registry = load(home)
                    result["codex_sync"] = registry.get("codex_sync")
                    result["codex_chats"] = [t for t in registry.get("codex_chats", []) if t["project_id"] == result["project_id"]]
                else:
                    result["projects"], result["project_id"] = [], None
                result["workbench_mode"] = home is not None
                return self.send(200, result)
            except (OSError, ValueError, TypeError, KeyError) as exc:
                return self.send(422, {"error": str(exc)})

        def do_POST(self):
            parts = urlsplit(self.path)
            if not self.authorized() or parts.path not in {f"/{token}/api/preferences", f"/{token}/api/rules", f"/{token}/api/activity", f"/{token}/api/projects", f"/{token}/api/harness"} or self.headers.get("X-Conduct-Edit") != "1":
                return self.send(403, {"error": "Local editor required"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                require(0 < length <= 256_000, "Invalid request size")
                body = json.loads(self.rfile.read(length).decode("utf-8"))
                query = parse_qs(parts.query, keep_blank_values=True)
                if parts.path.endswith('/projects'):
                    require(home is not None, "Start workbench serve to register projects")
                    from workbench import register, unregister
                    require(body.get("action") in {"register", "unregister"}, "Invalid project action")
                    result = register(home, body["root"], body.get("name")) if body["action"] == 'register' else unregister(home, body["id"])
                elif parts.path.endswith('/harness'):
                    from harness import save as save_brief
                    result = save_brief(self.workspace(query), body['task'], body['data'], body.get('revision'))
                elif parts.path.endswith('/rules'):
                    result = edit_rule(self.workspace(query), body)
                elif parts.path.endswith('/activity'):
                    from activity import feedback, set_enabled
                    workspace = self.workspace(query)
                    require(body.get("action") in {"feedback", "enable", "disable"}, "Invalid activity action")
                    result = feedback(workspace, body["call_id"], body["rating"], body.get("note", "")) if body["action"] == 'feedback' else set_enabled(workspace, body["action"] == 'enable')
                else:
                    result = save(self.workspace(query), body["data"], body.get("task"), body.get("revision"))
                return self.send(200, result)
            except (OSError, ValueError, TypeError, KeyError) as exc:
                return self.send(409, {"error": str(exc)})

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    server.preference_url = f"http://127.0.0.1:{server.server_port}/{token}/"
    return server


def add_arguments(parser):
    parser.add_argument("action", choices=["init", "show", "context", "serve"])
    parser.add_argument("--task")
    parser.add_argument("--type", dest="types", action="append", default=[])
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--port", type=int, default=0)


def execute(args):
    if args.action == "init":
        return initialize(args.workspace, args.task)
    if args.action == "context":
        return context(args.workspace, args.task, args.types, args.exclude)
    if args.action == "show":
        return resolve(args.workspace, args.task, args.types, args.exclude)
    initialize(args.workspace)
    with make_server(args.workspace, args.port) as server:
        print(json.dumps({"url": server.preference_url, "workspace": str(Path(args.workspace).resolve()),
                          "message": "Live while this process runs; Ctrl+C to stop"}), flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    return {"status": "stopped"}
