"""Lifecycle evidence, feedback, restart persistence and registered-project isolation."""
import json
import sys
from pathlib import Path
import unittest
from urllib.error import HTTPError
from urllib.request import Request

import test_preferences as fixtures
from test_preferences import prefs, urlopen, writing

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/conduct-best-skills/scripts"))
import activity
import workbench


class WorkbenchTests(unittest.TestCase):
    setUp = fixtures.PreferenceTests.setUp
    put = fixtures.PreferenceTests.put
    def invoke(self, root=None, call="call-1", task="intro", kind="skill", name="nature-writing"):
        root = root or self.a
        activity.set_enabled(root, True)
        return activity.record(root, task, kind, name, "invoked", call, work="manuscript")

    def test_selection_is_not_invocation_or_feedback(self):
        activity.set_enabled(self.a, True)
        activity.record(self.a, "intro", "skill", "nature-writing", "selected", "pick")
        report = activity.report(self.a)
        self.assertFalse(report["calls"][0]["invoked"])
        self.assertEqual(report["capabilities"][0]["invocations"], 0)
        with self.assertRaises(ValueError):
            activity.feedback(self.a, "pick", "helpful")

    def test_outcome_requires_observed_invocation_and_verification_evidence(self):
        activity.set_enabled(self.a, True)
        with self.assertRaises(ValueError):
            activity.record(self.a, "intro", "skill", "nature-writing", "succeeded", "missing")
        self.invoke()
        activity.record(self.a, "intro", "skill", "nature-writing", "succeeded", "call-1", work="manuscript")
        with self.assertRaises(ValueError):
            activity.record(self.a, "intro", "skill", "nature-writing", "verified", "call-1", work="manuscript")
        activity.record(self.a, "intro", "skill", "nature-writing", "verified", "call-1", evidence=["tool:check-1"], work="manuscript")
        report = activity.report(self.a)
        self.assertEqual(report["capabilities"][0]["verified"], 1)
        self.assertEqual(report["calls"][0]["rating"], "unknown")

    def test_user_feedback_is_separate_and_latest_correction_wins(self):
        self.invoke()
        activity.feedback(self.a, "call-1", "helpful", "结构清楚")
        activity.feedback(self.a, "call-1", "mixed", "后续仍需修改")
        report = activity.report(self.a)
        self.assertEqual(report["calls"][0]["rating"], "mixed")
        self.assertEqual(report["calls"][0]["outcome"], "unknown")
        self.assertEqual(report["capabilities"][0]["helpful"], 0)
        self.assertEqual(report["capabilities"][0]["mixed"], 1)

    def test_event_retry_is_idempotent_and_call_identity_is_bound(self):
        activity.set_enabled(self.a, True)
        for _ in range(2):
            activity.record(self.a, "intro", "tool", "python", "invoked", "python-1", event_id="same-event")
        self.assertEqual(activity.report(self.a)["recorded_events"], 1)
        with self.assertRaises(ValueError):
            activity.record(self.a, "other", "tool", "python", "succeeded", "python-1")

    def test_disable_preserves_history_and_report_is_project_local(self):
        self.invoke()
        activity.set_enabled(self.a, False)
        with self.assertRaises(ValueError):
            activity.record(self.a, "intro", "tool", "python", "invoked", "new")
        self.assertEqual(len(activity.report(self.a)["calls"]), 1)
        self.assertEqual(activity.report(self.b)["calls"], [])
        self.assertFalse((self.b / ".conduct").exists())

    def test_workbench_register_restart_and_unregister_preserve_project_data(self):
        home = self.root / "index"
        one = workbench.register(home, self.a, "论文 A")
        two = workbench.register(home, self.b, "仿真 B")
        self.invoke()
        self.assertEqual(len(workbench.load(home)["projects"]), 2)
        self.assertEqual(workbench.overview(home)[0]["invocations"], 1)
        workbench.register(home, self.a)
        self.assertEqual(len(workbench.load(home)["projects"]), 2)
        workbench.unregister(home, one["id"])
        self.assertEqual(len(activity.report(self.a)["calls"]), 1)
        self.assertEqual(workbench.project_root(home, two["id"]), self.b)
        with self.assertRaises(ValueError):
            workbench.project_root(home, one["id"])

    def test_onboarding_preserves_existing_project_instructions_and_is_repeatable(self):
        path = self.a / 'AGENTS.md'
        path.write_text('# Existing instructions\nPreserve this.\n', encoding='utf-8')
        workbench.onboard(self.root / 'index', self.a)
        first = path.read_text(encoding='utf-8')
        self.assertIn('Preserve this.', first)
        self.assertEqual(first.count('<!-- conduct-workbench:start -->'), 1)
        workbench.onboard(self.root / 'index', self.a)
        self.assertEqual(path.read_text(encoding='utf-8'), first)
        self.assertTrue(activity.read(self.a)['enabled'])
        self.assertFalse((self.b / 'AGENTS.md').exists())

    def test_codex_sync_is_idempotent_preserves_manual_projects_and_does_not_write_roots(self):
        home = self.root / 'index'
        workbench.register(home, self.b, 'Manual')
        self.put(writing())
        before = prefs.read(self.a)
        snapshot = {'schema_version': 1, 'projects': [
            {'projectId': 'native-a', 'label': '论文 A', 'path': str(self.a)},
            {'projectId': 'missing', 'label': 'Offline', 'path': str(self.root / 'missing')}],
            'threads': [{'id': 'chat-a', 'projectId': None, 'cwd': str(self.a), 'title': '<script>untrusted</script>', 'status': 'active'},
                        {'id': 'chat-other', 'projectId': 'another', 'cwd': str(self.a), 'title': 'Not ours', 'status': 'idle'}]}
        for _ in range(2):
            workbench.sync_codex(home, snapshot)
        data = workbench.load(home)
        self.assertEqual(len(data['projects']), 3)
        self.assertEqual(data['codex_sync']['chat_count'], 1)
        self.assertEqual(data['codex_chats'][0]['title'], '<script>untrusted</script>')
        self.assertEqual(prefs.read(self.a), before)
        self.assertFalse((self.b / '.conduct').exists())
        self.assertFalse((self.root / 'missing').exists())
        self.assertEqual(workbench.overview(home)[2]['status'], 'unavailable')
        snapshot['projects'][0]['label'] = 'Updated name'
        snapshot['projects'] = snapshot['projects'][:1]
        snapshot['threads'] = []
        workbench.sync_codex(home, snapshot)
        data = workbench.load(home)
        self.assertEqual(data['projects'][1]['name'], 'Updated name')
        self.assertFalse(data['projects'][2]['in_latest_snapshot'])
        self.assertEqual(data['projects'][0]['name'], 'Manual')
        self.assertEqual(data['codex_chats'], [])
        self.assertEqual(activity.report(self.a)['calls'], [])

    def test_invalid_codex_snapshot_cannot_partially_replace_registry(self):
        home = self.root / 'index'
        workbench.register(home, self.a)
        before = workbench.load(home)
        for projects in [[{'projectId': 'a', 'label': 'A', 'path': 'relative'}],
                         [{'projectId': 'a', 'label': 'A', 'path': str(self.a)}] * 2]:
            with self.assertRaises(ValueError):
                workbench.sync_codex(home, {'schema_version': 1, 'projects': projects})
            self.assertEqual(workbench.load(home), before)

    def test_web_project_switching_and_edits_stay_in_selected_registered_project(self):
        import threading
        home = self.root / "index"
        a = workbench.register(home, self.a)
        b = workbench.register(home, self.b)
        self.put(writing())
        workbench.sync_codex(home, {'schema_version': 1, 'projects': [
            {'projectId': 'native-b', 'label': 'B', 'path': str(self.b)}], 'threads': [
            {'id': 'chat-b', 'projectId': 'native-b', 'title': 'B chat', 'status': 'idle'}]})
        server = prefs.make_server(self.a, home=home)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = server.preference_url + 'api/preferences?project=' + b["id"]
            with urlopen(url, timeout=3) as response:
                data = json.load(response)
            self.assertEqual(data["project"]["data"]["rules"], [])
            self.assertEqual(len(data["projects"]), 2)
            self.assertEqual(data['codex_chats'][0]['title'], 'B chat')
            self.assertEqual(data['codex_sync']['coverage'], 'recent-chats-snapshot')
            request = Request(url, data=json.dumps({"data": {"schema_version": 1, "workflow": {"language": "English"}, "rules": []}, "revision": "missing"}).encode(), headers={"X-Conduct-Edit": "1"})
            with urlopen(request, timeout=3) as response:
                self.assertEqual(response.status, 200)
            self.assertEqual(prefs.read(self.a)["data"], writing())
            self.assertEqual(prefs.read(self.b)["data"]["workflow"]["language"], "English")
            with self.assertRaises(HTTPError) as error:
                urlopen(server.preference_url + 'api/preferences?project=unknown', timeout=3)
            self.assertEqual(error.exception.code, 422)
            error.exception.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


if __name__ == '__main__':
    unittest.main()
