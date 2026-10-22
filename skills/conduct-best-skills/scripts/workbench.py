"""User-owned project index, separate from project preferences and history."""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from preferences import atomic_write, require, safe_path


def default_home():
    return Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "conduct-workbench"


def registry_path(home):
    home = Path(home).absolute()
    require(home.resolve() == home, "Workbench home must not redirect through a link")
    path = home / "projects.json"
    require(path.resolve() == path, "Workbench registry must not be redirected")
    return path


def load(home):
    path = registry_path(home)
    if not path.exists():
        return {"schema_version": 1, "projects": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(data, dict) and data.get("schema_version") == 1 and isinstance(data.get("projects"), list), "Invalid workspace registry")
    ids = set()
    for project in data["projects"]:
        require(isinstance(project, dict) and all(isinstance(project.get(k), str) and project[k] for k in ("id", "name", "root")), "Invalid registered project")
        require(project["id"] not in ids, "Duplicate registered project ID")
        require(Path(project["root"]).is_absolute(), "Registered roots must be absolute")
        ids.add(project["id"])
    return data


def change(home, update):
    path = registry_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.parent / "registry.lock"
    require(lock.resolve() == lock, "Workbench lock must not redirect")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError("Workbench registry is being updated; retry after the current write") from exc
    try:
        os.close(fd)
        data = load(home)
        result = update(data)
        atomic_write(path, data)
        return result
    finally:
        lock.unlink()


def register(home, root, name=None):
    root = Path(root).absolute()
    require(root.is_dir() and root.resolve() == root, "Register an existing workspace root without redirection")
    identity = hashlib.sha256(os.path.normcase(str(root)).encode("utf-8")).hexdigest()[:16]
    require(name is None or isinstance(name, str) and name.strip(), "Project name must not be empty")
    def update(data):
        existing = next((p for p in data["projects"] if p["id"] == identity), None)
        project = {"id": identity, "name": name or (existing["name"] if existing else root.name), "root": str(root)}
        if existing:
            existing.update(project)
        else:
            data["projects"].append(project)
        return project
    return change(home, update)


def unregister(home, identity):
    def update(data):
        require(any(p["id"] == identity for p in data["projects"]), "Unknown project ID")
        data["projects"] = [p for p in data["projects"] if p["id"] != identity]
        return {"removed_from_index": identity, "project_files_unchanged": True}
    return change(home, update)


def sync_codex(home, snapshot):
    """Import a minimal local-host snapshot supplied by Codex's documented tools.

    Never initialize imported roots or infer capability usage from chat metadata.
    Missing projects remain indexed, labelled absent from the latest snapshot.
    """
    require(isinstance(snapshot, dict) and snapshot.get("schema_version") == 1,
            "Invalid Codex snapshot version")
    projects, threads = snapshot.get("projects"), snapshot.get("threads", [])
    require(isinstance(projects, list) and isinstance(threads, list), "Invalid Codex snapshot lists")
    seen_ids, seen_roots = set(), set()
    normalized = []
    for project in projects:
        require(isinstance(project, dict) and all(isinstance(project.get(k), str) and project[k].strip()
                for k in ("projectId", "label", "path")), "Invalid Codex project")
        root = Path(project["path"])
        require(root.is_absolute(), "Codex project path must be absolute on this host")
        root_key = os.path.normcase(str(root))
        require(project["projectId"] not in seen_ids and root_key not in seen_roots, "Duplicate Codex project")
        seen_ids.add(project["projectId"])
        seen_roots.add(root_key)
        normalized.append({"id": hashlib.sha256(root_key.encode("utf-8")).hexdigest()[:16],
                           "name": project["label"], "root": str(root), "codex_project_id": project["projectId"]})
    clean_threads, seen_threads = [], set()
    for thread in threads:
        require(isinstance(thread, dict) and all(isinstance(thread.get(k), str) for k in ("id", "title", "status")), "Invalid Codex chat")
        require(thread["id"] and thread["id"] not in seen_threads, "Duplicate or empty Codex chat ID")
        require(thread.get("cwd") is None or isinstance(thread["cwd"], str), "Invalid chat workspace")
        require(thread.get("projectId") is None or isinstance(thread["projectId"], str), "Invalid chat project")
        seen_threads.add(thread["id"])
        matched = next((p for p in normalized if p["codex_project_id"] == thread.get("projectId")), None)
        if matched is None and not thread.get("projectId") and thread.get("cwd"):
            matched = next((p for p in normalized if os.path.normcase(p["root"]) == os.path.normcase(str(Path(thread["cwd"])))), None)
        if matched:
            clean_threads.append({"id": thread["id"], "title": thread["title"], "status": thread["status"], "project_id": matched["id"]})
    now = datetime.now(timezone.utc).isoformat()
    def update(data):
        for project in data["projects"]:
            if project.get("source") == "codex":
                project["in_latest_snapshot"] = False
        for project in normalized:
            existing = next((p for p in data["projects"] if p["id"] == project["id"]), None)
            project.update({"source": "codex", "synced_at": now, "in_latest_snapshot": True})
            if existing:
                existing.update(project)
            else:
                data["projects"].append(project)
        data["codex_sync"] = {"synced_at": now, "project_count": len(normalized),
                              "chat_count": len(clean_threads), "coverage": "recent-chats-snapshot", "host": "local"}
        data["codex_chats"] = clean_threads
        return data["codex_sync"]
    return change(home, update)


def project_root(home, identity):
    project = next((p for p in load(home)["projects"] if p["id"] == identity), None)
    require(project is not None, "Project is not registered in this workbench")
    root = Path(project["root"])
    require(root.is_dir() and root.resolve() == root.absolute(), "Registered workspace is missing or redirected")
    return root


def overview(home):
    from activity import report
    projects = []
    for project in load(home)["projects"]:
        item = dict(project)
        try:
            stats = report(project_root(home, project["id"]))
            calls = [c for c in stats["calls"] if c["invoked"]]
            item.update({"tasks": len({c["task"] for c in calls}), "works": len({c["work"] for c in calls}),
                         "invocations": len(calls), "enabled": stats["enabled"], "status": "available"})
        except (OSError, ValueError, TypeError, KeyError) as exc:
            item.update({"status": "unavailable", "error": str(exc)})
        projects.append(item)
    return projects


def onboard(home, root, name=None):
    from preferences import initialize
    from activity import set_enabled
    root = Path(root).resolve()
    initialize(root)
    target = safe_path(root, "AGENTS.md")
    original = target.read_bytes() if target.exists() else b""
    content = original.decode("utf-8-sig")
    template = (Path(__file__).resolve().parent.parent / "templates/workspace-agents.md").read_text(encoding="utf-8").strip()
    start, end = '<!-- conduct-workbench:start -->', '<!-- conduct-workbench:end -->'
    require(content.count(start) == content.count(end) and content.count(start) <= 1, "Existing Conduct guidance markers are ambiguous; review AGENTS.md")
    if start in content:
        begin, finish = content.index(start), content.index(end) + len(end)
        require(finish > begin, "Invalid Conduct guidance marker order")
        updated = content[:begin] + template + content[finish:]
    else:
        updated = content.rstrip() + ("\n\n" if content.strip() else "") + template + "\n"
    backup = safe_path(root, ".conduct/agents-before-onboarding.md")
    if original and not backup.exists():
        with backup.open('xb') as stream:
            stream.write(original)
    require((target.read_bytes() if target.exists() else b"") == original, "AGENTS.md changed; rerun onboarding after reviewing it")
    target.write_bytes(updated.encode('utf-8'))
    project = register(home, root, name)
    set_enabled(root, True)
    return {"project": project, "guidance": "AGENTS.md", "preferences": ".conduct/preferences.json",
            "activity": ".conduct/activity.json", "coverage": "host-recorded-partial"}


def add_arguments(parser):
    parser.add_argument("action", choices=["onboard", "sync", "register", "unregister", "list", "serve"])
    parser.add_argument("--snapshot", help="Minimal snapshot from Codex list_projects/list_threads")
    parser.add_argument("--home", default=str(default_home()))
    parser.add_argument("--name")
    parser.add_argument("--project-id")
    parser.add_argument("--port", type=int, default=0)


def execute(args):
    if args.action == "sync":
        require(args.snapshot, "Provide --snapshot from Codex's local project tools")
        return sync_codex(args.home, json.loads(Path(args.snapshot).read_text(encoding="utf-8-sig")))
    if args.action == "onboard":
        return onboard(args.home, args.workspace, args.name)
    if args.action == "register":
        return register(args.home, args.workspace, args.name)
    if args.action == "unregister":
        return unregister(args.home, args.project_id)
    if args.action == "list":
        return {"projects": overview(args.home), "home": str(Path(args.home).absolute())}
    from preferences import make_server
    register(args.home, args.workspace, args.name)
    with make_server(args.workspace, args.port, args.home) as server:
        print(json.dumps({"url": server.preference_url, "home": str(Path(args.home).absolute()),
                          "message": "Persistent workspace index; live while this process runs"}), flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    return {"status": "stopped"}
