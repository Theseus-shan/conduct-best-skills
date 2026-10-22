"""Editable task intent and evidence-aware orientation for the local harness."""
import json
import os
from pathlib import Path

from preferences import atomic_write, require, revision, safe_path, task_id

FIELDS = ('objective', 'context', 'constraints', 'approach', 'acceptance', 'baseline', 'next_step', 'delivery')
STAGES = ('context', 'goals', 'planning', 'execution', 'verification', 'refinement', 'delivery')


def empty():
    return {'schema_version': 1, 'stage': 'context', **{field: '' for field in FIELDS}}


def validate(data):
    require(isinstance(data, dict) and data.get('schema_version') == 1, 'Invalid task brief version')
    require(set(data) <= {'schema_version', 'stage', *FIELDS}, 'Unknown task brief fields')
    require(data.get('stage') in STAGES, 'Unknown workflow stage')
    require(all(isinstance(data.get(k, ''), str) and len(data.get(k, '')) <= 8000 for k in FIELDS),
            '请使用简短的任务说明，每项不超过 8000 字。')
    return {**empty(), **data}


def read(root, task):
    path = safe_path(root, f'.conduct/tasks/{task_id(task)}/brief.json')
    if not path.exists():
        return {'task': task, 'revision': 'missing', 'data': empty()}
    raw = path.read_bytes()
    require(len(raw) <= 256_000, 'Task brief exceeds 256 KB')
    return {'task': task, 'revision': revision(raw), 'data': validate(json.loads(raw.decode('utf-8-sig')))}


def contract_revision(data):
    """Operational notes and focus stage do not change the agreed acceptance contract."""
    contract = {k: data[k] for k in FIELDS if k != 'next_step'}
    return revision(json.dumps(contract, sort_keys=True, ensure_ascii=False).encode('utf-8'))


def binding(root, task):
    current = read(root, task)
    return contract_revision(current['data']) if current['revision'] != 'missing' else 'missing'


def save(root, task, data, expected):
    data = validate(data)
    path = safe_path(root, f'.conduct/tasks/{task_id(task)}/brief.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = safe_path(root, f'.conduct/tasks/{task}/brief.lock')
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError('任务说明正在被修改，请稍后重试。') from exc
    try:
        os.close(fd)
        require(expected is not None and read(root, task)['revision'] == expected, '任务说明已变化，请重新载入后再保存。')
        atomic_write(path, data)
    finally:
        lock.unlink()
    return read(root, task)


def tasks(root):
    parent = safe_path(root, '.conduct/tasks')
    if not parent.exists():
        return []
    result = []
    for folder in parent.iterdir():
        if folder.is_dir() and safe_path(root, f'.conduct/tasks/{task_id(folder.name)}/brief.json').is_file():
            result.append(folder.name)
    return sorted(result)


def execution(root):
    """Read the optional workspace execution contract; never execute its checks."""
    try:
        if not safe_path(root, '.conduct/contract.json').exists():
            return {'status': 'unconfigured'}
        from conduct import Workspace
        workspace = Workspace(root)
        report = workspace.status()
        contract, _ = workspace.load()
        dependencies = {t['id']: t.get('depends_on', []) for t in contract['tasks']}
        for task in report['tasks']:
            task['depends_on'] = dependencies[task['id']]
        return {'status': 'available', 'report': report}
    except (ValueError, OSError, KeyError, TypeError):
        return {'status': 'unavailable', 'message': '执行状态暂不可核验；请检查本项目的契约、状态和文件。'}


def dashboard(root, task, calls):
    if not task:
        return {'brief': None, 'checks': [], 'observations': [], 'current_calls': 0, 'previous_calls': 0}
    current = read(root, task)
    data = current['data']
    bound = binding(root, task)
    selected = [call for call in calls if call['task'] == task and call['invoked']]
    matched = [call for call in selected if bound != 'missing' and call.get('brief_revision') == bound]
    checks = [{'label': label, 'supplied': bool(data[field].strip())} for field, label in [
        ('objective', '目标已说明'), ('approach', '方案与选择理由已说明'),
        ('acceptance', '验收标准已说明'), ('constraints', '范围与资源限制已说明'), ('delivery', '交付要求已说明')]]
    observations = []
    if not data['objective'].strip(): observations.append('先明确需要交付的结果，再决定调用哪些能力。')
    if not data['approach'].strip(): observations.append('补充实施路径和能力选择理由，必要时比较不用额外 Skill 的方案。')
    if not data['acceptance'].strip(): observations.append('补充可检查的完成标准；调用成功不能代替任务验收。')
    if len(selected) > len(matched): observations.append('部分调用来自旧版或未绑定的任务说明，需要按当前目标重新核对。')
    if any(c['outcome'] == 'failed' for c in matched): observations.append('有失败记录，检查失败原因及后续重试，避免原样重复。')
    if matched and any(c['outcome'] != 'verified' for c in matched): observations.append('部分当前调用没有验证记录，先补证据或说明验证边界。')
    if not selected: observations.append('尚无明确记录的实际调用；这里不能推断任务进展。')
    if not data['baseline'].strip(): observations.append('需要优化时先写出现状和对比依据，再评估改动是否更好。')
    if not observations: observations.append('已有说明与调用证据仍需逐项对照验收标准；不能据此自动判定最优或完成。')
    return {'brief': current, 'checks': checks, 'observations': observations,
            'current_calls': len(matched), 'previous_calls': len(selected) - len(matched)}


def add_arguments(parser):
    parser.add_argument('action', choices=['show', 'set'])
    parser.add_argument('--task', required=True)
    parser.add_argument('--expected', help='Revision from show; required when saving')
    parser.add_argument('--stage', choices=STAGES)
    for field in FIELDS:
        parser.add_argument('--' + field.replace('_', '-'), dest=field)


def execute(args):
    if args.action == 'show':
        from activity import report
        return dashboard(args.workspace, args.task, report(args.workspace)['calls'])
    current = read(args.workspace, args.task)['data']
    for field in (*FIELDS, 'stage'):
        value = getattr(args, field)
        if value is not None:
            current[field] = value
    return save(args.workspace, args.task, current, args.expected)
