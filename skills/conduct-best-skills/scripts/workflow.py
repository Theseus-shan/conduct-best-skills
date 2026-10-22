"""Project work graph, evidence views and an explicit Agent change inbox.

No browser action executes commands or sends prompts to a host conversation.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import uuid

from preferences import atomic_write, require, revision, safe_path, task_id

TEXT = ('title', 'objective', 'approach', 'acceptance', 'next_step', 'blocker')
LISTS = ('depends_on', 'inputs', 'outputs', 'capabilities', 'evidence')
STATES = ('planned', 'active', 'blocked', 'done', 'skipped')


def now():
    return datetime.now(timezone.utc).isoformat()


def new_node(identity, title, task=None, **values):
    return {'id': identity, 'task': task or identity, 'title': title,
            **{k: '' for k in TEXT if k != 'title'}, **{k: [] for k in LISTS},
            'state': 'planned', 'execution_task': '', **values}


def validate_node(node, root):
    require(isinstance(node, dict) and set(node) <= {'id', 'task', 'state', 'execution_task', *TEXT, *LISTS}, '未知工作节点字段')
    task_id(node.get('id'))
    task_id(node.get('task'))
    require(node.get('state') in STATES, '未知工作状态')
    require(all(isinstance(node.get(k), str) and len(node[k]) <= 8000 for k in TEXT), '请用简短自然语言描述工作，每项不超过 8000 字')
    require(bool(node['title'].strip()), '请填写工作名称')
    require(isinstance(node.get('execution_task'), str), 'Invalid execution task')
    for key in LISTS:
        values = node.get(key)
        require(isinstance(values, list) and len(values) <= 500 and all(isinstance(v, str) and v.strip() and len(v) <= 1000 for v in values), 'Invalid node references')
        require(len(set(values)) == len(values), '请勿重复填写同一引用')
    for path in node['inputs'] + node['outputs']:
        from conduct import local_path
        local_path(Path(root).resolve(), path)
    return node


def validate_graph(nodes, root):
    require(isinstance(nodes, list) and len(nodes) <= 150, '工作图最多保存 150 个节点')
    for node in nodes:
        validate_node(node, root)
    identities = {n['id'] for n in nodes}
    require(len(identities) == len(nodes), '重复的节点标识')
    require(len({n['task'] for n in nodes}) == len(nodes), '每项工作需要独立的关联任务名称，避免调用记录重复归属')
    pending = {n['id']: set(n['depends_on']) for n in nodes}
    require(all(deps <= identities for deps in pending.values()), '前置工作不存在')
    visited = set()
    while pending:
        ready = [key for key, deps in pending.items() if deps <= visited]
        require(bool(ready), '工作依赖形成了循环，请调整前置工作')
        for key in ready:
            visited.add(key)
            del pending[key]


def derived(root, calls, execution):
    """Use only explicitly recorded tasks/dependencies. Never invent a paper pipeline."""
    from harness import read as brief, tasks
    nodes = []
    if execution.get('status') == 'available':
        from conduct import Workspace
        contract, _ = Workspace(root).load()
        criteria = {c['id']: c for c in contract['criteria']}
        for task in contract['tasks']:
            checks = [criteria[c] for c in task['criteria']]
            nodes.append(new_node('check-' + task['id'], task['objective'], task['id'],
                objective=task['objective'], execution_task=task['id'],
                depends_on=['check-' + d for d in task.get('depends_on', [])],
                acceptance='\n'.join(c['requirement'] for c in checks),
                inputs=list(dict.fromkeys(p for c in checks for p in c['inputs'])),
                outputs=list(dict.fromkeys(p for c in checks for p in c['artifacts']))))
    known = {n['task'] for n in nodes}
    for task in sorted(set(tasks(root)) | {c['task'] for c in calls}):
        if task in known:
            continue
        data = brief(root, task)['data']
        key = 'work-' + hashlib.sha256(task.encode()).hexdigest()[:12]
        nodes.append(new_node(key, task, task, **{k: data[k] for k in ('objective', 'approach', 'acceptance', 'next_step')}))
    return {'schema_version': 1, 'nodes': nodes, 'requests': [], 'history': []}


def read(root, calls=None, execution=None):
    if calls is None:
        from activity import report
        calls = report(root)['calls']
    if execution is None:
        from harness import execution as status
        execution = status(root)
    path = safe_path(root, '.conduct/workflow.json')
    if path.exists():
        raw = path.read_bytes()
        require(len(raw) <= 2_000_000, '工作图记录超过 2 MB，请归档后再编辑')
        data = json.loads(raw.decode('utf-8-sig'))
        require(data.get('schema_version') == 1 and isinstance(data.get('requests'), list) and isinstance(data.get('history'), list), 'Invalid workflow record')
        validate_graph(data['nodes'], root)
        observed = derived(root, calls, execution)['nodes']
        task_map = {n['task']: n['id'] for n in data['nodes']}
        additions = [n for n in observed if n['task'] not in task_map]
        # Existing edits win; newly observed tasks join without inventing links.
        key_map = {n['id']: task_map.get(n['task'], n['id']) for n in observed}
        for node in additions:
            node['depends_on'] = [key_map[d] for d in node['depends_on']]
        data['nodes'].extend(additions)
        validate_graph(data['nodes'], root)
        effective = raw + (json.dumps(additions, ensure_ascii=False, sort_keys=True).encode() if additions else b'')
        return {'revision': revision(effective), 'data': data, 'derived': False}
    data = derived(root, calls, execution)
    return {'revision': 'derived-' + revision(json.dumps(data, ensure_ascii=False, sort_keys=True).encode()), 'data': data, 'derived': True}


def node_revision(node):
    return revision(json.dumps({k: v for k, v in node.items() if k not in {'state', 'next_step', 'blocker'}}, sort_keys=True, ensure_ascii=False).encode())


def binding(root, task):
    node = next((n for n in read(root)['data']['nodes'] if n['task'] == task), None)
    return node_revision(node) if node else 'missing'


def mutate(root, expected, operation):
    path = safe_path(root, '.conduct/workflow.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = safe_path(root, '.conduct/workflow.lock')
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError('工作图正在修改，请稍后重试') from exc
    try:
        os.close(fd)
        current = read(root)
        require(expected is not None and current['revision'] == expected, '工作图已变化，请重新载入后再保存')
        result = operation(current['data'])
        validate_graph(current['data']['nodes'], root)
        require(len(json.dumps(current['data'], ensure_ascii=False).encode()) <= 1_900_000, '工作图记录过多，请归档后再保存')
        atomic_write(path, current['data'])
        return {'revision': read(root)['revision'], **result}
    finally:
        lock.unlink()


def save_node(root, node, expected):
    validate_node(node, root)
    def apply(data):
        previous = next((n for n in data['nodes'] if n['id'] == node['id']), None)
        if previous:
            data['nodes'][data['nodes'].index(previous)] = node
        else:
            data['nodes'].append(node)
        changed = [k for k in (*TEXT, *LISTS, 'state') if not previous or previous[k] != node[k]]
        data['history'].append({'id': str(uuid.uuid4()), 'node': node['id'], 'at': now(),
                                'kind': 'edited' if previous else 'created',
                                'text': '更新工作计划' if previous else '创建工作节点',
                                'changes': {k: {'before': previous[k] if previous else None, 'after': node[k]} for k in changed}})
        return {'node': node['id']}
    return mutate(root, expected, apply)


def request_change(root, node_id, text, expected, request_id):
    require(isinstance(text, str) and 0 < len(text.strip()) <= 4000, '请用一句话说明需要的调整（最多 4000 字）')
    task_id(request_id)
    def apply(data):
        require(any(n['id'] == node_id for n in data['nodes']), '工作节点不存在')
        existing = next((r for r in data['requests'] if r['id'] == request_id), None)
        if existing:
            require(existing['node'] == node_id and existing['text'] == text.strip(), '请求标识已用于另一项调整')
            return {'request': existing}
        request = {'id': request_id, 'node': node_id, 'text': text.strip(), 'status': 'pending', 'at': now(), 'resolution': '', 'evidence': []}
        data['requests'].append(request)
        data['history'].append({'id': str(uuid.uuid4()), 'node': node_id, 'at': request['at'], 'kind': 'requested', 'text': text.strip()})
        return {'request': request}
    # A network retry can safely recover the same request after revision changes.
    previous = next((r for r in read(root)['data']['requests'] if r['id'] == request_id), None)
    if previous:
        require(previous['node'] == node_id and previous['text'] == text.strip(), '请求标识已用于另一项调整')
        return {'request': previous, 'revision': read(root)['revision']}
    return mutate(root, expected, apply)


def resolve_request(root, identity, status, note, evidence, expected):
    require(status in ('applied', 'declined'), 'Invalid request outcome')
    require(isinstance(note, str) and 0 < len(note.strip()) <= 4000, '处理结果需要说明')
    require(isinstance(evidence, list) and all(isinstance(x, str) and x.strip() for x in evidence), 'Invalid evidence references')
    require(status != 'applied' or evidence, '落实调整需要可核查的证据引用')
    def apply(data):
        request = next((r for r in data['requests'] if r['id'] == identity), None)
        require(request is not None and request['status'] == 'pending', '请求不存在或已处理')
        request.update(status=status, resolution=note, evidence=evidence, resolved_at=now())
        data['history'].append({'id': str(uuid.uuid4()), 'node': request['node'], 'at': request['resolved_at'], 'kind': status, 'text': note})
        return {'request': request}
    return mutate(root, expected, apply)


def inspect_file(root, relative, expected=None):
    from conduct import local_path
    try:
        path = local_path(Path(root).resolve(), relative)
        if not path.is_file():
            return {'path': relative, 'status': 'missing'}
        size = path.stat().st_size
        status = 'present'
        if expected:
            # Bounded hashes avoid repeatedly loading large simulation outputs.
            status = ('unchanged' if hashlib.sha256(path.read_bytes()).hexdigest() == expected else 'changed') if size <= 8_000_000 else 'not_checked'
        return {'path': relative, 'status': status, 'bytes': size}
    except (OSError, ValueError):
        return {'path': relative, 'status': 'unavailable'}


def artifact(root, node_id, relative):
    current = read(root)
    node = next((n for n in current['data']['nodes'] if n['id'] == node_id), None)
    require(node is not None and relative in node['inputs'] + node['outputs'], '仅能打开本节点明确关联的文件')
    from conduct import local_path
    path = local_path(Path(root).resolve(), relative)
    require(path.is_file() and path.stat().st_size <= 256_000, '此文件不存在或超过文本预览上限，请在项目中打开')
    require(path.suffix.lower() in {'.md', '.txt', '.csv', '.json', '.py', '.tex', '.typ', '.yaml', '.yml', '.log'}, '此格式请在项目中打开；工作台只预览文本')
    return {'path': relative, 'content': path.read_text(encoding='utf-8-sig')}


def view(root, calls, execution):
    from preferences import resolve
    from harness import dashboard
    current = read(root, calls, execution)
    report = execution.get('report', {})
    runtime_tasks = {t['id']: t for t in report.get('tasks', [])}
    runtime_checks = {}
    if execution.get('status') == 'available':
        from conduct import Workspace
        contract, _ = Workspace(root).load()
        checks = {c['id']: c for c in report['criteria']}
        runtime_checks = {t['id']: [checks[c] for c in t['criteria']] for t in contract['tasks']}
    nodes, decisions = [], []
    for node in current['data']['nodes']:
        checks = runtime_checks.get(node['execution_task'], [])
        task_calls = [c for c in calls if c['task'] == node['task']]
        runtime = runtime_tasks.get(node['execution_task'])
        # Evidence status comes from the executable contract, never a manual "done" marker.
        status = runtime['status'] if runtime else 'blocked' if node['blocker'] else node['state']
        inputs = [inspect_file(root, p) for p in node['inputs']]
        outputs = [inspect_file(root, p) for p in node['outputs']]
        pending = [r for r in current['data']['requests'] if r['node'] == node['id'] and r['status'] == 'pending']
        notices = []
        if pending:
            notices.append({'priority': 0, 'text': f"{len(pending)} 项调整待 Agent 处理", 'basis': '已保存的用户请求'})
        if node['blocker']:
            notices.append({'priority': 1, 'text': node['blocker'], 'basis': '节点记录的阻碍'})
        missing = [f['path'] for f in inputs if f['status'] == 'missing']
        if missing:
            notices.append({'priority': 1, 'text': '补充输入：' + '、'.join(missing[:3]), 'basis': '关联文件当前不存在'})
        for check in checks:
            if check['status'] != 'PASS':
                notices.append({'priority': 1 if check['status'] in ('FAIL', 'STALE') else 2,
                                'text': check['requirement'], 'basis': check['status'] + ' · ' + check['reason']})
        for call in task_calls:
            if call['outcome'] == 'failed':
                notices.append({'priority': 2, 'text': '复核失败调用：' + call['name'], 'basis': '调用 ' + call['call_id'] + '（历史失败不等于当前仍阻塞）'})
        brief = dashboard(root, node['task'], calls)
        if brief['previous_calls']:
            notices.append({'priority': 2, 'text': f"核对 {brief['previous_calls']} 次旧版或未绑定调用", 'basis': '调用记录与当前任务说明版本不匹配'})
        changed_calls = [c for c in task_calls if c['invoked'] and c.get('workflow_revision', 'missing') not in ('missing', node_revision(node))]
        if changed_calls:
            notices.append({'priority': 1, 'text': f"工作计划已改变，复核 {len(changed_calls)} 次历史调用", 'basis': '调用绑定的方案、依赖或文件引用与当前工作节点不同'})
        for notice in notices:
            decisions.append({**notice, 'node': node['id'], 'title': node['title']})
        nodes.append({**node, 'display_status': status, 'runtime': runtime, 'checks': checks,
                      'calls': task_calls, 'files': {'inputs': inputs, 'outputs': outputs},
                      'preferences': resolve(root, node['task'])['rules'], 'notices': notices,
                      'requests': [r for r in current['data']['requests'] if r['node'] == node['id']]})
    timeline = list(current['data']['history'])
    from activity import read as activity_read
    mapping = {n['task']: n['id'] for n in nodes}
    for event in activity_read(root)['events']:
        if event['task'] in mapping:
            timeline.append({'id': event['id'], 'node': mapping[event['task']], 'at': event['at'],
                             'kind': event['event'], 'text': event['name'] + (' · ' + event['note'] if event.get('note') else '')})
    return {'revision': current['revision'], 'derived': current['derived'], 'nodes': nodes,
            'decisions': sorted(decisions, key=lambda n: n['priority']),
            'timeline': sorted(timeline, key=lambda e: e['at'], reverse=True)[:60],
            'pending': sum(r['status'] == 'pending' for r in current['data']['requests'])}


def add_arguments(parser):
    parser.add_argument('action', choices=['show', 'node', 'inbox', 'resolve'])
    parser.add_argument('--id')
    parser.add_argument('--task')
    parser.add_argument('--expected')
    parser.add_argument('--state', choices=STATES)
    parser.add_argument('--execution-task')
    for key in TEXT:
        parser.add_argument('--' + key.replace('_', '-'))
    for key in LISTS:
        parser.add_argument('--' + key.replace('_', '-'), action='append')
    parser.add_argument('--clear', action='append', choices=LISTS, default=[])
    parser.add_argument('--outcome', choices=['applied', 'declined'])
    parser.add_argument('--note')


def execute(args):
    current = read(args.workspace)
    if args.action == 'show':
        from activity import report
        from harness import execution
        return view(args.workspace, report(args.workspace)['calls'], execution(args.workspace))
    if args.action == 'inbox':
        return {'revision': current['revision'], 'requests': [r for r in current['data']['requests'] if r['status'] == 'pending']}
    if args.action == 'resolve':
        return resolve_request(args.workspace, args.id, args.outcome, args.note, args.evidence or [], args.expected)
    node = next((dict(n) for n in current['data']['nodes'] if n['id'] == args.id), new_node(args.id, args.title or '', args.task))
    for key in args.clear:
        node[key] = []
    for key in (*TEXT, *LISTS, 'state', 'task', 'execution_task'):
        value = getattr(args, key)
        if value is not None:
            node[key] = value
    return save_node(args.workspace, node, args.expected)
