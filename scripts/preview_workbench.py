"""Render the real workbench with synthetic, read-only documentation fixtures.

Never imports Codex's project index, user preferences, chat history or credentials.
The temporary fixture roots are replaced before responding to the browser.
"""
import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import sys
import tempfile
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / 'skills/conduct-best-skills'
sys.path.insert(0, str(CORE / 'scripts'))
import activity
import harness
import workflow
import preferences


def seed(parent):
    projects = []
    for key, name in [('paper', '论文写作 · 演示'), ('simulation', '仿真实验 · 演示'), ('review', '文献综述 · 演示')]:
        folder = parent / key
        folder.mkdir()
        preferences.initialize(folder)
        projects.append({'id': key, 'name': name, 'root': '演示空间 / ' + key,
                         'source': 'codex', 'in_latest_snapshot': True, 'status': 'available', 'invocations': 0})
    paper = parent / 'paper'
    rules = [preferences.parse_sentence(sentence, key) for key, sentence in [
        ('writing', '写论文时，默认使用 Anti-Defensive Writing 和 nature-writing，并保留事实、引用和必要局限。'),
        ('simulation', '跑仿真时，默认使用 simulation-runner，并先完成小规模验证。')]]
    preferences.save(paper, {'schema_version': 1, 'workflow': {'language': '简体中文'}, 'rules': rules},
                     expected=preferences.read(paper)['revision'])
    preferences.context(paper, '引言初稿', ['paper-writing'], [])
    harness.save(paper, '引言初稿', {**harness.empty(), 'stage': 'planning',
        'objective': '形成一份论证清晰、可核查的论文引言初稿。',
        'context': '依据作者提供的研究问题、结果摘要与已核验文献；材料不足处先保留待核对项。',
        'constraints': '保留事实、引用和必要局限；不补造结果，不扩大结论。',
        'approach': '先梳理论证结构，再由 nature-writing 起草，结合 Anti-Defensive Writing 检查防御性表达；最后逐项核对引用。',
        'acceptance': '研究缺口清楚；每项关键主张有依据；引用与原文匹配；未决问题单列。',
        'baseline': '对照初稿检查重复铺垫和无依据的强调。必要标准通过后交付，不以自评分代替改善证据。',
        'next_step': '确认研究缺口与现有文献的对应关系，再进入起草。',
        'delivery': '可编辑引言、引用核对清单及待解决问题。以上均为合成展示。'}, 'missing')
    activity.set_enabled(paper, True)
    for number, (task, kind, name, outcome, rating) in enumerate([
        ('引言初稿', 'skill', 'nature-writing', 'succeeded', 'helpful'),
        ('引言初稿', 'skill', 'Anti-Defensive Writing', 'succeeded', 'helpful'),
        ('文献核对', 'mcp', 'literature-search', 'failed', 'mixed'),
        ('统计复核', 'tool', 'python', 'succeeded', 'unknown'),
    ]):
        call = f'demo-{number}'
        common = dict(root=paper, task=task, kind=kind, name=name, call_id=call, work='论文准备')
        activity.record(**common, event='invoked', note='合成展示记录，不代表真实科研调用。')
        activity.record(**common, event=outcome, evidence=['demo:synthetic-evidence'])
        if rating != 'unknown':
            activity.feedback(paper, call, rating, '合成示例反馈，不代表真实用户评价。')
    (paper / 'draft.md').write_text('# 合成引言示例\n\n这里是用于界面验收的虚构内容，不代表科研结论。\n', encoding='utf-8')
    (paper / 'results.csv').write_text('case,value\nsynthetic-a,1\nsynthetic-b,2\n', encoding='utf-8')
    nodes = [
        workflow.new_node('sources', '核对关键文献', '文献核对', objective='为关键主张建立可核查的来源。', approach='优先核对已有文献；检索失败时保留待核对项，不猜测引用。', acceptance='逐条确认原文是否支持相应主张。', next_step='补充两条关键主张的来源。', blocker='合成示例：文献服务调用失败，仍需补充来源。', capabilities=['literature-search'], state='blocked'),
        workflow.new_node('gap', '明确研究缺口', '研究缺口', objective='把研究问题与现有工作的区别说清楚。', approach='依据已核实材料梳理论证，再与作者确认。', depends_on=['sources'], outputs=['research-gap.md']),
        workflow.new_node('analysis', '仿真与统计复核', '统计复核', objective='核对合成结果并准备可复现的分析依据。', approach='先检查输入，再复核统计口径。', acceptance='数据、单位与报告一致。', outputs=['results.csv'], capabilities=['python'], state='active'),
        workflow.new_node('figures', '制作结果图表', '图表制作', objective='将已核对的结果转为可读图表。', inputs=['results.csv'], outputs=['figure.svg'], depends_on=['analysis'], capabilities=['nature-figure']),
        workflow.new_node('intro', '撰写引言初稿', '引言初稿', objective='交付论证清晰、引用可核查的引言。', approach='nature-writing 起草结构，Anti-Defensive Writing 检查防御性表达，保留事实和必要局限。', acceptance='每条关键主张有来源，研究缺口清楚。', next_step='先核实研究缺口，再调整初稿。', depends_on=['gap', 'figures'], outputs=['draft.md'], capabilities=['nature-writing', 'Anti-Defensive Writing'])]
    preferences.atomic_write(paper / '.conduct/workflow.json', {'schema_version': 1, 'nodes': nodes, 'requests': [], 'history': []})
    workflow.request_change(paper, 'intro', '合成演示：先核对研究缺口，暂时不要润色。', workflow.read(paper)['revision'], 'demo-request')
    projects[0]['invocations'] = 4
    return projects


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=0)
    args = parser.parse_args()
    token = secrets.token_urlsafe(24)
    with tempfile.TemporaryDirectory(prefix='conduct-docs-demo-') as scratch:
        parent = Path(scratch).resolve()
        projects = seed(parent)
        stamp = datetime.now(timezone.utc).isoformat()

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def reply(self, status, value, mime='application/json; charset=utf-8'):
                raw = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False).encode('utf-8')
                self.send_response(status)
                self.send_header('Content-Type', mime)
                self.send_header('Content-Length', str(len(raw)))
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Referrer-Policy', 'no-referrer')
                self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'")
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):
                parts = urlsplit(self.path)
                if self.headers.get('Host') != f'127.0.0.1:{self.server.server_port}' or not parts.path.startswith(f'/{token}/'):
                    return self.reply(403, {'error': 'Local demo URL required'})
                if parts.path == f'/{token}/':
                    return self.reply(200, (CORE / 'assets/preferences.html').read_bytes(), 'text/html; charset=utf-8')
                query = parse_qs(parts.query, keep_blank_values=True)
                key = query.get('project', ['paper'])[0]
                if key not in {p['id'] for p in projects}:
                    return self.reply(404, {'error': 'Unknown demo project'})
                folder = parent / key
                if parts.path == f'/{token}/api/artifact':
                    try:
                        return self.reply(200, workflow.artifact(folder, query.get('node', [''])[0], query.get('path', [''])[0]))
                    except (ValueError, OSError) as error:
                        return self.reply(422, {'error': str(error)})
                if parts.path == f'/{token}/api/reflection':
                    return self.reply(200, activity.markdown(activity.report(folder)).encode('utf-8'), 'text/markdown; charset=utf-8')
                if parts.path != f'/{token}/api/preferences':
                    return self.reply(404, {'error': 'Not found'})
                data = preferences.view(folder, query.get('task', [None])[0], query.get('type'))
                data.update({'workspace': '公开演示 · 项目、聊天、调用及反馈均为合成数据', 'projects': projects,
                             'project_id': key, 'workbench_mode': False,
                             'codex_sync': {'project_count': 3, 'synced_at': stamp},
                             'codex_chats': [{'id': 'demo-chat', 'title': '规划论文与验证步骤（合成演示）', 'status': 'idle'}] if key == 'paper' else []})
                # Source locations returned by preference readers can be absolute.
                raw = json.dumps(data, ensure_ascii=False)
                for project in projects:
                    raw = raw.replace(json.dumps(str(parent / project['id']), ensure_ascii=False)[1:-1], project['root'])
                assert str(parent) not in raw and str(parent).replace('\\', '\\\\') not in raw
                return self.reply(200, raw.encode('utf-8'))

            def do_POST(self):
                self.reply(405, {'error': '这是只读的合成演示；请在自己的工作台保存偏好。'})

        with ThreadingHTTPServer(('127.0.0.1', args.port), Handler) as server:
            print(json.dumps({'url': f'http://127.0.0.1:{server.server_port}/{token}/', 'mode': 'synthetic-read-only'}), flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass


if __name__ == '__main__':
    main()
