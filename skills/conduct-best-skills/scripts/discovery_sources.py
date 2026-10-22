"""Read-only Skill discovery adapters. Remote content is data, never executed."""
import hashlib
import base64
import copy
import json
import os
from pathlib import Path, PurePosixPath
import re
from urllib.parse import quote, urlencode, urlsplit, unquote

import discovery_core
from discovery_core import DiscoveryError, now, parse_skill, validate_candidate


PROVIDERS = ('local', 'openai', 'anthropic', 'skills-sh', 'skillsmp', 'github')
SHA = re.compile(r'^[0-9a-fA-F]{40}$')
REPO = re.compile(r'^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$')
SKIP_DIRS = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', '.conduct-discovery'}


def safe_relative(value):
    """Repository and manifest paths must stay inside their declared root."""
    if not isinstance(value, str) or not value or '\\' in value or '\x00' in value:
        raise DiscoveryError('PATH', 'Invalid source-relative path')
    value = value[2:] if value.startswith('./') else value
    parts = PurePosixPath(value).parts
    if not parts or value.startswith('/') or any(p in {'.', '..'} or ':' in p for p in parts):
        raise DiscoveryError('PATH', 'Source-relative path escapes its root')
    return '/'.join(parts)


def github_locator(value):
    """Resolve public GitHub locators only; no arbitrary URL fetching."""
    if not isinstance(value, str):
        return None
    if REPO.fullmatch(value):
        return {'repository': value, 'path': None, 'ref': None}
    try:
        url = urlsplit(value)
        if (url.scheme != 'https' or url.hostname not in {'github.com', 'raw.githubusercontent.com'}
                or url.username or url.password or url.query or url.fragment or url.port not in {None, 443}):
            return None
        parts = [unquote(p) for p in url.path.strip('/').split('/')]
        if len(parts) < 2:
            return None
        repo = '/'.join(parts[:2]).removesuffix('.git')
        if not REPO.fullmatch(repo):
            return None
        path = ref = None
        if url.hostname == 'raw.githubusercontent.com' and len(parts) >= 4:
            ref, path = parts[2], '/'.join(parts[3:])
        elif len(parts) >= 5 and parts[2] in {'blob', 'tree'}:
            ref, path = parts[3], '/'.join(parts[4:])
            if parts[2] == 'tree':
                path = path.rstrip('/') + '/SKILL.md'
        elif len(parts) > 2:
            return None
        return {'repository': repo, 'path': safe_relative(path) if path else None, 'ref': ref}
    except (ValueError, DiscoveryError):
        return None


class Adapter:
    provider, level, external = '', 0, True

    def __init__(self, config, client, workspace):
        self.config, self.client = config, client
        self.workspace = Path(workspace).resolve()
        self.settings = config.get('sources', {}).get(self.provider, {})
        self.diagnostics = []
        self.limit = config.get('max_candidates', 8)
        self.max_files = config.get('max_files', 300)
        self.max_depth = config.get('max_depth', 4)
        self.pages = config.get('pages', 1)

    def note(self, code, message):
        # Never expose caught exception text, request headers or server error bodies.
        entry = {'code': code, 'message': message}
        if entry not in self.diagnostics:
            self.diagnostics.append(entry)

    def caught(self, error):
        if isinstance(error, DiscoveryError) and error.code == 'BUDGET':
            raise error
        code = error.code if isinstance(error, DiscoveryError) else 'READ_FAILED'
        self.note(code, 'A source item could not be read or validated; other items may remain available')

    def stop_after_error(self, error, rows):
        """Keep already validated results when the remaining budget runs out."""
        if isinstance(error, DiscoveryError) and error.code == 'BUDGET' and rows:
            self.note('BUDGET', 'Discovery budget exhausted; previously validated candidates were preserved')
            return True
        self.caught(error)
        return False

    def budget_stopped(self):
        return any(item['code'] == 'BUDGET' for item in self.diagnostics)

    def check_availability(self):
        if self.settings.get('enabled', True) is False:
            return {'status': 'DISABLED', 'reason': 'Source disabled by configuration'}
        return {'status': 'AVAILABLE', 'reason': 'Configuration checked; connectivity and authentication not tested'}

    def get_capabilities(self):
        return {'provider': self.provider, 'level': self.level, 'external': self.external,
                'metadata': True, 'immutable_revision': self.external, 'execute': False, 'install': False}

    def get_metadata(self, candidate):
        return candidate

    def resolve_source(self, candidate):
        return candidate['source']


class LocalAdapter(Adapter):
    provider, level, external = 'local', 0, False

    def roots(self):
        configured = self.settings.get('roots')
        if configured is not None:
            return [Path(p) if Path(p).is_absolute() else self.workspace / p for p in configured]
        # Scan only canonical skill containers, never arbitrary project contents.
        ancestors, cursor = [], self.workspace
        while True:
            ancestors.append(cursor)
            if (cursor / '.git').exists():
                break
            if cursor.parent == cursor:
                ancestors = [self.workspace]
                break
            cursor = cursor.parent
        roots = [p / '.agents' / 'skills' for p in ancestors]
        roots.extend([Path.home() / '.agents' / 'skills', Path.home() / '.codex' / 'skills'])
        if os.name != 'nt':
            roots.append(Path('/etc/codex/skills'))
        return roots

    def _allowed_link(self, path):
        for part in (path, *path.parents):
            if not part.is_symlink() and not (hasattr(part, 'is_junction') and part.is_junction()):
                continue
            target = part.resolve()
            allowed_target = False
            for root in self.settings.get('allowed_symlink_roots', []):
                allowed = Path(root)
                allowed = (allowed if allowed.is_absolute() else self.workspace / allowed).resolve()
                if target == allowed or allowed in target.parents:
                    allowed_target = True
                    break
            if not allowed_target:
                self.note('SYMLINK_SKIPPED', 'A symlink or junction needs an explicitly allowed target root')
                return False
        return True

    def resources(self, root):
        paths, stack, visited = [], [(root, 0)], set()
        while stack:
            path, depth = stack.pop()
            self.client.budget.check()
            if not self._allowed_link(path) or path.resolve() in visited:
                continue
            visited.add(path.resolve())
            with os.scandir(path) as entries:
                for entry in entries:
                    if len(paths) >= self.max_files:
                        self.note('RESOURCE_LIMIT', 'Resource listing truncated; missing resources cannot be determined')
                        return None
                    child = Path(entry.path)
                    if not self._allowed_link(child):
                        continue
                    paths.append(child.relative_to(root).as_posix())
                    if entry.is_dir(follow_symlinks=True) and entry.name not in SKIP_DIRS:
                        if depth < self.max_depth:
                            stack.append((child, depth + 1))
                        else:
                            self.note('RESOURCE_LIMIT', 'Resource depth truncated; missing resources cannot be determined')
                            return None
        return paths

    @staticmethod
    def read(path):
        if path.stat().st_size > 1_000_000:
            raise DiscoveryError('SIZE_LIMIT', 'Skill metadata exceeds local read budget')
        return path.read_text(encoding='utf-8-sig')

    def discover(self, query, context, filters):
        rows, seen, visited, walked = [], set(), set(), 0
        cache = getattr(self.client, 'cache', None)
        try:
            parser_hash = hashlib.sha256(Path(discovery_core.__file__).read_bytes()).hexdigest()
        except OSError:
            parser_hash, cache = None, None
        for root in self.roots():
            stack = [(root, 0)]
            while stack:
                path, depth = stack.pop()
                try:
                    self.client.budget.check()
                    if not self._allowed_link(path):
                        continue
                    if not path.exists():
                        continue
                    resolved = path.resolve()
                    if path.is_file():
                        files = [path] if path.name == 'SKILL.md' else []
                    else:
                        if resolved in visited:
                            continue
                        visited.add(resolved)
                        files = [path / 'SKILL.md'] if (path / 'SKILL.md').is_file() else []
                        if not files and depth < self.max_depth:
                            if walked >= self.max_files:
                                self.note('FILE_LIMIT', 'Local directory-entry budget reached; inventory is partial')
                                continue
                            children = []
                            with os.scandir(path) as entries:
                                for entry in entries:
                                    if walked >= self.max_files:
                                        self.note('FILE_LIMIT', 'Local directory-entry budget reached; inventory is partial')
                                        break
                                    walked += 1
                                    if entry.name not in SKIP_DIRS and entry.is_dir(follow_symlinks=True):
                                        children.append(Path(entry.path))
                            stack.extend((p, depth + 1) for p in sorted(children, reverse=True))
                        elif not files:
                            self.note('DEPTH_LIMIT', 'Local depth budget reached; inventory may be partial')
                    for skill in files:
                        if not self._allowed_link(skill):
                            continue
                        resolved_skill = skill.resolve()
                        if resolved_skill in seen:
                            continue
                        seen.add(resolved_skill)
                        content = self.read(skill)
                        associated = {}
                        yaml = skill.parent / 'agents' / 'openai.yaml'
                        if yaml.is_file() and self._allowed_link(yaml.parent) and self._allowed_link(yaml):
                            associated['agents/openai.yaml'] = self.read(yaml)
                        resources = self.resources(skill.parent)
                        digest = hashlib.sha256(content.encode())
                        for key, value in sorted(associated.items()):
                            digest.update(key.encode() + b'\x00' + value.encode())
                        source = {'provider': self.provider, 'repository': None, 'path': str(resolved_skill),
                                  'revision': digest.hexdigest(),
                                  'canonical_url': resolved_skill.as_uri(), 'method': 'local-read'}
                        # Always reread metadata and enumerate resources before consulting this cache.
                        cache_key = 'local-metadata:' + json.dumps([str(resolved_skill), source['revision'],
                            sorted(resources) if resources is not None else None, parser_hash],
                            ensure_ascii=False, separators=(',', ':'))
                        row = None
                        if cache is not None and 'local' not in getattr(self.client, 'refresh', ()):
                            try:
                                hit = cache.get('metadata', cache_key)
                                if hit:
                                    candidate = copy.deepcopy(hit['payload'])
                                    validate_candidate(candidate)
                                    if candidate['source'] != source:
                                        raise DiscoveryError('CACHE_INVALID', 'Cached metadata source does not match current file')
                                    row = candidate
                                    row['provenance']['discovered_at'] = now()
                                    if hasattr(self.client, 'events'):
                                        self.client.events.append({'provider': self.provider, 'cache': 'HIT', 'bucket': 'metadata'})
                            except (DiscoveryError, OSError, KeyError, TypeError, ValueError):
                                self.note('CACHE_INVALID', 'Invalid local metadata cache ignored; current files are parsed')
                        if row is None:
                            row = parse_skill(content, source, resources=resources, associated=associated)
                            if hasattr(self.client, 'events'):
                                self.client.events.append({'provider': self.provider, 'cache': 'MISS', 'bucket': 'metadata'})
                        row['local_observation'] = {'discovered_path': str(skill),
                            'resolved_path': str(resolved_skill), 'host_enabled': 'unknown',
                            'revision_scope': 'skill_and_associated_metadata_only',
                            'resource_contents_reviewed': False,
                            'root_kind': 'legacy-compatibility' if '.codex' in skill.parts else 'configured-or-canonical'}
                        if cache is not None:
                            try:
                                cache.put('metadata', cache_key, row, 86400)
                            except (DiscoveryError, OSError, ValueError, TypeError):
                                self.note('CACHE_WRITE_FAILED', 'Local metadata cache could not be saved; candidate remains available for review')
                        rows.append(row)
                        if len(rows) >= self.max_files:
                            self.note('FILE_LIMIT', 'Local skill budget reached; inventory is partial')
                            return rows
                except (DiscoveryError, OSError, UnicodeError, ValueError, RuntimeError) as error:
                    if self.stop_after_error(error, rows):
                        return rows
        return rows


class GitHubReader:
    """Public-repository verifier shared by official, registry and search adapters."""
    def __init__(self, adapter):
        self.a, self.client = adapter, adapter.client
        self.repos, self.trees, self.tree_complete = {}, {}, {}

    def headers(self):
        headers = {'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2026-03-10'}
        token = self.client.credential('GITHUB_TOKEN')
        if token:
            headers['Authorization'] = 'Bearer ' + token
        return headers

    def json(self, path, bucket='metadata', ttl=None, max_bytes=2_000_000):
        return self.client.get_json('https://api.github.com/' + path, provider=self.a.provider,
                                    bucket=bucket, headers=self.headers(), ttl=ttl, max_bytes=max_bytes)

    def repository(self, repo, ref=None):
        if not isinstance(repo, str) or not REPO.fullmatch(repo):
            raise DiscoveryError('REPOSITORY', 'Invalid repository identifier')
        key = (repo.lower(), ref)
        if key in self.repos:
            return self.repos[key]
        info = self.json('repos/' + repo, ttl=3600)
        if not isinstance(info, dict) or info.get('private') is not False:
            raise DiscoveryError('PRIVATE_REPOSITORY', 'Only verified public repositories are eligible')
        revision = ref or info.get('default_branch')
        if not isinstance(revision, str) or not revision or len(revision) > 160:
            raise DiscoveryError('REVISION', 'Repository has no usable revision')
        commit = self.json('repos/' + repo + '/commits/' + quote(revision, safe=''), ttl=3600)
        sha = commit.get('sha') if isinstance(commit, dict) else None
        if not isinstance(sha, str) or not SHA.fullmatch(sha):
            raise DiscoveryError('REVISION', 'Commit resolution did not return an immutable SHA')
        info = dict(info, resolved_sha=sha.lower())
        self.repos[key] = info
        return info

    def tree(self, repo, sha):
        key = (repo, sha)
        if key not in self.trees:
            data = self.json('repos/' + repo + '/git/trees/' + sha + '?recursive=1', max_bytes=8_000_000)
            if not isinstance(data, dict) or not isinstance(data.get('tree'), list):
                raise DiscoveryError('RESPONSE', 'Invalid repository tree')
            if data.get('truncated'):
                self.a.note('TRUNCATED', 'GitHub tree is truncated; inventory is partial')
            self.tree_complete[key] = not bool(data.get('truncated'))
            rows = []
            for item in data['tree']:
                if not isinstance(item, dict) or not isinstance(item.get('path'), str):
                    continue
                try:
                    path = safe_relative(item['path'])
                except DiscoveryError:
                    continue
                if item.get('type') == 'blob' and item.get('mode') != '120000':
                    rows.append(path)
            self.trees[key] = rows
        return self.trees[key]

    def text(self, repo, sha, path):
        path = safe_relative(path)
        try:
            return self.client.get_text('https://raw.githubusercontent.com/' + repo + '/' + sha + '/' + quote(path, safe='/'),
                                        provider=self.a.provider, bucket='metadata')
        except DiscoveryError as error:
            if error.code != 'NETWORK':
                raise
            # Official Contents API fallback for networks that cannot reach raw.
            # The repo was already checked public and sha is immutable.
            data = self.json('repos/' + repo + '/contents/' + quote(path, safe='/') + '?' + urlencode({'ref': sha}))
            if not isinstance(data, dict) or data.get('type') != 'file' or data.get('encoding') != 'base64' or not isinstance(data.get('content'), str):
                raise DiscoveryError('RESPONSE', 'Contents fallback did not return an encoded file')
            try:
                raw = base64.b64decode(''.join(data['content'].split()), validate=True)
                if len(raw) > 1_000_000:
                    raise DiscoveryError('SIZE_LIMIT', 'Contents file exceeds metadata read budget')
                text = raw.decode('utf-8-sig')
            except (ValueError, UnicodeError) as exc:
                raise DiscoveryError('RESPONSE', 'Contents fallback returned invalid file encoding') from exc
            self.a.note('CONTENTS_FALLBACK', 'Raw host unavailable; read the same pinned public file through GitHub Contents API')
            return text

    def skill(self, repo, sha, path, paths=None, plugin=None):
        path = safe_relative(path)
        content = self.text(repo, sha, path)
        prefix = path.rsplit('/', 1)[0] + '/' if '/' in path else ''
        resources = None
        associated = {}
        if paths is not None:
            listed = [p[len(prefix):] for p in paths if p.startswith(prefix) and p != path]
            if len(listed) <= self.a.max_files and self.tree_complete.get((repo, sha), True):
                resources = listed
            else:
                self.a.note('RESOURCE_LIMIT', 'Resource listing incomplete; missing resources cannot be determined')
            yaml = prefix + 'agents/openai.yaml'
            if yaml in paths:
                try:
                    associated['agents/openai.yaml'] = self.text(repo, sha, yaml)
                except DiscoveryError as error:
                    self.a.caught(error)
        source = {'provider': self.a.provider, 'repository': repo, 'path': path, 'revision': sha,
                  'canonical_url': 'https://github.com/' + repo + '/blob/' + sha + '/' + quote(path, safe='/'),
                  'method': 'github-pinned-file'}
        if plugin:
            source['plugin'] = plugin
        row = parse_skill(content, source, resources=resources, associated=associated)
        if plugin:
            requirements = row.setdefault('requirements', {})
            requirements.setdefault('dependencies', []).append('plugin:' + plugin.get('name', 'unknown'))
            for server in plugin.get('mcp_servers', []):
                if server not in requirements.setdefault('mcp_servers', []):
                    requirements['mcp_servers'].append(server)
        return row

    def candidates(self, repo, query, ref=None, exact_path=None, name=None, limit=None):
        info = self.repository(repo, ref)
        sha = info['resolved_sha']
        paths = self.tree(repo, sha)
        if exact_path:
            selected = [exact_path] if (exact_path in paths or not self.tree_complete.get((repo, sha), True)) and exact_path.endswith('SKILL.md') else []
            if not selected:
                self.a.note('PATH_NOT_FOUND', 'Upstream Skill path was not found at its pinned revision')
        else:
            selected = [p for p in paths if p == 'SKILL.md' or p.endswith('/SKILL.md')]
            if name:
                normalized_name = str(name).lower().replace(' ', '-')
                selected = [p for p in selected if p == 'SKILL.md' or p.split('/')[-2:-1] == [normalized_name]]
                if not selected:
                    self.a.note('NAME_NOT_FOUND', 'Registry name has no matching Skill directory; no unrelated Skill was substituted')
            selected = rank_paths(selected, query)
        rows = []
        for path in selected[:limit or self.a.limit]:
            try:
                row = self.skill(repo, sha, path, paths)
                if name and not exact_path and row['name'] != str(name).lower().replace(' ', '-'):
                    self.a.note('NAME_MISMATCH', 'Registry name does not match the inspected Skill frontmatter')
                    continue
                rows.append(row)
            except (DiscoveryError, ValueError, TypeError) as error:
                if self.a.stop_after_error(error, rows):
                    break
        return rows


def rank_paths(paths, query):
    words = [w.lower() for w in query if len(w) > 1]
    return sorted(paths, key=lambda p: (-sum(w in p.lower() for w in words), p))


class OfficialAdapter(Adapter):
    level = 1
    repository_name = ''

    def discover(self, query, context, filters):
        reader = GitHubReader(self)
        info = reader.repository(self.repository_name, self.settings.get('revision'))
        sha = info['resolved_sha']
        paths = reader.tree(self.repository_name, sha)
        selected = [p for p in paths if p.startswith('skills/') and p.endswith('/SKILL.md')]
        rows = []
        for path in rank_paths(selected, query)[:self.limit]:
            try:
                rows.append(reader.skill(self.repository_name, sha, path, paths))
            except (DiscoveryError, ValueError, TypeError) as error:
                if self.stop_after_error(error, rows):
                    break
        if len(selected) > self.limit:
            self.note('CANDIDATE_LIMIT', 'Only a bounded path-ranked subset was inspected; not exhaustive search')
        return rows


class AnthropicAdapter(OfficialAdapter):
    provider, repository_name = 'anthropic', 'anthropics/skills'


class OpenAIAdapter(OfficialAdapter):
    provider, repository_name = 'openai', 'openai/plugins'

    def _plugin(self, reader, sha, root, paths):
        import json
        portable_path = root + '/plugin.json'
        legacy_path = root + '/.codex-plugin/plugin.json'
        portable = portable_path in paths
        manifest_path = portable_path if portable else legacy_path
        manifest = json.loads(reader.text(self.repository_name, sha, manifest_path))
        if not isinstance(manifest, dict):
            raise DiscoveryError('MANIFEST', 'Plugin manifest must be an object')
        overlay = manifest
        if portable:
            extension = manifest.get('extensions', {}).get('com.openai') if isinstance(manifest.get('extensions', {}), dict) else None
            if isinstance(extension, dict):
                overlay = extension
            elif legacy_path in paths:
                overlay = json.loads(reader.text(self.repository_name, sha, legacy_path))
            else:
                overlay = {}
        skill_value = 'skills/' if portable else manifest.get('skills')
        if not isinstance(skill_value, str):
            raise DiscoveryError('MANIFEST', 'Plugin has no declared supported Skill directory')
        skill_root = root + '/' + safe_relative(skill_value).rstrip('/') + '/'
        mcp = 'mcp.json' if portable and root + '/mcp.json' in paths else overlay.get('mcpServers')
        servers = []
        if isinstance(mcp, str):
            mcp_path = root + '/' + safe_relative(mcp)
            if mcp_path in paths:
                config = json.loads(reader.text(self.repository_name, sha, mcp_path))
                if isinstance(config, dict) and isinstance(config.get('mcpServers'), dict):
                    servers = sorted(config['mcpServers'])
        apps = overlay.get('apps')
        return skill_root, {'name': manifest.get('name', root.rsplit('/', 1)[-1]),
                            'version': manifest.get('version'), 'manifest_path': manifest_path,
                            'format': 'portable' if portable else 'codex-compatibility',
                            'mcp_servers': servers, 'registered_apps_manifest': apps,
                            'installation_unit': 'plugin', 'connection_status': 'unknown'}

    def discover(self, query, context, filters):
        reader = GitHubReader(self)
        info = reader.repository(self.repository_name, self.settings.get('revision'))
        sha = info['resolved_sha']
        paths = reader.tree(self.repository_name, sha)
        roots = set()
        for p in paths:
            if p.endswith('/.codex-plugin/plugin.json'):
                roots.add(p[:-len('/.codex-plugin/plugin.json')])
            elif p.endswith('/plugin.json') and '/.claude-plugin/' not in p and '/.codex-plugin/' not in p:
                roots.add(p[:-len('/plugin.json')])
        chosen = rank_paths([p for p in paths if p.endswith('/SKILL.md') and
                             any(p.startswith(root + '/') for root in roots)], query)
        rows, plugins, inspected = [], {}, 0
        for path in chosen:
            if len(rows) >= self.limit or inspected >= self.max_files:
                self.note('CANDIDATE_LIMIT', 'Only a bounded subset of plugin Skills was inspected')
                break
            root = max((r for r in roots if path.startswith(r + '/')), key=len)
            try:
                if root not in plugins:
                    plugins[root] = self._plugin(reader, sha, root, paths)
                skill_root, plugin = plugins[root]
                # Plugin import reads direct Skill directories, not nested support SKILL.md files.
                relative = path[len(skill_root):] if path.startswith(skill_root) else ''
                if len(relative.split('/')) != 2 or not relative.endswith('/SKILL.md'):
                    continue
                inspected += 1
                rows.append(reader.skill(self.repository_name, sha, path, paths, plugin))
            except (DiscoveryError, ValueError, TypeError) as error:
                if self.stop_after_error(error, rows):
                    break
                plugins[root] = ('', {})
        return rows


class RegistryAdapter(Adapter):
    level = 2

    def resolve_items(self, items, query, limit=None):
        reader, rows, seen = GitHubReader(self), [], set()
        limit = self.limit if limit is None else limit
        for item in items[:self.max_files]:
            if len(rows) >= limit:
                break
            if not isinstance(item, dict):
                self.note('RESPONSE', 'Registry returned a malformed candidate')
                continue
            locator = None
            for key in ('githubUrl', 'source', 'installUrl'):
                locator = github_locator(item.get(key))
                if locator:
                    break
            if not locator:
                self.note('UNSUPPORTED_SOURCE', 'Registry lead has no supported GitHub source; not treated as a verified Skill')
                continue
            key = (locator['repository'].lower(), locator['path'], item.get('slug') or item.get('name'))
            if key in seen:
                continue
            seen.add(key)
            try:
                candidates = reader.candidates(locator['repository'], query, locator['ref'], locator['path'],
                                               item.get('slug') or item.get('name'), limit - len(rows))
                for row in candidates:
                    row['registry_observation'] = {'provider': self.provider,
                        'id': item.get('id'), 'name': item.get('name'),
                        'popularity': item.get('installs', item.get('stars')), 'quality_verified': False}
                    rows.append(row)
                if self.budget_stopped():
                    break
            except (DiscoveryError, ValueError, TypeError) as error:
                if self.stop_after_error(error, rows):
                    break
        return rows


class SkillsShAdapter(RegistryAdapter):
    provider = 'skills-sh'

    def check_availability(self):
        base = super().check_availability()
        if base['status'] == 'DISABLED':
            return base
        if not self.client.credential('VERCEL_OIDC_TOKEN'):
            return {'status': 'CREDENTIAL_REQUIRED', 'reason': 'Documented skills.sh API needs VERCEL_OIDC_TOKEN; no CLI is executed'}
        return base

    def discover(self, query, context, filters):
        token = self.client.credential('VERCEL_OIDC_TOKEN')
        if not token:
            self.note('CREDENTIAL_REQUIRED', 'Configure VERCEL_OIDC_TOKEN with credential use enabled, or use skills.sh manually')
            return []
        params = {'q': ' '.join(query)[:200], 'limit': min(self.limit, 200)}
        data = self.client.get_json('https://skills.sh/api/v1/skills/search?' + urlencode(params),
                                   provider=self.provider, headers={'Authorization': 'Bearer ' + token})
        if not isinstance(data, dict) or not isinstance(data.get('data'), list):
            raise DiscoveryError('RESPONSE', 'Invalid skills.sh search envelope')
        return self.resolve_items(data['data'], query)


class SkillsMPAdapter(RegistryAdapter):
    provider = 'skillsmp'

    def check_availability(self):
        base = super().check_availability()
        if base['status'] != 'DISABLED' and not self.client.credential('SKILLSMP_API_KEY'):
            base['reason'] = 'Anonymous keyword search with lower service quota; optional SKILLSMP_API_KEY'
        return base

    def discover(self, query, context, filters):
        token = self.client.credential('SKILLSMP_API_KEY')
        headers = {'Authorization': 'Bearer ' + token} if token else {}
        rows, seen, inspected = [], set(), 0
        for page in range(1, self.pages + 1):
            params = {'q': ' '.join(query)[:200], 'page': page, 'limit': min(50, self.limit), 'sortBy': 'recent'}
            try:
                data = self.client.get_json('https://skillsmp.com/api/v1/skills/search?' + urlencode(params),
                                           provider=self.provider, headers=headers)
            except DiscoveryError as error:
                if not rows:
                    raise
                self.stop_after_error(error, rows)
                break
            if not isinstance(data, dict) or data.get('success') is not True:
                error_code = data.get('error', {}).get('code') if isinstance(data, dict) and isinstance(data.get('error'), dict) else None
                code = 'SEARCH_COMPLETION_UNCERTAIN' if error_code == 'SEARCH_COMPLETION_UNCERTAIN' else 'RESPONSE'
                error = DiscoveryError(code, 'SkillsMP keyword search did not return a successful envelope')
                if not rows:
                    raise error
                self.caught(error)
                break
            payload = data.get('data')
            if not isinstance(payload, dict) or not isinstance(payload.get('skills'), list):
                raise DiscoveryError('RESPONSE', 'Invalid SkillsMP keyword search results')
            inspected += len(payload['skills'])
            try:
                candidates = self.resolve_items(payload['skills'], query, self.limit - len(rows))
                for row in candidates:
                    if row['id'] not in seen:
                        seen.add(row['id'])
                        rows.append(row)
            except DiscoveryError as error:
                if self.stop_after_error(error, rows):
                    break
            pagination = payload.get('pagination', {})
            if (self.budget_stopped() or len(rows) >= self.limit or not isinstance(pagination, dict)
                    or not pagination.get('hasNext') or inspected >= self.max_files):
                break
        return rows


class GitHubSearchAdapter(Adapter):
    provider, level = 'github', 3

    def check_availability(self):
        base = super().check_availability()
        if base['status'] != 'DISABLED' and not self.client.credential('GITHUB_TOKEN'):
            base['reason'] = 'Anonymous public repository search; code search requires GITHUB_TOKEN'
        return base

    def discover(self, query, context, filters):
        reader, rows, seen = GitHubReader(self), [], set()
        code = bool(self.client.credential('GITHUB_TOKEN'))
        mode = 'code' if code else 'repositories'
        if not code:
            self.note('ANONYMOUS_FALLBACK', 'Using public repository search; filename code search requires authentication')
        terms = ' '.join(query)[:200] + (' filename:SKILL.md is:public' if code else ' skill in:readme is:public')
        for page in range(1, self.pages + 1):
            try:
                data = reader.json('search/' + mode + '?' + urlencode({'q': terms, 'per_page': min(100, self.limit), 'page': page}), bucket='search')
            except DiscoveryError as error:
                if not rows:
                    raise
                self.stop_after_error(error, rows)
                break
            if not isinstance(data, dict) or not isinstance(data.get('items'), list):
                raise DiscoveryError('RESPONSE', 'Invalid GitHub search envelope')
            if data.get('incomplete_results'):
                self.note('INCOMPLETE_RESULTS', 'GitHub reports incomplete search results')
            for item in data['items']:
                if not isinstance(item, dict):
                    continue
                repo = item.get('repository', {}).get('full_name') if code and isinstance(item.get('repository'), dict) else item.get('full_name')
                path = item.get('path') if code else None
                key = (repo, path)
                if key in seen:
                    continue
                seen.add(key)
                try:
                    rows.extend(reader.candidates(repo, query, exact_path=path, limit=self.limit - len(rows)))
                except (DiscoveryError, ValueError, TypeError) as error:
                    if self.stop_after_error(error, rows):
                        return rows
                if self.budget_stopped():
                    return rows
                if len(rows) >= self.limit:
                    return rows[:self.limit]
            if len(data['items']) < min(100, self.limit):
                break
        return rows


def build_adapters(config, client, workspace):
    classes = {c.provider: c for c in (LocalAdapter, OpenAIAdapter, AnthropicAdapter,
                                      SkillsShAdapter, SkillsMPAdapter, GitHubSearchAdapter)}
    order = config.get('order', list(PROVIDERS))
    if not isinstance(order, list) or len(order) != len(set(order)) or any(p not in classes for p in order):
        raise DiscoveryError('CONFIG', 'Source order contains unknown or duplicate providers')
    return [classes[name](config, client, workspace) for name in order]
