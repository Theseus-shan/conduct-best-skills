"""Discovery decisions, privacy and composition; synthetic adapters, no network."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/conduct-best-skills/scripts'
sys.path.insert(0, str(SCRIPTS))
from discovery import DiscoveryEngine, configure, context_checked, deduplicate, keywords
from discovery_core import DiscoveryError, parse_skill
from discovery_io import Budget, HttpClient


def candidate(provider='local', repo=None, name='literature-search', desc='Search literature and retrieve papers', revision='a' * 40, extra=''):
    source = {'provider': provider, 'repository': repo, 'path': 'skills/' + name + '/SKILL.md',
              'revision': revision, 'canonical_url': 'file:///synthetic/' + name if repo is None else
              'https://github.com/' + repo + '/blob/' + revision + '/skills/' + name + '/SKILL.md'}
    return parse_skill('---\nname: ' + name + '\ndescription: ' + desc + '\n' + extra + '---\nUse the evidence.\n', source, resources=[])


class FakeAdapter:
    def __init__(self, provider, rows=None, error=None):
        self.provider, self.rows, self.error = provider, rows or [], error
        self.level = {'local': 0, 'openai': 1, 'anthropic': 1, 'skills-sh': 2, 'skillsmp': 2, 'github': 3}[provider]
        self.external, self.diagnostics, self.calls = provider != 'local', [], 0

    def check_availability(self):
        return {'status': 'AVAILABLE'}

    def discover(self, query, context, filters):
        self.calls += 1
        self.sent_query = list(query)
        if self.error:
            raise self.error
        return copy.deepcopy(self.rows)


class DiscoveryEngineTests(unittest.TestCase):
    def run_engine(self, adapters, needs=('literature search',), query=('literature',), context=None, config=None, client=None):
        cfg = configure(overrides=config or {})
        return DiscoveryEngine(adapters, cfg, client or HttpClient(Budget())).run(list(query), list(needs), context)

    def test_local_sufficient_stops_before_remote_but_is_not_approval(self):
        local = FakeAdapter('local', [candidate()])
        remote = FakeAdapter('github', [candidate('github', 'acme/skills')])
        report = self.run_engine([local, remote], config={'allow_external': True})
        self.assertEqual(remote.calls, 0)
        self.assertEqual(report['stop_reason'], 'planning_coverage')
        self.assertEqual(report['composition']['missing'], [])
        self.assertEqual(report['composition']['not_ready'], ['literature search'])
        self.assertFalse(report['catalog']['capabilities'][0]['available'])
        self.assertEqual(report['sources'][-1]['status'], 'NOT_EXECUTED')

    def test_missing_capability_expands_and_composes_complementary_skills(self):
        a = FakeAdapter('local', [candidate(desc='Search literature')])
        b = FakeAdapter('anthropic', [candidate('anthropic', 'acme/read', 'paper-reading', 'Read papers')])
        report = self.run_engine([a, b], needs=('literature search', 'read papers'), config={'allow_external': True})
        self.assertEqual(b.calls, 1)
        self.assertEqual(len(report['composition']['selected']), 2)
        self.assertEqual(report['composition']['missing'], [])

    def test_native_capabilities_avoid_unneeded_skill_and_network(self):
        adapter = FakeAdapter('local', [candidate()])
        report = self.run_engine([adapter], context={'native_capabilities': ['literature search']})
        self.assertEqual(adapter.calls, 0)
        self.assertEqual(report['composition']['not_ready'], [])
        self.assertEqual(report['stop_reason'], 'native_coverage')

    def test_external_default_off_whitelist_level_and_enabled(self):
        for config in ({}, {'allow_external': True, 'allowed_sources': ['local']},
                       {'allow_external': True, 'max_level': 0},
                       {'allow_external': True, 'sources': {'github': {'enabled': False}}}):
            adapter = FakeAdapter('github', [candidate('github', 'acme/search')])
            report = self.run_engine([adapter], config=config)
            self.assertEqual(adapter.calls, 0)
            self.assertEqual(report['sources'][0]['status'], 'DISABLED')

    def test_each_source_failure_isolated_and_budget_stops(self):
        for code in ('NETWORK', 'RATE_LIMIT', 'AUTH', 'RESPONSE'):
            a = FakeAdapter('openai', error=DiscoveryError(code, 'Unavailable'))
            b = FakeAdapter('anthropic', [candidate('anthropic', 'acme/search')])
            result = self.run_engine([a, b], config={'allow_external': True})
            self.assertEqual(b.calls, 1)
            self.assertEqual(result['sources'][0]['status'], code)
        a = FakeAdapter('openai', error=DiscoveryError('BUDGET', 'Exhausted'))
        b = FakeAdapter('github')
        result = self.run_engine([a, b], config={'allow_external': True})
        self.assertEqual(b.calls, 0)
        self.assertEqual(result['stop_reason'], 'budget_exhausted')

    def test_dedup_preserves_registry_provenance_names_forks_and_versions(self):
        first = candidate('github', 'acme/search')
        second = candidate('skillsmp', 'acme/search')
        result = deduplicate([first, second, candidate('github', 'other/search'),
                              candidate('github', 'acme/search', revision='b' * 40)])
        self.assertEqual(len(result), 3)
        self.assertEqual(len(result[0]['discovery_records']), 2)
        self.assertEqual(result[0]['version_alternatives'], ['b' * 40])

    def test_conflicting_metadata_cannot_silently_upgrade_trust(self):
        a = candidate('github', 'acme/search')
        b = candidate('skillsmp', 'acme/search', desc='Search literature with altered metadata')
        result = self.run_engine([FakeAdapter('github', [a, b])], config={'allow_external': True})
        self.assertEqual(result['composition']['selected'], [])
        self.assertIn('conflicting_metadata', result['candidates'][0]['assessment']['excluded'])

    def test_duplicate_constraints_merge_conservatively(self):
        a = candidate('github', 'acme/search')
        b = candidate('skillsmp', 'acme/search')
        b['compatibility']['status'] = 'blocked'
        b['requirements']['mcp_servers'] = ['private-data']
        b['security']['permissions_required'] = ['credentials']
        rows = deduplicate([a, b])
        self.assertEqual(rows[0]['compatibility']['status'], 'blocked')
        self.assertEqual(rows[0]['requirements']['mcp_servers'], ['private-data'])
        self.assertEqual(rows[0]['security']['permissions_required'], ['credentials'])

    def test_relevant_local_candidate_beyond_output_limit_is_not_lost(self):
        rows = [candidate(name='unrelated-' + str(i), desc='Paint walls') for i in range(15)] + [candidate()]
        external = FakeAdapter('github')
        result = self.run_engine([FakeAdapter('local', rows), external], config={'allow_external': True, 'max_candidates': 2})
        self.assertEqual(result['composition']['missing'], [])
        self.assertEqual(external.calls, 0)

    def test_declared_dependencies_are_reported_missing(self):
        row = candidate(extra='metadata:\n  dependencies: [engine==9]\n')
        result = self.run_engine([FakeAdapter('local', [row])])
        self.assertIn('dependencies:engine==9', result['candidates'][0]['assessment']['missing_requirements'])

    def test_dependency_conflict_reports_gap_instead_of_false_coverage(self):
        a = candidate(desc='Search literature', extra='metadata:\n  dependencies: [engine==1]\n')
        b = candidate(name='paper-reader', desc='Read papers', extra='metadata:\n  dependencies: [engine==2]\n')
        result = self.run_engine([FakeAdapter('local', [a, b])], needs=('search literature', 'read papers'))
        self.assertEqual(len(result['composition']['selected']), 1)
        self.assertEqual(len(result['composition']['missing']), 1)
        self.assertEqual(result['composition']['conflicts'][0]['reason'], 'dependency_pins')

    def test_injection_and_denied_permissions_are_hard_exclusions(self):
        row = candidate()
        row['security']['risk_flags'] = ['prompt_injection']
        row['security']['review_status'] = 'blocked'
        result = self.run_engine([FakeAdapter('local', [row])], context={'approved_ids': [row['id']]})
        self.assertEqual(result['composition']['selected'], [])

    def test_executable_resource_manifest_requires_review_without_running(self):
        row = candidate()
        source = row['source']
        parsed = parse_skill('---\nname: literature-search\ndescription: Search literature\n---\nRun scripts/search.py when needed.\n',
                             source, resources=['scripts/search.py'])
        self.assertIn('unreviewed_executable_resources', parsed['security']['risk_flags'])
        self.assertEqual(parsed['security']['review_status'], 'review_required')
        row = candidate()
        row['security']['permissions_required'] = ['network']
        result = self.run_engine([FakeAdapter('local', [row])], context={'denied_permissions': ['network']})
        self.assertEqual(result['composition']['selected'], [])

    def test_platform_and_missing_tools_not_automatically_ready(self):
        row = candidate(extra='metadata:\n  requirements:\n    environment: [Windows]\n    tools: [tool-a]\n')
        result = self.run_engine([FakeAdapter('local', [row])], context={'platform': 'linux', 'approved_ids': [row['id']]})
        self.assertFalse(result['candidates'][0]['assessment']['available'])
        self.assertIn('platform_mismatch', result['candidates'][0]['assessment']['excluded'])
        result = self.run_engine([FakeAdapter('local', [row])], context={'platform': 'windows', 'approved_ids': [row['id']]})
        self.assertIn('tools:tool-a', result['candidates'][0]['assessment']['missing_requirements'])

    def test_explicit_host_approval_only_applies_to_current_local_metadata(self):
        row = candidate()
        result = self.run_engine([FakeAdapter('local', [row])], context={'approved_ids': [row['id']]})
        self.assertFalse(result['catalog']['capabilities'][0]['available'])
        self.assertTrue(result['candidates'][0]['assessment']['host_review_recorded'])
        row['resources'] = ['scripts/run.py']
        result = self.run_engine([FakeAdapter('local', [row])], context={'approved_ids': [row['id']]})
        self.assertFalse(result['catalog']['capabilities'][0]['available'])
        changed = candidate(revision='b' * 40)
        result = self.run_engine([FakeAdapter('local', [changed])], context={'approved_ids': [row['id']]})
        self.assertFalse(result['catalog']['capabilities'][0]['available'])
        self.assertFalse(result['candidates'][0]['assessment']['host_review_recorded'])

    def test_sensitive_queries_fail_before_any_adapter(self):
        a = FakeAdapter('github')
        for query in ['https://private.example/code', 'alice@example.com', 'C:\\private\\code', 'sk-secret123456789012', 'x' * 49]:
            with self.assertRaises(DiscoveryError):
                self.run_engine([a], query=(query,), config={'allow_external': True})
        self.assertEqual(a.calls, 0)
        with self.assertRaises(DiscoveryError):
            context_checked({'original_prompt': 'private source code'})

    def test_source_order_forced_all_and_minimized_query(self):
        a = FakeAdapter('local', [candidate()])
        b = FakeAdapter('github', [candidate('github', 'acme/search')])
        result = self.run_engine([a, b], context={'tools': ['PRIVATE_TOOL_NAME']},
                                 config={'allow_external': True, 'stop_when_covered': False})
        self.assertEqual(b.sent_query, ['literature'])
        self.assertEqual(b.calls, 1)
        self.assertEqual(result['stop_reason'], 'sources_exhausted')

    def test_invalid_candidate_and_stale_cache_do_not_pass(self):
        a = FakeAdapter('local', [{'name': 'broken'}, candidate()])
        result = self.run_engine([a])
        self.assertEqual(result['sources'][0]['invalid_candidates'], 1)
        row = candidate()
        row['observations'].append({'code': 'STALE_CACHE', 'message': 'old response'})
        result = self.run_engine([FakeAdapter('local', [row])])
        self.assertEqual(result['composition']['selected'], [])

    def test_config_is_strict_and_current_request_overrides_saved(self):
        self.assertFalse(configure({'allow_external': True}, {'allow_external': False})['allow_external'])
        for config in ({'api_key': 'no'}, {'max_level': 8}, {'max_requests': -1}, {'seconds': float('nan')},
                       {'sources': {'github': {'token': 'no'}}}, {'order': ['unknown']}, {'allow_external': 'yes'}):
            with self.assertRaises(DiscoveryError):
                configure(config)

    def test_cli_local_real_file_report_and_no_install_or_execution(self):
        scratch = ROOT / 'local' / 'discovery-engine-tests'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as tmp:
            path = Path(tmp)
            skill = path / 'skills' / 'literature-search'
            skill.mkdir(parents=True)
            (skill / 'SKILL.md').write_text('---\nname: literature-search\ndescription: Search literature\n---\nUse sources.\n', encoding='utf-8')
            base = [sys.executable, str(SCRIPTS / 'discovery.py'), '--workspace', tmp, '--root', 'skills', '--keyword', 'literature', '--need', 'literature search', '--no-cache']
            run = subprocess.run(base + ['--output', 'report.json'], capture_output=True, encoding='utf-8')
            self.assertEqual(run.returncode, 0, run.stderr)
            report = json.loads((path / 'report.json').read_text(encoding='utf-8'))
            self.assertEqual(report['composition']['missing'], [])
            self.assertEqual(report['requests_used'], 0)
            for flag in ('--install', '--execute', '--add-mcp'):
                run = subprocess.run(base + [flag], capture_output=True, encoding='utf-8')
                self.assertNotEqual(run.returncode, 0)
            self.assertFalse((path / '.agents').exists())
            run = subprocess.run([sys.executable, str(SCRIPTS / 'conduct.py'), '--workspace', tmp, 'discover',
                                  '--root', 'skills', '--keyword', 'literature', '--no-cache'], capture_output=True, encoding='utf-8')
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads(run.stdout)['requests_used'], 0)


if __name__ == '__main__':
    unittest.main()
