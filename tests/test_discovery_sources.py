"""Synthetic documented-interface fixtures, not live service acceptance tests."""
import json
import base64
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit, parse_qs

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills' / 'conduct-best-skills' / 'scripts'))
from discovery_core import DiscoveryError, validate_candidate
import discovery_sources
from discovery_sources import (LocalAdapter, OpenAIAdapter, AnthropicAdapter, SkillsShAdapter,
                               SkillsMPAdapter, GitHubSearchAdapter, GitHubReader,
                               build_adapters, github_locator, safe_relative)

SHA = 'a' * 40


def skill(name='csv', extra='', body='Read a local CSV and explain the columns.'):
    return '---\nname: ' + name + '\ndescription: Analyze CSV data.\n' + extra + '---\n' + body


class FakeBudget:
    def check(self):
        pass


class FakeClient:
    """Requests must match declared fixtures, so accidental networks fail the test."""
    def __init__(self, repositories=None, service=None, credentials=None):
        self.repositories = repositories or {}
        self.service, self.credentials = service, credentials or {}
        self.budget, self.cache, self.calls = FakeBudget(), None, []

    def credential(self, key):
        return self.credentials.get(key)

    def get_json(self, url, **kwargs):
        self.calls.append((url, kwargs))
        parsed = urlsplit(url)
        if parsed.hostname == 'api.github.com' and parsed.path.startswith('/repos/'):
            parts = parsed.path.strip('/').split('/')
            repo = '/'.join(parts[1:3])
            fixture = self.repositories[repo]
            if len(parts) == 3:
                return {'private': fixture.get('private', False), 'default_branch': 'main'}
            if parts[3] == 'commits':
                return {'sha': fixture.get('sha', SHA)}
            if parts[3:5] == ['git', 'trees']:
                return {'truncated': fixture.get('truncated', False), 'tree': [
                    {'path': path, 'type': 'blob', 'mode': '100644'} for path in fixture['files']]}
        if self.service:
            return self.service(url, kwargs)
        raise AssertionError('Unexpected fixture URL: ' + url)

    def get_text(self, url, **kwargs):
        self.calls.append((url, kwargs))
        parts = urlsplit(url).path.strip('/').split('/')
        if urlsplit(url).hostname != 'raw.githubusercontent.com':
            raise AssertionError('Unexpected metadata host')
        repo, revision, path = '/'.join(parts[:2]), parts[2], '/'.join(parts[3:])
        if revision != self.repositories[repo].get('sha', SHA):
            raise AssertionError('Unpinned request')
        value = self.repositories[repo]['files'][path]
        return json.dumps(value) if isinstance(value, dict) else value


class BudgetAfterOneSkillClient(FakeClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.skills_read = 0

    def get_text(self, url, **kwargs):
        if url.endswith('/SKILL.md'):
            if self.skills_read:
                raise DiscoveryError('BUDGET', 'Synthetic request budget exhausted')
            self.skills_read += 1
        return super().get_text(url, **kwargs)


class MemoryCache:
    def __init__(self):
        self.values = {}

    def get(self, bucket, key):
        return {'payload': self.values[(bucket, key)]} if (bucket, key) in self.values else None

    def put(self, bucket, key, payload, ttl):
        assert ttl == 86400
        self.values[(bucket, key)] = json.loads(json.dumps(payload))


class DiscoverySourceTests(unittest.TestCase):
    def test_raw_network_failure_uses_same_pinned_contents_file(self):
        fixture = {'acme/skills': {'files': {'skills/csv/SKILL.md': skill()}}}
        client = FakeClient(fixture, service=lambda url, kwargs: {'type': 'file', 'encoding': 'base64',
                            'content': base64.b64encode(skill().encode()).decode()})
        with patch.object(client, 'get_text', side_effect=DiscoveryError('NETWORK', 'offline raw')):
            adapter = AnthropicAdapter({}, client, self.root)
            rows = GitHubReader(adapter).candidates('acme/skills', ['csv'])
        self.assertEqual(rows[0]['name'], 'csv')
        self.assertTrue(any('/contents/skills/csv/SKILL.md?ref=' + SHA in url for url, _ in client.calls))
        self.assertIn('CONTENTS_FALLBACK', [x['code'] for x in adapter.diagnostics])

    def setUp(self):
        scratch = ROOT / 'local' / 'discovery-source-tests'
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='sources-', dir=scratch)
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def config(self, **kwargs):
        result = {'sources': {}, 'max_candidates': 8, 'max_files': 300, 'max_depth': 4, 'pages': 1}
        result.update(kwargs)
        return result

    def write(self, path, content):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
        return target

    def test_local_duplicates_broken_skill_and_changed_metadata(self):
        self.write('one/csv/SKILL.md', skill())
        second = self.write('two/csv/SKILL.md', skill())
        self.write('two/broken/SKILL.md', 'not a skill')
        config = self.config(sources={'local': {'roots': ['one', 'two']}})
        adapter = LocalAdapter(config, FakeClient(), self.root)
        rows = adapter.discover(['csv'], {}, {})
        self.assertEqual(len(rows), 2)
        self.assertNotEqual(rows[0]['id'], rows[1]['id'])
        self.assertTrue(adapter.diagnostics)
        before = {r['source']['path']: r['source']['revision'] for r in rows}
        second.write_text(skill(body='Now inspect CSV headers only.'), encoding='utf-8')
        after = adapter.discover(['csv'], {}, {})
        changed = next(r for r in after if r['source']['path'] == str(second.resolve()))
        self.assertNotEqual(changed['source']['revision'], before[str(second.resolve())])
        for row in after:
            validate_candidate(row)
            self.assertEqual(row['security']['review_status'], 'review_required')

    def test_local_resources_are_listed_without_executing(self):
        self.write('csv/SKILL.md', skill(body='See [helper](scripts/helper.py).'))
        self.write('csv/scripts/helper.py', 'raise RuntimeError("must never execute")')
        adapter = LocalAdapter(self.config(sources={'local': {'roots': ['csv']}}), FakeClient(), self.root)
        rows = adapter.discover([], {}, {})
        self.assertEqual(len(rows), 1)
        self.assertIn('scripts/helper.py', rows[0]['resources'])
        self.assertNotEqual(rows[0]['compatibility']['status'], 'blocked')
        self.assertFalse(rows[0]['local_observation']['resource_contents_reviewed'])

    def test_local_associated_metadata_changes_digest(self):
        self.write('csv/SKILL.md', skill())
        meta = self.write('csv/agents/openai.yaml', 'interface:\n  display_name: CSV\n')
        adapter = LocalAdapter(self.config(sources={'local': {'roots': ['csv/SKILL.md']}}), FakeClient(), self.root)
        a = adapter.discover([], {}, {})[0]
        meta.write_text('interface:\n  display_name: Better CSV\n', encoding='utf-8')
        b = adapter.discover([], {}, {})[0]
        self.assertNotEqual(a['source']['revision'], b['source']['revision'])

    def test_local_bounded_container(self):
        for n in range(6):
            self.write(f'container/csv{n}/SKILL.md', skill(f'csv{n}'))
        adapter = LocalAdapter(self.config(sources={'local': {'roots': ['container']}}, max_files=2), FakeClient(), self.root)
        rows = adapter.discover([], {}, {})
        self.assertEqual(len(rows), 2)
        self.assertTrue(any(d['code'] == 'FILE_LIMIT' for d in adapter.diagnostics))

    def test_local_symlink_requires_explicit_target_root(self):
        self.write('real/csv/SKILL.md', skill())
        link = self.root / 'linked'
        try:
            link.symlink_to(self.root / 'real', target_is_directory=True)
        except OSError:
            self.skipTest('OS account cannot create directory symlinks')
        config = self.config(sources={'local': {'roots': ['linked']}})
        adapter = LocalAdapter(config, FakeClient(), self.root)
        self.assertEqual(adapter.discover([], {}, {}), [])
        config['sources']['local']['allowed_symlink_roots'] = ['real']
        self.assertEqual(len(LocalAdapter(config, FakeClient(), self.root).discover([], {}, {})), 1)

    def test_official_plugins_keep_plugin_dependency_and_exclude_nested_skills(self):
        files = {'plugins/table/.codex-plugin/plugin.json': {'name': 'table', 'skills': './skills/', 'mcpServers': './.mcp.json'},
                 'plugins/table/.mcp.json': {'mcpServers': {'table-server': {'type': 'http', 'url': 'https://example.invalid'}}},
                 'plugins/table/skills/csv/SKILL.md': skill(),
                 'plugins/table/skills/tsv/SKILL.md': skill('tsv'),
                 'plugins/table/skills/csv/references/nested/SKILL.md': skill('nested')}
        client = FakeClient({'openai/plugins': {'files': files}})
        rows = OpenAIAdapter(self.config(), client, self.root).discover(['csv'], {}, {})
        self.assertEqual({r['name'] for r in rows}, {'csv', 'tsv'})
        for row in rows:
            validate_candidate(row)
            self.assertEqual(row['source']['revision'], SHA)
            self.assertIn('table-server', row['requirements']['mcp_servers'])
            self.assertEqual(row['source']['plugin']['installation_unit'], 'plugin')

    def test_portable_plugin_inline_overlay_replaces_legacy(self):
        files = {'plugins/table/plugin.json': {'name': 'table', 'extensions': {'com.openai': {}}},
                 'plugins/table/.codex-plugin/plugin.json': {'name': 'old', 'skills': './wrong/', 'mcpServers': './.mcp.json'},
                 'plugins/table/.mcp.json': {'mcpServers': {'must-not-inherit': {}}},
                 'plugins/table/skills/csv/SKILL.md': skill()}
        rows = OpenAIAdapter(self.config(), FakeClient({'openai/plugins': {'files': files}}), self.root).discover(['csv'], {}, {})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['source']['plugin']['format'], 'portable')
        self.assertNotIn('must-not-inherit', rows[0]['requirements']['mcp_servers'])

    def test_anthropic_spec_valid_does_not_mean_codex_ready(self):
        files = {'skills/csv/SKILL.md': skill(extra='license: Proprietary\n', body='Use the Claude Code Bash tool.')}
        rows = AnthropicAdapter(self.config(), FakeClient({'anthropics/skills': {'files': files}}), self.root).discover(['csv'], {}, {})
        self.assertEqual(rows[0]['compatibility']['status'], 'conditional')
        self.assertEqual(rows[0]['license']['identifier'], 'Proprietary')
        self.assertNotEqual(rows[0]['security']['review_status'], 'approved')

    def test_private_repo_is_rejected_before_file_fetch(self):
        client = FakeClient({'example/private': {'private': True, 'files': {'SKILL.md': skill()}}})
        reader = GitHubReader(GitHubSearchAdapter(self.config(), client, self.root))
        with self.assertRaises(DiscoveryError) as caught:
            reader.candidates('example/private', ['csv'])
        self.assertEqual(caught.exception.code, 'PRIVATE_REPOSITORY')
        self.assertEqual(len(client.calls), 1)

    def test_registry_metadata_is_resolved_to_pinned_skill(self):
        def service(url, kwargs):
            self.assertEqual(urlsplit(url).path, '/api/v1/skills/search')
            return {'success': True, 'data': {'skills': [{'id': 'registry1', 'name': 'csv', 'stars': 999,
                'githubUrl': 'https://github.com/example/public/tree/main/skills/csv'}], 'pagination': {'hasNext': False}}}
        client = FakeClient({'example/public': {'files': {'skills/csv/SKILL.md': skill()}}}, service)
        rows = SkillsMPAdapter(self.config(), client, self.root).discover(['csv'], {}, {})
        self.assertEqual(rows[0]['source']['revision'], SHA)
        self.assertFalse(rows[0]['registry_observation']['quality_verified'])
        self.assertEqual(rows[0]['security']['trust_level'], 'unverified')
        self.assertNotIn('Authorization', client.calls[0][1]['headers'])

    def test_skills_sh_missing_oidc_has_no_network_or_cli(self):
        client = FakeClient()
        adapter = SkillsShAdapter(self.config(), client, self.root)
        self.assertEqual(adapter.check_availability()['status'], 'CREDENTIAL_REQUIRED')
        self.assertEqual(adapter.discover(['csv'], {}, {}), [])
        self.assertEqual(client.calls, [])

    def test_skills_sh_documented_api_preserves_upstream_observation(self):
        def service(url, kwargs):
            self.assertEqual(urlsplit(url).path, '/api/v1/skills/search')
            self.assertEqual(kwargs['headers']['Authorization'], 'Bearer synthetic-oidc')
            return {'data': [{'id': 'id1', 'slug': 'csv', 'name': 'CSV', 'source': 'example/public', 'installs': 400}]}
        client = FakeClient({'example/public': {'files': {'skills/csv/SKILL.md': skill()}}}, service,
                            {'VERCEL_OIDC_TOKEN': 'synthetic-oidc'})
        rows = SkillsShAdapter(self.config(), client, self.root).discover(['csv'], {}, {})
        self.assertEqual(rows[0]['registry_observation']['popularity'], 400)
        self.assertNotIn('synthetic-oidc', json.dumps(rows))

    def test_skillsmp_uncertain_completion_not_retried(self):
        client = FakeClient(service=lambda *args: {'success': False, 'error': {'code': 'SEARCH_COMPLETION_UNCERTAIN'}})
        adapter = SkillsMPAdapter(self.config(pages=3), client, self.root)
        with self.assertRaises(DiscoveryError) as caught:
            adapter.discover(['csv'], {}, {})
        self.assertEqual(caught.exception.code, 'SEARCH_COMPLETION_UNCERTAIN')
        self.assertEqual(len(client.calls), 1)

    def test_registry_later_page_failure_keeps_prior_leads(self):
        def service(url, kwargs):
            if parse_qs(urlsplit(url).query)['page'] == ['2']:
                raise DiscoveryError('RATE_LIMIT', 'synthetic throttling')
            return {'success': True, 'data': {'skills': [{'name': 'csv', 'githubUrl': 'https://github.com/example/public'}],
                                               'pagination': {'hasNext': True}}}
        client = FakeClient({'example/public': {'files': {'SKILL.md': skill()}}}, service)
        adapter = SkillsMPAdapter(self.config(pages=2), client, self.root)
        rows = adapter.discover(['csv'], {}, {})
        self.assertEqual(len(rows), 1)
        self.assertIn('RATE_LIMIT', [d['code'] for d in adapter.diagnostics])

    def test_registry_name_mismatch_does_not_attach_popularity_to_other_skills(self):
        client = FakeClient({'example/public': {'files': {'skills/other/SKILL.md': skill('other')}}})
        adapter = SkillsMPAdapter(self.config(), client, self.root)
        rows = adapter.resolve_items([{'name': 'missing', 'githubUrl': 'https://github.com/example/public', 'stars': 99999}], ['csv'])
        self.assertEqual(rows, [])
        self.assertIn('NAME_NOT_FOUND', [d['code'] for d in adapter.diagnostics])

    def test_incomplete_tree_does_not_invent_missing_resource(self):
        client = FakeClient({'anthropics/skills': {'truncated': True, 'files': {
            'skills/csv/SKILL.md': skill(body='See [helper](scripts/helper.py).')}}})
        adapter = AnthropicAdapter(self.config(), client, self.root)
        rows = adapter.discover(['csv'], {}, {})
        self.assertEqual(len(rows), 1)
        self.assertNotEqual(rows[0]['compatibility']['status'], 'blocked')
        self.assertIn('RESOURCE_LIMIT', [d['code'] for d in adapter.diagnostics])

    def test_github_anonymous_repository_search_validates_content(self):
        def service(url, kwargs):
            self.assertEqual(urlsplit(url).path, '/search/repositories')
            self.assertIn('is:public', parse_qs(urlsplit(url).query)['q'][0])
            return {'incomplete_results': True, 'items': [{'full_name': 'example/public'}]}
        client = FakeClient({'example/public': {'files': {'skills/bad/SKILL.md': 'not valid', 'skills/csv/SKILL.md': skill()}}}, service)
        adapter = GitHubSearchAdapter(self.config(), client, self.root)
        rows = adapter.discover(['csv'], {}, {})
        self.assertEqual(len(rows), 1)
        self.assertTrue(any(d['code'] == 'INCOMPLETE_RESULTS' for d in adapter.diagnostics))

    def test_github_authenticated_code_search_uses_commit_not_blob_sha(self):
        def service(url, kwargs):
            self.assertEqual(urlsplit(url).path, '/search/code')
            return {'items': [{'path': 'skills/csv/SKILL.md', 'sha': 'b' * 40, 'repository': {'full_name': 'example/public'}}]}
        client = FakeClient({'example/public': {'files': {'skills/csv/SKILL.md': skill()}}}, service, {'GITHUB_TOKEN': 'synthetic'})
        row = GitHubSearchAdapter(self.config(), client, self.root).discover(['csv'], {}, {})[0]
        self.assertEqual(row['source']['revision'], SHA)

    def test_github_and_manifest_paths_reject_escape_or_unapproved_hosts(self):
        for value in ('../outside', './skills/../outside', 'C:/keys', '/root', 'skills\\csv'):
            with self.assertRaises(DiscoveryError):
                safe_relative(value)
        for url in ('http://github.com/example/public', 'https://github.com.evil.test/a/b',
                    'https://token@github.com/a/b', 'https://github.com/a/b?secret=x',
                    'https://github.com/a/b/blob/main/%2e%2e/SKILL.md'):
            self.assertIsNone(github_locator(url))

    def test_factory_contract_and_source_enabling(self):
        adapters = build_adapters(self.config(), FakeClient(), self.root)
        self.assertEqual([a.provider for a in adapters], ['local', 'openai', 'anthropic', 'skills-sh', 'skillsmp', 'github'])
        disabled = LocalAdapter(self.config(sources={'local': {'enabled': False}}), FakeClient(), self.root)
        self.assertEqual(disabled.check_availability()['status'], 'DISABLED')
        self.assertFalse(disabled.get_capabilities()['execute'])
        with self.assertRaises(DiscoveryError):
            build_adapters(self.config(order=['github', 'github']), FakeClient(), self.root)

    def test_official_budget_preserves_one_validated_candidate(self):
        files = {'skills/csv-one/SKILL.md': skill('csv-one'), 'skills/csv-two/SKILL.md': skill('csv-two')}
        client = BudgetAfterOneSkillClient({'anthropics/skills': {'files': files}})
        adapter = AnthropicAdapter(self.config(), client, self.root)
        rows = adapter.discover(['csv'], {}, {})
        self.assertEqual(len(rows), 1)
        self.assertIn('BUDGET', [d['code'] for d in adapter.diagnostics])
        tree_call = next(kwargs for url, kwargs in client.calls if '/git/trees/' in url)
        self.assertEqual(tree_call['max_bytes'], 8_000_000)
        info_call = next(kwargs for url, kwargs in client.calls if url.endswith('/repos/anthropics/skills'))
        self.assertEqual(info_call['max_bytes'], 2_000_000)

    def test_openai_budget_preserves_one_validated_candidate(self):
        files = {'plugins/table/plugin.json': {'name': 'table'},
                 'plugins/table/skills/csv-one/SKILL.md': skill('csv-one'),
                 'plugins/table/skills/csv-two/SKILL.md': skill('csv-two')}
        client = BudgetAfterOneSkillClient({'openai/plugins': {'files': files}})
        adapter = OpenAIAdapter(self.config(), client, self.root)
        self.assertEqual(len(adapter.discover(['csv'], {}, {})), 1)
        self.assertIn('BUDGET', [d['code'] for d in adapter.diagnostics])

    def test_registry_budget_preserves_one_resolved_candidate(self):
        files = {'skills/csv-one/SKILL.md': skill('csv-one'), 'skills/csv-two/SKILL.md': skill('csv-two')}
        client = BudgetAfterOneSkillClient({'example/public': {'files': files}})
        adapter = SkillsMPAdapter(self.config(), client, self.root)
        rows = adapter.resolve_items([{'name': name, 'githubUrl': 'https://github.com/example/public'}
                                      for name in ('csv-one', 'csv-two')], ['csv'])
        self.assertEqual(len(rows), 1)
        self.assertIn('BUDGET', [d['code'] for d in adapter.diagnostics])

    def test_registry_page_budget_preserves_prior_page_candidate(self):
        def service(url, kwargs):
            if parse_qs(urlsplit(url).query)['page'] == ['2']:
                raise DiscoveryError('BUDGET', 'Synthetic request budget exhausted')
            return {'success': True, 'data': {'skills': [{'name': 'csv', 'githubUrl': 'https://github.com/example/public'}],
                                               'pagination': {'hasNext': True}}}
        client = FakeClient({'example/public': {'files': {'SKILL.md': skill()}}}, service)
        adapter = SkillsMPAdapter(self.config(pages=2), client, self.root)
        self.assertEqual(len(adapter.discover(['csv'], {}, {})), 1)
        self.assertIn('BUDGET', [d['code'] for d in adapter.diagnostics])

    def test_github_budget_preserves_reader_partial_results(self):
        service = lambda *args: {'items': [{'full_name': 'example/public'}]}
        files = {'skills/csv-one/SKILL.md': skill('csv-one'), 'skills/csv-two/SKILL.md': skill('csv-two')}
        client = BudgetAfterOneSkillClient({'example/public': {'files': files}}, service)
        adapter = GitHubSearchAdapter(self.config(), client, self.root)
        self.assertEqual(len(adapter.discover(['csv'], {}, {})), 1)
        self.assertIn('BUDGET', [d['code'] for d in adapter.diagnostics])

    def test_local_budget_preserves_first_skill(self):
        self.write('container/csv-one/SKILL.md', skill('csv-one'))
        self.write('container/csv-two/SKILL.md', skill('csv-two'))
        class ThreeChecks:
            used = 0
            def check(self):
                self.used += 1
                if self.used > 3:
                    raise DiscoveryError('BUDGET', 'Synthetic time budget exhausted')
        client = FakeClient()
        client.budget = ThreeChecks()
        adapter = LocalAdapter(self.config(sources={'local': {'roots': ['container']}}), client, self.root)
        self.assertEqual(len(adapter.discover([], {}, {})), 1)
        self.assertIn('BUDGET', [d['code'] for d in adapter.diagnostics])

    def test_budget_before_any_candidate_still_raises(self):
        client = BudgetAfterOneSkillClient({'anthropics/skills': {'files': {'skills/csv/SKILL.md': skill()}}})
        client.skills_read = 1
        with self.assertRaises(DiscoveryError) as caught:
            AnthropicAdapter(self.config(), client, self.root).discover(['csv'], {}, {})
        self.assertEqual(caught.exception.code, 'BUDGET')

    def test_local_metadata_cache_hit_refresh_and_new_discovered_at(self):
        self.write('csv/SKILL.md', skill())
        client = FakeClient()
        client.cache, client.events, client.refresh = MemoryCache(), [], set()
        adapter = LocalAdapter(self.config(sources={'local': {'roots': ['csv']}}), client, self.root)
        with patch('discovery_sources.parse_skill', wraps=discovery_sources.parse_skill) as parser:
            adapter.discover([], {}, {})
            with patch('discovery_sources.now', return_value='2040-01-01T00:00:00+00:00'):
                row = adapter.discover([], {}, {})[0]
            self.assertEqual(parser.call_count, 1)
            self.assertEqual(row['provenance']['discovered_at'], '2040-01-01T00:00:00+00:00')
            client.refresh.add('local')
            adapter.discover([], {}, {})
            self.assertEqual(parser.call_count, 2)
        self.assertEqual([event['cache'] for event in client.events], ['MISS', 'HIT', 'MISS'])

    def test_local_cache_invalidates_metadata_resource_manifest_and_parser(self):
        text = self.write('csv/SKILL.md', skill())
        parser_file = self.write('parser-fixture.py', '# parser version one')
        client = FakeClient()
        client.cache = MemoryCache()
        adapter = LocalAdapter(self.config(sources={'local': {'roots': ['csv']}}), client, self.root)
        with patch('discovery_sources.discovery_core.__file__', str(parser_file)):
            with patch('discovery_sources.parse_skill', wraps=discovery_sources.parse_skill) as parser:
                adapter.discover([], {}, {})
                text.write_text(skill(body='Inspect the CSV header.'), encoding='utf-8')
                adapter.discover([], {}, {})
                self.write('csv/references/guide.md', 'Resource only; never executed.')
                adapter.discover([], {}, {})
                self.write('csv/agents/openai.yaml', 'interface:\n  display_name: CSV\n')
                adapter.discover([], {}, {})
                parser_file.write_text('# parser version two', encoding='utf-8')
                adapter.discover([], {}, {})
                self.assertEqual(parser.call_count, 5)

    def test_invalid_local_cache_is_reparsed_not_accepted(self):
        self.write('csv/SKILL.md', skill())
        client = FakeClient()
        client.cache = MemoryCache()
        adapter = LocalAdapter(self.config(sources={'local': {'roots': ['csv']}}), client, self.root)
        adapter.discover([], {}, {})
        record = next(iter(client.cache.values.values()))
        record['security']['review_status'] = 'approved'
        rows = adapter.discover([], {}, {})
        self.assertEqual(rows[0]['security']['review_status'], 'review_required')
        self.assertIn('CACHE_INVALID', [d['code'] for d in adapter.diagnostics])


if __name__ == '__main__':
    unittest.main()
