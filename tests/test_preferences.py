"""Real preference isolation, precedence, editor concurrency and live reload."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import sys
import unittest
from urllib.error import HTTPError
from urllib.request import Request, build_opener, ProxyHandler

from test_runtime import ROOT, conduct, fixture
sys.path.insert(0, str(ROOT / "skills/conduct-best-skills/scripts"))

spec = importlib.util.spec_from_file_location("preferences", ROOT / "skills/conduct-best-skills/scripts/preferences.py")
prefs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prefs)
urlopen = build_opener(ProxyHandler({})).open


def writing():
    return {"schema_version": 1, "workflow": {"language": "中文"}, "rules": [
        {"id": "paper-style", "when": ["paper-writing"], "skills": ["Anti-Defensive Writing"],
         "instruction": "保留事实和必要局限", "enabled": True}]}


class PreferenceTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / "local/preference-tests"
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.a, self.b = self.root / "a", self.root / "b"
        self.a.mkdir()
        self.b.mkdir()

    def put(self, data, task=None, root=None):
        root = root or self.a
        return prefs.save(root, data, task, prefs.read(root, task)["revision"])

    def test_project_isolation_and_show_does_not_create_state(self):
        self.put(writing())
        self.assertEqual(prefs.resolve(self.a, types=["paper-writing"])["requested_skills"], ["Anti-Defensive Writing"])
        self.assertEqual(prefs.resolve(self.b, types=["paper-writing"])["requested_skills"], [])
        self.assertFalse((self.b / ".conduct").exists())

    def test_no_parent_inheritance(self):
        self.put(writing())
        nested = self.a / "nested"
        nested.mkdir()
        self.assertEqual(prefs.resolve(nested, types=["paper-writing"])["requested_skills"], [])

    def test_task_overlay_and_sibling_isolation(self):
        self.put(writing())
        task = {"schema_version": 1, "workflow": {"language": "English"}, "rules": [{"id": "paper-style", "enabled": False}]}
        self.put(task, "paper-a")
        result = prefs.resolve(self.a, "paper-a", ["paper-writing"])
        self.assertEqual(result["requested_skills"], [])
        self.assertEqual(result["workflow"]["language"], {"value": "English", "source": "task"})
        self.assertEqual(result["overridden"][0]["source"], "project")
        self.assertEqual(prefs.resolve(self.a, "paper-b", ["paper-writing"])["requested_skills"], ["Anti-Defensive Writing"])

    def test_prompt_override_is_transient_and_normalizes_skill_label(self):
        self.put(writing())
        before = prefs.location(self.a).read_bytes()
        result = prefs.resolve(self.a, types=["paper-writing"], excluded=["anti-defensive-writing"])
        self.assertEqual(result["requested_skills"], [])
        self.assertEqual(result["rules"][0]["status"], "prompt_excluded")
        self.assertEqual(prefs.location(self.a).read_bytes(), before)
        self.assertTrue(prefs.resolve(self.a, types=["paper-writing"])["requested_skills"])

    def test_current_context_is_view_only_and_updates(self):
        self.put(writing())
        prefs.context(self.a, "draft", ["paper-writing"], ["Anti-Defensive Writing"])
        self.assertEqual(prefs.view(self.a)["rules"][0]["status"], "prompt_excluded")
        self.assertTrue(prefs.resolve(self.a, "draft", ["paper-writing"])["requested_skills"])
        self.assertEqual(prefs.view(self.a, "other")["prompt_exclusions"], [])
        prefs.context(self.a, "draft", ["paper-writing"])
        self.assertEqual(prefs.view(self.a)["rules"][0]["status"], "active")

    def test_types_do_not_activate_on_unrelated_work_and_missing_context(self):
        self.put(writing())
        self.assertEqual(prefs.resolve(self.a, types=["coding"])["rules"][0]["status"], "not_matched")
        self.assertEqual(prefs.resolve(self.a)["rules"][0]["status"], "configured")
        result = prefs.resolve(self.a, types=["coding", "paper-writing"])
        self.assertEqual(result["invocation_status"], "NOT_CHECKED")
        self.assertTrue(result["requested_skills"])

    def test_additive_rules_deduplicate_selected_skills_and_partial_exclusion(self):
        data = writing()
        data["rules"][0]["skills"].append("citation-check")
        data["rules"].append({"id": "also", "when": ["*"], "skills": ["citation-check"]})
        self.put(data)
        result = prefs.resolve(self.a, types=["paper-writing"], excluded=["Anti-Defensive Writing"])
        self.assertEqual(result["requested_skills"], ["citation-check"])
        self.assertEqual(result["rules"][0]["status"], "partially_excluded")

    def test_init_preserves_user_edits_and_execution_initializes_after_preferences(self):
        self.put(writing())
        first = prefs.location(self.a).read_bytes()
        prefs.initialize(self.a)
        ws = conduct.Workspace(self.a)
        ws.initialize(fixture())
        self.assertEqual(first, prefs.location(self.a).read_bytes())
        with self.assertRaises(conduct.ContractError):
            ws.initialize(fixture())

    def test_stale_edit_rejected_without_losing_new_content(self):
        loaded = self.put(writing())
        changed = copy.deepcopy(writing())
        changed["workflow"]["language"] = "English"
        self.put(changed)
        with self.assertRaises(prefs.PreferenceError):
            prefs.save(self.a, writing(), expected=loaded["revision"])
        self.assertEqual(prefs.read(self.a)["data"], changed)

    def test_bad_config_is_visible_and_not_silently_replaced(self):
        self.put(writing())
        prefs.location(self.a).write_text('{broken', encoding="utf-8")
        with self.assertRaises(ValueError):
            prefs.resolve(self.a)
        with self.assertRaises(ValueError):
            prefs.initialize(self.a)
        self.assertEqual(prefs.location(self.a).read_text(), '{broken')

    def test_task_paths_reject_escape_and_windows_reserved_names(self):
        for task in ("../b", "a/b", "a\\b", "C:drive", "CON", "", "x" * 65):
            with self.subTest(task=task), self.assertRaises(prefs.PreferenceError):
                prefs.initialize(self.a, task)

    def test_schema_rejects_duplicate_ids_and_invalid_enabled_value(self):
        data = writing()
        data["rules"].append(copy.deepcopy(data["rules"][0]))
        with self.assertRaises(prefs.PreferenceError):
            self.put(data)

        data = writing()
        data["rules"][0]["enabled"] = "false"
        with self.assertRaises(prefs.PreferenceError):
            self.put(data)

    def test_natural_language_rule_maps_scene_and_keeps_instruction(self):
        result = prefs.parse_sentence('写论文时，默认使用 Anti-Defensive Writing 和 nature-writing，并保留必要局限。', 'writing')
        self.assertEqual(result['when'], ['paper-writing'])
        self.assertEqual(result['skills'], ['Anti-Defensive Writing', 'nature-writing'])
        self.assertEqual(result['instruction'], '保留必要局限')
        self.assertEqual(prefs.parse_sentence('跑仿真的时候，优先调用 simulation-runner', 'sim')['when'], ['simulation'])

    def test_unsupported_natural_language_does_not_silently_save(self):
        prefs.initialize(self.a)
        before = prefs.location(self.a).read_bytes()
        with self.assertRaises(prefs.PreferenceError):
            prefs.edit_rule(self.a, {'action':'save', 'sentence':'让我所有的东西都更好', 'revision':prefs.read(self.a)['revision']})
        self.assertEqual(prefs.location(self.a).read_bytes(), before)

    def test_natural_task_override_can_disable_inherited_rule(self):
        rule = prefs.parse_sentence('写论文时，默认使用 nature-writing', 'writing')
        self.put({'schema_version':1, 'workflow':{}, 'rules':[rule]})
        prefs.edit_rule(self.a, {'action':'save', 'task':'论文初稿', 'id':'writing', 'sentence':rule['sentence'], 'enabled':False, 'revision':'missing'})
        self.assertEqual(prefs.resolve(self.a, '论文初稿', ['paper-writing'])['requested_skills'], [])
        self.assertEqual(prefs.resolve(self.a, types=['paper-writing'])['requested_skills'], ['nature-writing'])
    def start_server(self):
        server = prefs.make_server(self.a)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def close():
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)
        self.addCleanup(close)
        return server.preference_url

    def test_live_server_reads_new_file_versions_and_context(self):
        self.put(writing())
        url = self.start_server()
        with urlopen(url, timeout=3) as response:
            self.assertIn('保存工作偏好', response.read().decode('utf-8'))
        prefs.context(self.a, types=["paper-writing"])
        with urlopen(url + 'api/preferences', timeout=3) as response:
            self.assertTrue(json.load(response)["requested_skills"])
        self.put(prefs.empty())
        with urlopen(url + 'api/preferences', timeout=3) as response:
            self.assertEqual(json.load(response)["requested_skills"], [])
        prefs.location(self.a).write_text('{bad', encoding='utf-8')
        with self.assertRaises(HTTPError) as error:
            urlopen(url + 'api/preferences', timeout=3)
        self.assertEqual(error.exception.code, 422)

    def test_editor_updates_and_rejects_stale_revision_or_unauthorized_post(self):
        loaded = self.put(writing())
        url = self.start_server() + 'api/preferences'
        body = json.dumps({"data": prefs.empty(), "revision": loaded["revision"]}).encode()
        request = Request(url, data=body, headers={"Content-Type": "application/json", "X-Conduct-Edit": "1"})
        with urlopen(request, timeout=3) as response:
            self.assertEqual(json.load(response)["data"], prefs.empty())
        with self.assertRaises(HTTPError) as error:
            urlopen(request, timeout=3)
        self.assertEqual(error.exception.code, 409)
        with self.assertRaises(HTTPError) as error:
            urlopen(Request(url, data=body), timeout=3)
        self.assertEqual(error.exception.code, 403)


if __name__ == '__main__':
    unittest.main()
