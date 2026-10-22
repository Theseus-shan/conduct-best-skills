"""Task intent isolation and invocation evidence validity after contract edits."""
import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request

import test_preferences as fixtures
from test_preferences import prefs, urlopen
import activity
import harness
import workbench


class HarnessTests(unittest.TestCase):
    setUp = fixtures.PreferenceTests.setUp

    def save(self, **fields):
        current = harness.read(self.a, 'intro')
        return harness.save(self.a, 'intro', {**current['data'], **fields}, current['revision'])

    def call(self, event='invoked'):
        activity.set_enabled(self.a, True)
        return activity.record(self.a, 'intro', 'tool', 'python', event, 'call')

    def dashboard(self):
        return harness.dashboard(self.a, 'intro', activity.report(self.a)['calls'])

    def test_read_only_and_isolation(self):
        self.assertEqual(harness.read(self.a, 'intro')['revision'], 'missing')
        self.assertFalse((self.a / '.conduct').exists())
        self.save(objective='Draft an introduction')
        self.assertEqual(harness.read(self.b, 'intro')['revision'], 'missing')
        self.assertEqual(harness.read(self.a, 'other')['revision'], 'missing')
        self.assertIn('intro', prefs.view(self.a)['tasks'])

    def test_invalid_input_and_conflicts_preserve_saved_brief(self):
        saved = self.save(objective='Original')
        for data in [dict(saved['data'], stage='done'), dict(saved['data'], unknown=True),
                     dict(saved['data'], objective=42), dict(saved['data'], context='x'*8001)]:
            with self.assertRaises(ValueError):
                harness.save(self.a, 'intro', data, saved['revision'])
        for task in ['../outside', 'a/b', '..']:
            with self.assertRaises(ValueError):
                harness.save(self.a, task, saved['data'], 'missing')
        with self.assertRaises(ValueError):
            harness.save(self.a, 'intro', saved['data'], 'missing')
        self.assertEqual(harness.read(self.a, 'intro'), saved)

    def test_contract_change_marks_prior_evidence_for_review(self):
        self.save(objective='Original', acceptance='Check the draft')
        invoked = self.call()
        self.assertEqual(self.dashboard()['current_calls'], 1)
        self.save(acceptance='Check draft and references')
        outcome = self.call('succeeded')
        self.assertEqual(outcome['brief_revision'], invoked['brief_revision'])
        self.assertEqual(self.dashboard()['current_calls'], 0)
        self.assertEqual(self.dashboard()['previous_calls'], 1)

    def test_focus_and_next_step_preserve_binding(self):
        self.save(objective='Original')
        self.call()
        self.save(stage='verification', next_step='Check citations')
        self.assertEqual(self.dashboard()['current_calls'], 1)

    def test_invocation_binds_after_selection(self):
        self.save(objective='Original')
        selected = self.call('selected')
        self.save(objective='Changed')
        invoked = self.call()
        self.assertNotEqual(selected['brief_revision'], invoked['brief_revision'])
        self.assertEqual(self.dashboard()['current_calls'], 1)

    def test_legacy_unbound_calls_remain_visible(self):
        self.call()
        data = activity.read(self.a)
        for event in data['events']:
            event.pop('brief_revision')
        prefs.atomic_write(self.a / '.conduct/activity.json', data)
        self.save(objective='New goal')
        self.assertEqual(self.dashboard()['previous_calls'], 1)
        self.assertEqual(activity.report(self.a)['calls'][0]['brief_revision'], 'missing')

    def test_http_save_is_project_local_and_rejects_stale_revision(self):
        home = self.root / 'index'
        workbench.register(home, self.a)
        b = workbench.register(home, self.b)
        server = prefs.make_server(self.a, home=home)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = server.preference_url + 'api/harness?project=' + b['id']
            body = {'task': 'intro', 'revision': 'missing', 'data': dict(harness.empty(), objective='B only')}
            def request():
                return urlopen(Request(url, data=json.dumps(body).encode(), headers={'X-Conduct-Edit': '1'}), timeout=3)
            with request() as response:
                self.assertEqual(json.load(response)['data']['objective'], 'B only')
            with self.assertRaises(HTTPError) as error:
                request()
            self.assertEqual(error.exception.code, 409)
            error.exception.close()
            self.assertEqual(harness.read(self.a, 'intro')['revision'], 'missing')
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_unconfigured_runtime_is_read_only(self):
        self.assertEqual(harness.execution(self.a)['status'], 'unconfigured')
        self.assertFalse((self.a / '.conduct').exists())

    def test_runtime_dependency_and_evidence_summary_does_not_execute(self):
        from test_runtime import conduct, fixture
        workspace = conduct.Workspace(self.a)
        workspace.initialize(fixture())
        before = (self.a / '.conduct/state.json').read_bytes()
        runtime = harness.execution(self.a)
        self.assertEqual(runtime['status'], 'available')
        self.assertEqual(runtime['report']['tasks'][0]['depends_on'], [])
        self.assertNotEqual(runtime['report']['validation_status'], 'VERIFIED')
        self.assertEqual((self.a / '.conduct/state.json').read_bytes(), before)

    def test_invalid_runtime_preserves_task_editor(self):
        self.save(objective='Continue editing')
        (self.a / '.conduct/contract.json').write_text('{}', encoding='utf-8')
        self.assertEqual(prefs.view(self.a, 'intro')['execution']['status'], 'unavailable')
        self.assertEqual(prefs.view(self.a, 'intro')['harness']['brief']['data']['objective'], 'Continue editing')


if __name__ == '__main__':
    unittest.main()
