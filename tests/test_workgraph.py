"""Real workflow edits, dependency integrity, change inbox and artifact confinement."""
import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request

import test_preferences as fixtures
from test_preferences import prefs, urlopen
from test_runtime import conduct, fixture
import activity
import harness
import workflow
import workbench


class WorkgraphTests(unittest.TestCase):
    setUp = fixtures.PreferenceTests.setUp

    def save(self, node, root=None):
        root = root or self.a
        return workflow.save_node(root, node, workflow.read(root)['revision'])

    def seed(self):
        self.save(workflow.new_node('first', '核对材料'))
        self.save(workflow.new_node('second', '撰写初稿', depends_on=['first']))

    def test_empty_project_has_no_invented_nodes_or_writes(self):
        self.assertEqual(prefs.view(self.a)['workgraph']['nodes'], [])
        self.assertFalse((self.a / '.conduct').exists())

    def test_actual_runtime_tasks_and_dependencies_are_derived(self):
        data = fixture()
        data['tasks'].append({'id': 'delivery', 'objective': 'Deliver', 'criteria': ['delivery'], 'depends_on': ['repair']})
        data['criteria'].append({**data['criteria'][0], 'id': 'delivery'})
        conduct.Workspace(self.a).initialize(data)
        graph = prefs.view(self.a)['workgraph']
        self.assertEqual([n['title'] for n in graph['nodes']], ['Fix total', 'Deliver'])
        self.assertEqual(graph['nodes'][1]['depends_on'], ['check-repair'])
        self.assertEqual(graph['nodes'][1]['display_status'], 'WAITING')
        self.assertFalse((self.a / '.conduct/workflow.json').exists())

    def test_new_observed_tasks_join_without_overwriting_edits(self):
        self.seed()
        old = workflow.read(self.a)['revision']
        harness.save(self.a, 'later', {**harness.empty(), 'objective': 'New observed task'}, 'missing')
        graph = workflow.read(self.a)
        self.assertEqual(len(graph['data']['nodes']), 3)
        self.assertEqual(graph['data']['nodes'][0]['title'], '核对材料')
        self.assertEqual(graph['data']['nodes'][-1]['depends_on'], [])
        with self.assertRaises(ValueError):
            workflow.save_node(self.a, workflow.new_node('first', 'Stale graph'), old)

    def test_node_edits_are_project_local_and_revision_safe(self):
        initial = workflow.read(self.a)['revision']
        self.save(workflow.new_node('first', '核对材料'))
        with self.assertRaises(ValueError):
            workflow.save_node(self.a, workflow.new_node('first', 'Stale edit'), initial)
        self.assertEqual(workflow.read(self.a)['data']['nodes'][0]['title'], '核对材料')
        self.assertEqual(workflow.read(self.b)['data']['nodes'], [])

    def test_cyclic_and_unknown_dependencies_are_rejected_atomically(self):
        self.seed()
        before = workflow.read(self.a)
        for deps in [['second'], ['missing']]:
            with self.assertRaises(ValueError):
                self.save(workflow.new_node('first', 'Bad dependency', depends_on=deps))
            self.assertEqual(workflow.read(self.a), before)

    def test_unsafe_file_paths_are_rejected(self):
        for path in ['../secret.txt', '/secret.txt', 'C:/secret.txt', 'folder/../../secret.txt']:
            with self.assertRaises(ValueError):
                self.save(workflow.new_node('first', 'Bad path', outputs=[path]))

    def test_pending_request_is_not_execution_and_retry_is_idempotent(self):
        self.seed()
        rev = workflow.read(self.a)['revision']
        first = workflow.request_change(self.a, 'first', '先检查来源', rev, 'request-1')
        retry = workflow.request_change(self.a, 'first', '先检查来源', rev, 'request-1')
        self.assertEqual(first['request'], retry['request'])
        self.assertEqual(first['request']['status'], 'pending')
        self.assertEqual(activity.report(self.a)['calls'], [])
        self.assertEqual(workflow.read(self.a)['data']['nodes'][0]['state'], 'planned')
        with self.assertRaises(ValueError):
            workflow.request_change(self.a, 'first', 'Different request', rev, 'request-1')

    def test_agent_resolution_requires_evidence_and_preserves_request(self):
        self.seed()
        workflow.request_change(self.a, 'first', '先检查来源', workflow.read(self.a)['revision'], 'request-1')
        rev = workflow.read(self.a)['revision']
        with self.assertRaises(ValueError):
            workflow.resolve_request(self.a, 'request-1', 'applied', 'Done', [], rev)
        workflow.resolve_request(self.a, 'request-1', 'applied', '已核对并更新计划', ['notes.md'], rev)
        request = workflow.read(self.a)['data']['requests'][0]
        self.assertEqual(request['text'], '先检查来源')
        self.assertEqual(request['status'], 'applied')
        self.assertEqual(prefs.view(self.a)['workgraph']['pending'], 0)

    def test_file_preview_only_reads_explicit_node_references(self):
        (self.a / 'draft.md').write_text('<script>untrusted()</script>', encoding='utf-8')
        (self.a / 'other.txt').write_text('not linked', encoding='utf-8')
        self.save(workflow.new_node('first', 'Draft', outputs=['draft.md']))
        self.assertEqual(workflow.artifact(self.a, 'first', 'draft.md')['content'], '<script>untrusted()</script>')
        for path in ['other.txt', '../draft.md']:
            with self.assertRaises(ValueError):
                workflow.artifact(self.a, 'first', path)

    def test_manual_done_and_file_existence_are_not_verification(self):
        (self.a / 'draft.md').write_text('Draft', encoding='utf-8')
        self.save(workflow.new_node('first', 'Draft', state='done', inputs=['missing.csv'], outputs=['draft.md']))
        graph = prefs.view(self.a)['workgraph']
        self.assertEqual(graph['nodes'][0]['display_status'], 'done')
        self.assertEqual(graph['nodes'][0]['checks'], [])
        self.assertEqual(graph['nodes'][0]['files']['outputs'][0]['status'], 'present')
        self.assertIn('missing.csv', graph['decisions'][0]['text'])

    def test_plan_changes_invalidate_invocation_context_but_progress_notes_do_not(self):
        self.seed()
        activity.set_enabled(self.a, True)
        invocation = activity.record(self.a, 'first', 'tool', 'python', 'invoked', 'call')
        node = workflow.read(self.a)['data']['nodes'][0]
        self.save({**node, 'next_step': 'Check references', 'state': 'active'})
        self.assertEqual(workflow.binding(self.a, 'first'), invocation['workflow_revision'])
        self.save({**node, 'approach': 'Use a different method'})
        outcome = activity.record(self.a, 'first', 'tool', 'python', 'succeeded', 'call')
        self.assertEqual(outcome['workflow_revision'], invocation['workflow_revision'])
        graph = prefs.view(self.a)['workgraph']
        self.assertTrue(any('工作计划已改变' in n['text'] for n in graph['decisions']))

    def test_http_request_isolation_and_no_browser_resolve_endpoint(self):
        self.seed()
        self.save(workflow.new_node('first', 'B work'), self.b)
        home = self.root / 'index'
        workbench.register(home, self.a)
        b = workbench.register(home, self.b)
        server = prefs.make_server(self.a, home=home)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = server.preference_url + 'api/workflow?project=' + b['id']
            body = {'action': 'request', 'node': 'first', 'text': 'B only', 'request_id': 'r-b', 'revision': workflow.read(self.b)['revision']}
            with urlopen(Request(url, data=json.dumps(body).encode(), headers={'X-Conduct-Edit': '1'}), timeout=3) as response:
                self.assertEqual(json.load(response)['request']['status'], 'pending')
            self.assertEqual(workflow.read(self.a)['data']['requests'], [])
            body['action'] = 'resolve'
            with self.assertRaises(HTTPError) as error:
                urlopen(Request(url, data=json.dumps(body).encode(), headers={'X-Conduct-Edit': '1'}), timeout=3)
            self.assertEqual(error.exception.code, 409)
            error.exception.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


if __name__ == '__main__':
    unittest.main()
