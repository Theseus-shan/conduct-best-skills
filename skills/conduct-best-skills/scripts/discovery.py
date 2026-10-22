"""Progressive Skill discovery. No installation, loading or script execution."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import sys

from discovery_core import DiscoveryError, validate_candidate, _identity
from discovery_io import Budget, Cache, HttpClient

PROVIDERS = ['local', 'openai', 'anthropic', 'skills-sh', 'skillsmp', 'github']
DEFAULTS = {'allow_external': False, 'allow_credentials': False, 'offline': False,
            'order': PROVIDERS, 'allowed_sources': PROVIDERS, 'max_level': 3,
            'max_candidates': 8, 'max_files': 300, 'max_depth': 4, 'pages': 1,
            'max_requests': 30, 'seconds': 60, 'timeout': 10, 'retries': 1,
            'cache_dir': '.conduct-discovery', 'refresh': [], 'sources': {}, 'stop_when_covered': True}


def string_list(value, label):
    if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value):
        raise DiscoveryError('CONFIG', label + ' must be a list of nonempty strings')
    return list(dict.fromkeys(value))


def keywords(values):
    values = string_list(values, 'keywords')
    if len(values) > 8 or sum(map(len, values)) > 160:
        raise DiscoveryError('PRIVACY', 'Use at most eight short public capability terms')
    for word in values:
        if (len(word) > 48 or len(word.split()) > 5 or not re.fullmatch(r'[\w \-]+', word, re.UNICODE)
                or re.search(r'(?:sk|ghp|github_pat|sk_live)[_-][\w-]{8,}', word, re.I)
                or re.search(r'(?i)\b(?:password|secret|token|api_key)\s+\S{10,}', word)):
            raise DiscoveryError('PRIVACY', 'Keywords must be public capability terms, not prompts, paths, code or credentials')
    return values


def configure(saved=None, overrides=None):
    config = copy.deepcopy(DEFAULTS)
    for incoming in (saved or {}, overrides or {}):
        if not isinstance(incoming, dict) or set(incoming) - set(DEFAULTS):
            raise DiscoveryError('CONFIG', 'Unknown discovery configuration field')
        config.update(copy.deepcopy(incoming))
    for key in ('allow_external', 'allow_credentials', 'offline', 'stop_when_covered'):
        if type(config[key]) is not bool:
            raise DiscoveryError('CONFIG', key + ' must be boolean')
    for key in ('order', 'allowed_sources', 'refresh'):
        config[key] = string_list(config[key], key)
        if set(config[key]) - set(PROVIDERS):
            raise DiscoveryError('CONFIG', 'Unknown source in ' + key)
    for key, low, high in [('max_level', 0, 3), ('max_candidates', 1, 50), ('max_files', 1, 5000),
                           ('max_depth', 0, 8), ('pages', 1, 5)]:
        if type(config[key]) is not int or not low <= config[key] <= high:
            raise DiscoveryError('CONFIG', 'Invalid ' + key)
    Budget(config['max_requests'], config['seconds'], config['timeout'], config['retries'])
    if config['cache_dir'] is not None and not isinstance(config['cache_dir'], str):
        raise DiscoveryError('CONFIG', 'cache_dir must be a project-relative path or null')
    if not isinstance(config['sources'], dict) or set(config['sources']) - set(PROVIDERS):
        raise DiscoveryError('CONFIG', 'Unknown source settings')
    for provider, settings in config['sources'].items():
        if not isinstance(settings, dict) or set(settings) - {'enabled', 'roots', 'revision', 'allowed_symlink_roots'}:
            raise DiscoveryError('CONFIG', 'Unknown adapter setting')
        if 'enabled' in settings and type(settings['enabled']) is not bool:
            raise DiscoveryError('CONFIG', 'enabled must be boolean')
        for key in ('roots', 'allowed_symlink_roots'):
            if key in settings:
                string_list(settings[key], key)
        if 'revision' in settings and (not isinstance(settings['revision'], str) or not re.fullmatch(r'[\w./-]{1,100}', settings['revision'])):
            raise DiscoveryError('CONFIG', 'Invalid source revision')
    return config


def context_checked(context):
    if not isinstance(context, dict) or set(context) - {'native_capabilities', 'tools', 'mcp_servers', 'environment',
                                                      'platform', 'approved_ids', 'denied_permissions', 'dependencies'}:
        raise DiscoveryError('CONFIG', 'Context accepts capability/environment facts only; never full prompts')
    result = copy.deepcopy(context)
    for key in ('native_capabilities', 'tools', 'mcp_servers', 'environment', 'approved_ids', 'denied_permissions', 'dependencies'):
        result[key] = string_list(result.get(key, []), key)
    if 'platform' in result and not isinstance(result['platform'], str):
        raise DiscoveryError('CONFIG', 'platform must be a string')
    return result


def words(text):
    return set(re.findall(r'\w+', text.lower().replace('_', ' '), re.UNICODE))


def matches(need, candidate):
    if need.lower() in {x.lower() for x in candidate['capabilities']}:
        return True
    haystack = words(' '.join([candidate['name'], candidate['description'], *candidate['capabilities'], *candidate['tags']]))
    return bool(words(need)) and words(need) <= haystack


def family(candidate):
    return _identity(dict(candidate['source'], revision=None))


def deduplicate(candidates):
    merged = {}
    for candidate in candidates:
        validate_candidate(candidate)
        row = copy.deepcopy(candidate)
        observation = {'provider': row['source']['provider'], 'canonical_url': row['source']['canonical_url'],
                       'revision': row['source']['revision'], 'discovered_at': row['provenance']['discovered_at']}
        if 'registry_observation' in row:
            observation['registry'] = row['registry_observation']
        row['discovery_records'] = [observation]
        if row['id'] not in merged:
            merged[row['id']] = row
            continue
        existing = merged[row['id']]
        if observation not in existing['discovery_records']:
            existing['discovery_records'].append(observation)
        # Conflicting metadata never silently upgrades trust for the same source identity.
        if any(row[k] != existing[k] for k in ('description', 'name', 'capabilities')):
            existing['security']['risk_flags'].append('conflicting_metadata')
        for group, keys in (('requirements', ('tools', 'mcp_servers', 'dependencies', 'environment')),
                            ('security', ('permissions_required',)), ('compatibility', ('constraints', 'agents'))):
            for key in keys:
                existing[group][key] = sorted(set(existing[group][key] + row[group][key]))
        for key in ('observations', 'inferred'):
            existing[key].extend(x for x in row[key] if x not in existing[key])
        if row['compatibility']['status'] == 'blocked':
            existing['compatibility']['status'] = 'blocked'
        existing['security']['risk_flags'] = sorted(set(existing['security']['risk_flags'] + row['security']['risk_flags']))
        if row['security']['review_status'] == 'blocked':
            existing['security']['review_status'] = 'blocked'
    versions = {}
    for row in merged.values():
        versions.setdefault(family(row), set()).add(row['source']['revision'])
    for row in merged.values():
        row['version_alternatives'] = sorted(str(x) for x in versions[family(row)] if x != row['source']['revision'])
    return list(merged.values())


def assess(candidate, needs, query, context, order):
    row = copy.deepcopy(candidate)
    blocked = []
    security, compatibility = row['security'], row['compatibility']
    if security['review_status'].lower() == 'blocked' or compatibility['status'].lower() == 'blocked':
        blocked.append('static_block')
    if set(security['permissions_required']) & set(context['denied_permissions']):
        blocked.append('permission_denied')
    if 'conflicting_metadata' in security['risk_flags']:
        blocked.append('conflicting_metadata')
    constraints = ' '.join(compatibility['constraints']).lower()
    platform = context.get('platform', '').lower()
    if platform and any(marker in constraints and target != platform for marker, target in
                        [('windows-only', 'windows'), ('linux-only', 'linux'), ('macos-only', 'macos')]):
        blocked.append('platform_mismatch')
    declared_platforms = {p.lower() for p in row['requirements']['environment']} & {'windows', 'linux', 'macos'}
    if platform and declared_platforms and platform not in declared_platforms:
        blocked.append('platform_mismatch')
    missing = []
    for key in ('tools', 'mcp_servers', 'environment', 'dependencies'):
        missing += [key + ':' + v for v in row['requirements'][key] if v not in context[key]]
    covered = [need for need in needs if matches(need, row)]
    relevant = [term for term in query if matches(term, row)]
    stale = any(x.get('code') == 'STALE_CACHE' for x in row['observations'])
    if stale:
        blocked.append('stale_evidence')
    approved = row['id'] in context['approved_ids']
    # Discovery reads metadata, not the full executable/reference bundle. Even a
    # host approval of this metadata ID is not a current runtime preflight.
    available = False
    row['assessment'] = {'covered': covered, 'matched_keywords': relevant, 'excluded': blocked,
                         'missing_requirements': missing, 'available': available,
                         'decision': 'blocked' if blocked else 'available' if available else 'review_required',
                         'approval_scope': 'host-supplied version identity' if approved else None,
                         'host_review_recorded': approved, 'preflight_required': True,
                         'evidence': 'metadata match; does not establish task performance',
                         'unknown_dimensions': ['maintenance_quality', 'task_performance', 'execution_cost']}
    rank = (bool(blocked), -len(covered), len(missing), -len(relevant),
            0 if available else 1, 0 if row['source']['revision'] else 1,
            order.index(row['source']['provider']) if row['source']['provider'] in order else len(order), row['id'])
    row['ranking'] = {'method': 'lexicographic-v1', 'key': list(rank),
                      'factors': ['hard_exclusion', 'coverage_desc', 'missing_requirements', 'keyword_matches_desc',
                                  'host_confirmed_local', 'revision_known', 'configured_source_order', 'stable_id']}
    return row


def dependency_pins(candidate):
    pins = {}
    for value in candidate['requirements']['dependencies'] + candidate['requirements']['environment']:
        match = re.fullmatch(r'([\w.-]+)==([\w.+-]+)', value)
        if match:
            pins[match[1].lower()] = match[2]
    return pins


def compose(candidates, needs, native):
    missing = [need for need in needs if need not in native]
    selection, conflicts, overlap = [], [], []
    pins, selected_families = {}, set()
    remaining = list(candidates)
    while missing and remaining:
        remaining.sort(key=lambda c: (-len(set(c['assessment']['covered']) & set(missing)), c['ranking']['key']))
        row = remaining.pop(0)
        a = row['assessment']
        if a['excluded'] or not set(a['covered']) & set(missing):
            continue
        cp = dependency_pins(row)
        incompatible = sorted(k for k, v in cp.items() if k in pins and pins[k] != v)
        if incompatible or family(row) in selected_families:
            conflicts.append({'candidate': row['id'], 'reason': 'dependency_pins' if incompatible else 'same_skill_version',
                              'dependencies': incompatible})
            continue
        overlap.append({'candidate': row['id'], 'capabilities': [x for x in a['covered'] if x not in missing]})
        selection.append(row['id'])
        selected_families.add(family(row))
        pins.update(cp)
        missing = [x for x in missing if x not in a['covered']]
    ready = set(native)
    for row in candidates:
        if row['id'] in selection and row['assessment']['available']:
            ready.update(row['assessment']['covered'])
    return {'selected': selection, 'native': [n for n in needs if n in native], 'missing': missing,
            'not_ready': [n for n in needs if n not in ready], 'conflicts': conflicts, 'overlap': overlap,
            'method': 'greedy metadata coverage; host review and preflight remain required'}


class DiscoveryEngine:
    def __init__(self, adapters, config, client):
        self.adapters, self.config, self.client = adapters, config, client

    def run(self, query, needs=None, context=None):
        query = keywords(query)
        needs = string_list(needs or [], 'needs')
        if len(needs) > 40 or any(len(x) > 100 for x in needs):
            raise DiscoveryError('CONFIG', 'Capability requirements exceed bounded input limits')
        context = context_checked(context or {})
        collected, statuses, ranked = [], [], []
        composition = compose([], needs, context['native_capabilities'])
        stop = 'sources_exhausted'
        if needs and not composition['missing'] and self.config['stop_when_covered']:
            stop = 'native_coverage'
        else:
            for adapter in self.adapters:
                provider = adapter.provider
                if (provider not in self.config['allowed_sources'] or adapter.level > self.config['max_level'] or
                        not self.config['sources'].get(provider, {}).get('enabled', True) or
                        (adapter.external and not self.config['allow_external'])):
                    statuses.append({'provider': provider, 'status': 'DISABLED', 'reason': 'source_policy'})
                    continue
                before = len(self.client.events)
                try:
                    self.client.budget.check()
                    availability = adapter.check_availability()
                    if availability.get('status', '').upper() in {'UNAVAILABLE', 'AUTH_REQUIRED', 'DISABLED', 'CREDENTIAL_REQUIRED'}:
                        statuses.append({'provider': provider, **availability})
                        continue
                    found = adapter.discover(query, context, {'needs': needs, 'limit': self.config['max_candidates']})
                    if not isinstance(found, list):
                        raise DiscoveryError('SCHEMA', 'Adapter did not return candidate records')
                    events = self.client.events[before:]
                    stale = any(x.get('cache') == 'STALE_FALLBACK' for x in events)
                    accepted, invalid = 0, 0
                    valid = []
                    for row in found[:self.config['max_files']]:
                        try:
                            validate_candidate(row)
                            if stale:
                                row['observations'].append({'code': 'STALE_CACHE', 'message': 'Source used cached fallback; refresh before use'})
                            valid.append(row)
                        except (DiscoveryError, ValueError, TypeError, KeyError):
                            invalid += 1
                    valid.sort(key=lambda c: assess(c, needs, query, context, self.config['order'])['ranking']['key'])
                    collected.extend(valid[:self.config['max_candidates']])
                    accepted = min(len(valid), self.config['max_candidates'])
                    statuses.append({'provider': provider, 'status': 'DEGRADED' if stale or invalid or adapter.diagnostics else 'OK',
                                     'candidates': accepted, 'invalid_candidates': invalid, 'diagnostics': adapter.diagnostics})
                except DiscoveryError as exc:
                    statuses.append({'provider': provider, 'status': exc.code, 'reason': str(exc)})
                    if exc.code == 'BUDGET':
                        stop = 'budget_exhausted'
                        break
                except (OSError, ValueError, KeyError, TypeError):
                    statuses.append({'provider': provider, 'status': 'ADAPTER_ERROR', 'reason': 'Source data unavailable or malformed'})
                ranked = sorted([assess(c, needs, query, context, self.config['order']) for c in deduplicate(collected)],
                                key=lambda c: c['ranking']['key'])
                composition = compose(ranked, needs, context['native_capabilities'])
                chosen = [c for c in ranked if c['id'] in composition['selected']]
                # A metadata-only plan can stop discovery, but it never authorizes use.
                sufficient = bool(needs) and not composition['missing'] and all(
                    not c['assessment']['missing_requirements'] and not c['security']['risk_flags'] for c in chosen)
                if not needs:
                    sufficient = any(c['assessment']['matched_keywords'] and not c['assessment']['excluded'] and
                                     not c['assessment']['missing_requirements'] and not c['security']['risk_flags'] for c in ranked)
                if sufficient and self.config['stop_when_covered']:
                    stop = 'planning_coverage'
                    break
        seen_sources = {s['provider'] for s in statuses}
        statuses.extend({'provider': a.provider, 'status': 'NOT_EXECUTED', 'reason': stop}
                        for a in self.adapters if a.provider not in seen_sources)
        return {'schema_version': 1, 'keywords': query, 'needs': needs, 'candidates': ranked,
                'composition': composition, 'sources': statuses, 'stop_reason': stop,
                'requests_used': self.client.budget.used, 'cache_events': self.client.events,
                'boundary': 'Discovery only. Recommendations do not install, approve, load or execute Skills.',
                'catalog': {'allowed_effects': ['READ_ONLY'], 'capabilities': [
                    {'id': c['id'], 'provides': c['assessment']['covered'], 'available': c['assessment']['available'],
                     'constraints_met': not c['assessment']['excluded'] and not c['assessment']['missing_requirements'],
                     'effect': 'READ_ONLY' if not c['security']['permissions_required'] else 'REVIEW_REQUIRED',
                     'observation': 'Discovery metadata only; host must perform and record current runtime preflight',
                     'preference': 0} for c in ranked]}}


def add_arguments(parser):
    parser.add_argument('--config', help='Trusted saved JSON source policy; CLI overrides it')
    parser.add_argument('--context', help='Trusted JSON environment facts; not a full prompt')
    parser.add_argument('--keyword', action='append', default=[], help='Short public capability term, repeatable')
    parser.add_argument('--need', action='append', default=[], help='Required capability, repeatable')
    parser.add_argument('--root', action='append', help='Explicit local Skill root, repeatable')
    parser.add_argument('--allow-external', action='store_true', default=None)
    parser.add_argument('--local-only', action='store_true')
    parser.add_argument('--allow-credentials', action='store_true', default=None)
    parser.add_argument('--offline', action='store_true', default=None)
    parser.add_argument('--source', action='append', choices=PROVIDERS, help='Source whitelist, repeatable')
    parser.add_argument('--refresh', action='append', choices=PROVIDERS)
    parser.add_argument('--max-requests', type=int)
    parser.add_argument('--seconds', type=float)
    parser.add_argument('--no-cache', action='store_true')
    parser.add_argument('--all-sources', action='store_true', help='Inspect every enabled source within the same budget')
    parser.add_argument('--output', help='Optional project-relative JSON report')


def execute(args):
    from conduct import atomic_json, local_path
    from discovery_sources import build_adapters
    workspace = Path(args.workspace).resolve()
    if not workspace.is_dir():
        raise DiscoveryError('CONFIG', 'Workspace must exist')
    saved = json.loads(Path(args.config).read_text(encoding='utf-8-sig')) if args.config else {}
    context = json.loads(Path(args.context).read_text(encoding='utf-8-sig')) if args.context else {}
    overrides = {k: getattr(args, k) for k in ('allow_external', 'allow_credentials', 'offline', 'max_requests', 'seconds')
                 if getattr(args, k) is not None}
    if args.local_only:
        overrides['allow_external'] = False
    if args.source:
        overrides['allowed_sources'] = args.source
    if args.refresh:
        overrides['refresh'] = args.refresh
    if args.no_cache:
        overrides['cache_dir'] = None
    if args.all_sources:
        overrides['stop_when_covered'] = False
    config = configure(saved, overrides)
    if args.root:
        config['sources'].setdefault('local', {})['roots'] = args.root
    query = keywords(args.keyword)
    context = context_checked(context)
    client = HttpClient(Budget(config['max_requests'], config['seconds'], config['timeout'], config['retries']),
                        Cache(workspace, config['cache_dir']), config['offline'], config['refresh'], config['allow_credentials'])
    result = DiscoveryEngine(build_adapters(config, client, workspace), config, client).run(query, args.need, context)
    if args.output:
        path = local_path(workspace, args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_json(local_path(workspace, args.output), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    # Successful discovery may legitimately find gaps. Report them in structured data.
    return 0


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', default='.')
    add_arguments(parser)
    try:
        return execute(parser.parse_args(argv))
    except (DiscoveryError, OSError, ValueError, KeyError, TypeError) as exc:
        code = exc.code if isinstance(exc, DiscoveryError) else 'CONFIG'
        message = str(exc) if isinstance(exc, DiscoveryError) else 'Invalid or inaccessible discovery configuration'
        print(json.dumps({'error': code, 'message': message}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
