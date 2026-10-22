"""Bounded metadata parsing and conservative static triage for Skill discovery.

No discovered text is executed. This parser deliberately supports a documented
YAML subset, not arbitrary YAML: maps, lists, scalar values and block strings.
Unsupported constructs fail explicitly instead of silently changing meaning.
"""
from __future__ import annotations

import hashlib
import json
import math
import ntpath
import posixpath
import re
from datetime import datetime, timezone
from urllib.parse import unquote, urlsplit


MAX_TEXT = 2 * 1024 * 1024
MAX_FRONTMATTER = 64 * 1024
MAX_DEPTH = 16


class DiscoveryError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _fail(message: str, code: str = "PARSE_ERROR"):
    raise DiscoveryError(code, message)


def _comment(value: str) -> str:
    quote = None
    i = 0
    while i < len(value):
        char = value[i]
        if quote == '"' and char == "\\":
            i += 2
            continue
        if quote == "'" and char == "'" and i + 1 < len(value) and value[i + 1] == "'":
            i += 2
            continue
        if char == quote:
            quote = None
        elif quote is None and char in "\"'":
            quote = char
        elif quote is None and char == "#" and (i == 0 or value[i - 1].isspace()):
            return value[:i].rstrip()
        i += 1
    return value.rstrip()


def _scalar(value: str, depth: int = 0):
    if depth > MAX_DEPTH:
        _fail("Metadata nesting exceeds the supported limit")
    value = _comment(value).strip()
    if not value:
        return None
    if value.startswith(('!', '&', '*', '{', '}', '%', '?')):
        _fail("YAML tags, anchors, aliases, flow maps and complex keys are unsupported")
    if value.startswith('"'):
        try:
            result = json.loads(value)
        except (ValueError, TypeError):
            _fail("Unsupported or malformed double-quoted scalar")
        if not isinstance(result, str):
            _fail("Expected a quoted string")
        return result
    if value.startswith("'"):
        if len(value) < 2 or not value.endswith("'") or re.search(r"(?<!')'(?!')", value[1:-1]):
            _fail("Malformed single-quoted scalar")
        return value[1:-1].replace("''", "'")
    if value.startswith('['):
        if not value.endswith(']'):
            _fail("Unclosed inline list")
        inner = value[1:-1].strip()
        if not inner:
            return []
        parts, start, nesting, quote = [], 0, 0, None
        i = 0
        while i < len(inner):
            char = inner[i]
            if quote == '"' and char == "\\":
                i += 2
                continue
            if quote == "'" and char == "'" and i + 1 < len(inner) and inner[i + 1] == "'":
                i += 2
                continue
            if char == quote:
                quote = None
            elif quote is None:
                if char in "\"'":
                    quote = char
                elif char == '[':
                    nesting += 1
                elif char == ']':
                    nesting -= 1
                elif char == ',' and nesting == 0:
                    parts.append(inner[start:i].strip())
                    start = i + 1
            i += 1
        if quote or nesting:
            _fail("Malformed inline list")
        parts.append(inner[start:].strip())
        if not all(parts):
            _fail("Empty or trailing inline list item is unsupported")
        return [_scalar(part, depth + 1) for part in parts]
    if re.search(r":\s", value) or value.startswith(('|', '>')) or value in ('---', '...'):
        _fail("Complex or multiline plain scalars require a quoted or block string")
    if value.lower() in ('null', '~'):
        return None
    if value.lower() in ('true', 'false'):
        return value.lower() == 'true'
    if re.fullmatch(r"-?(?:0|[1-9][0-9]*)", value):
        try:
            return int(value)
        except ValueError:
            _fail('Integer scalar exceeds supported bounds')
    if re.fullmatch(r"-?(?:[0-9]+\.[0-9]+)(?:[eE][+-]?[0-9]+)?", value):
        result = float(value)
        if not math.isfinite(result):
            _fail("Non-finite numbers are unsupported")
        return result
    return value


def _yaml_subset(text: str, _depth: int = 0) -> dict:
    lines = text.splitlines()
    if len(lines) > 4096:
        _fail("Too many frontmatter lines")
    for line in lines:
        if '\t' in line[:len(line) - len(line.lstrip())]:
            _fail("Tabs in YAML indentation are unsupported")

    def significant(index):
        while index < len(lines) and (not lines[index].strip() or lines[index].lstrip().startswith('#')):
            index += 1
        return index

    def indent(index):
        return len(lines[index]) - len(lines[index].lstrip(' '))

    def block_string(index, parent_indent, marker):
        start = index
        while index < len(lines) and (not lines[index].strip() or indent(index) > parent_indent):
            index += 1
        block = lines[start:index]
        nonblank = [len(line) - len(line.lstrip(' ')) for line in block if line.strip()]
        margin = min(nonblank) if nonblank else parent_indent + 1
        content = [line[margin:] if line.strip() else '' for line in block]
        if marker[0] == '|':
            result = '\n'.join(content)
        else:
            result = ''
            for offset, line in enumerate(content):
                result += line
                if offset + 1 < len(content):
                    following = content[offset + 1]
                    # Fold ordinary lines; preserve paragraph and indented breaks.
                    if line and following and not line.startswith(' ') and not following.startswith(' '):
                        result += ' '
                    elif not line and following and offset > 0 and not following.startswith(' '):
                        pass
                    else:
                        result += '\n'
        if marker.endswith('-'):
            return result.rstrip('\n'), index
        if marker.endswith('+'):
            return result + ('\n' if content else ''), index
        return result.rstrip('\n') + ('\n' if content else ''), index

    def node(index, level, depth):
        if depth > MAX_DEPTH:
            _fail("Metadata nesting exceeds the supported limit")
        index = significant(index)
        is_list = lines[index].lstrip().startswith('- ' ) or lines[index].strip() == '-'
        result = [] if is_list else {}
        while index < len(lines):
            index = significant(index)
            if index >= len(lines) or indent(index) < level:
                break
            if indent(index) != level:
                _fail("Unexpected indentation or multiline plain scalar")
            item = lines[index][level:]
            item_is_list = item.startswith('- ') or item == '-'
            if item_is_list != is_list:
                _fail("Mixed mapping and list at one indentation level")
            if is_list:
                raw_value = _comment(item[1:]).strip()
                key = None
            else:
                match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_.-]*):(?:\s+(.*))?", item)
                if not match:
                    _fail("Unsupported mapping syntax or key")
                key, raw_value = match.group(1), _comment(match.group(2) or '').strip()
                if key in result:
                    _fail("Duplicate metadata key: " + key)
            index += 1
            if is_list and re.match(r"[A-Za-z_][A-Za-z0-9_.-]*:(?:\s|$)", raw_value):
                end = index
                while end < len(lines) and (not lines[end].strip() or indent(end) > level):
                    end += 1
                fragment = raw_value + '\n' + '\n'.join(line[level + 2:] for line in lines[index:end])
                value = _yaml_subset(fragment, depth + 1)
                index = end
            elif re.fullmatch(r"[|>][+-]?", raw_value):
                value, index = block_string(index, level, raw_value)
            elif raw_value:
                value = _scalar(raw_value, depth)
            else:
                following = significant(index)
                if following < len(lines) and indent(following) > level:
                    value, index = node(following, indent(following), depth + 1)
                else:
                    value = None
            if is_list:
                result.append(value)
            else:
                result[key] = value
        return result, index

    first = significant(0)
    if first >= len(lines):
        _fail("Empty frontmatter")
    if indent(first):
        _fail("Frontmatter must start with a top-level mapping")
    result, end = node(first, 0, _depth)
    if significant(end) != len(lines) or not isinstance(result, dict):
        _fail("Frontmatter must be a mapping")
    return result


def _strings(value, field: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        _fail(field + " must contain strings")
    return list(dict.fromkeys(value))


def _name_valid(value):
    return (isinstance(value, str) and 1 <= len(value) <= 64 and not value.startswith('-')
            and not value.endswith('-') and '--' not in value
            and all(char == '-' or char.isdigit() or (char.isalpha() and char == char.lower()) for char in value))


def _identity(source: dict) -> str:
    repository = source['repository']
    if repository:
        repository = repository.rstrip('/')
        if repository.endswith('.git'):
            repository = repository[:-4]
        # GitHub repository names are case-insensitive; file paths are not.
        repository = re.sub(r"^https?://github\.com/", '', repository, flags=re.I)
        if re.fullmatch(r"[^/]+/[^/]+", repository):
            repository = repository.lower()
        identity = [repository, posixpath.normpath(source['path'].replace('\\', '/')), source['revision']]
    else:
        canonical = source['canonical_url']
        if re.match(r"^[A-Za-z]:[/\\]", canonical):
            canonical = ntpath.normcase(ntpath.normpath(canonical))
        elif canonical.startswith('file:'):
            parts = urlsplit(canonical)
            canonical = ('//' + parts.netloc if parts.netloc else '') + unquote(parts.path)
            if re.match(r"^/[A-Za-z]:/", canonical):
                canonical = ntpath.normcase(ntpath.normpath(canonical[1:]))
        identity = [canonical, source['revision']]
    return 'skill:' + hashlib.sha256(json.dumps(identity, ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest()


def _check_source(source):
    if not isinstance(source, dict):
        _fail("source must be an object", 'SCHEMA_ERROR')
    for key in ('provider', 'path', 'canonical_url'):
        if not isinstance(source.get(key), str) or not source[key].strip():
            _fail("source." + key + " must be a nonempty string", 'SCHEMA_ERROR')
    for key in ('repository', 'revision'):
        if key not in source or (source[key] is not None and (not isinstance(source[key], str) or not source[key].strip())):
            _fail("source." + key + " must be a nonempty string or null", 'SCHEMA_ERROR')
    if 'plugin' in source and source['plugin'] is not None and not isinstance(source['plugin'], (str, dict)):
        _fail("source.plugin must be an object, string or null", 'SCHEMA_ERROR')


def parse_skill(text: str, source: dict, resources=None, associated=None) -> dict:
    """Parse one SKILL.md and return metadata plus untrusted static observations.

    ``resources`` is a bounded manifest of paths relative to this Skill's root.
    None means not checked; [] means the caller checked and found no resources.
    ``associated`` optionally maps relative resource paths to inspected text.
    """
    _check_source(source)
    if not isinstance(text, str) or len(text.encode('utf-8')) > MAX_TEXT or '\x00' in text:
        _fail("Skill text must be bounded UTF-8 text without NUL")
    lines = text.lstrip('\ufeff').splitlines(keepends=True)
    if not lines or lines[0].strip() != '---':
        _fail("SKILL.md requires opening YAML frontmatter")
    closing = next((index for index in range(1, len(lines)) if re.fullmatch(r'---[ \t]*', lines[index].rstrip('\r\n'))), None)
    if closing is None:
        _fail("Unclosed YAML frontmatter")
    header = ''.join(lines[1:closing])
    if len(header.encode('utf-8')) > MAX_FRONTMATTER:
        _fail("Frontmatter exceeds 64 KiB")
    raw = _yaml_subset(header)
    name, description = raw.get('name'), raw.get('description')
    if not _name_valid(name):
        _fail("name must be 1–64 lowercase letters/digits with single internal hyphens")
    if not isinstance(description, str) or not description.strip() or len(description) > 1024:
        _fail("description must be a nonempty string of at most 1024 characters")
    metadata = raw.get('metadata')
    metadata = {} if metadata is None else metadata
    if not isinstance(metadata, dict):
        _fail("metadata must be a mapping")
    if resources is not None and (not isinstance(resources, list) or len(resources) > 10000 or not all(isinstance(item, str) for item in resources)):
        _fail("resources must be a bounded list of relative paths")
    if associated is not None and (not isinstance(associated, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in associated.items())):
        _fail("associated must map resource paths to text")
    associated = associated or {}
    if len(associated) > 1000 or sum(len(value.encode('utf-8')) for value in associated.values()) > MAX_TEXT:
        _fail("Associated resource text exceeds inspection bounds")
    normalized_resources = []
    for path in resources or []:
        normalized = posixpath.normpath(path.replace('\\', '/'))
        if normalized.startswith(('../', '/')) or normalized == '..' or re.match(r'^[A-Za-z]:', normalized):
            _fail("Resource manifest paths must remain inside the Skill directory")
        normalized_resources.append(normalized)

    stamp = now()
    result = {
        'id': _identity(source), 'name': name, 'description': description.strip(),
        'source': dict(source),
        'capabilities': _strings(metadata.get('capabilities', raw.get('capabilities')), 'capabilities'),
        'tags': _strings(metadata.get('tags', raw.get('tags')), 'tags'),
        'compatibility': {'specification': 'agentskills.io', 'agents': _strings(metadata.get('agents'), 'agents'), 'status': 'unknown', 'constraints': []},
        'requirements': {'tools': [], 'mcp_servers': [], 'dependencies': [], 'environment': []},
        'security': {'trust_level': 'unverified', 'review_status': 'review_required', 'risk_flags': [], 'permissions_required': []},
        'provenance': {'discovered_at': stamp, 'verified_at': None, 'source_method': source['provider']},
        'license': {'identifier': None, 'status': 'unknown'},
        'raw': raw, 'inferred': [], 'resources': list(dict.fromkeys(normalized_resources)), 'observations': [],
    }

    def observe(code, message):
        result['observations'].append({'code': code, 'message': message})

    def infer(field, value, evidence):
        result['inferred'].append({'field': field, 'value': value, 'evidence': evidence})

    observe('STATIC_ONLY', 'Static metadata inspection is not a security certification or execution approval.')
    observe('DEPENDENCIES_UNVERIFIED', 'Declared or inferred requirements have not been checked against installed tools or the current environment.')
    if source['revision'] is None:
        observe('UNPINNED_SOURCE', 'No immutable revision is recorded; source contents may change.')
    elif not re.fullmatch(r'[a-fA-F0-9]{40}|[a-fA-F0-9]{64}', source['revision']):
        observe('MUTABLE_REVISION', 'Revision is a named reference, not an identified commit digest.')
    if resources is None:
        observe('RESOURCES_UNCHECKED', 'Resource availability was not inspected.')
    if not associated:
        observe('ASSOCIATED_CONTENT_UNCHECKED', 'Only SKILL.md text was inspected; associated script contents are not certified.')
    executable_resources = [p for p in normalized_resources if p.lower().endswith(('.py', '.sh', '.ps1', '.js', '.ts', '.bat', '.cmd'))]
    if executable_resources:
        result['security']['risk_flags'].append('unreviewed_executable_resources')
        result['security']['permissions_required'].append('execute_commands')
        observe('EXECUTABLE_RESOURCES_UNREVIEWED', 'Executable resource paths were found; their contents and effects need host review before use.')
    compatibility = raw.get('compatibility')
    if compatibility is not None:
        if not isinstance(compatibility, str) or len(compatibility) > 500:
            _fail('compatibility must be a string of at most 500 characters')
        result['compatibility']['constraints'].append(compatibility)
        result['compatibility']['status'] = 'conditional'
    license_value = raw.get('license', metadata.get('license'))
    if license_value is not None:
        if not isinstance(license_value, str) or not license_value.strip():
            _fail('license must be a nonempty string')
        result['license'] = {'identifier': license_value, 'status': 'declared'}
    else:
        observe('LICENSE_UNKNOWN', 'No license declaration was found; repository license inheritance was not verified.')
    requirements = metadata.get('requirements', raw.get('requirements'))
    requirements = {} if requirements is None else requirements
    if not isinstance(requirements, dict):
        _fail('requirements must be a mapping')
    for key in result['requirements']:
        result['requirements'][key] = _strings(requirements.get(key, metadata.get(key)), 'requirements.' + key)
    allowed_tools = raw.get('allowed-tools')
    if allowed_tools is not None:
        if isinstance(allowed_tools, str):
            result['requirements']['tools'].extend(allowed_tools.split())
        else:
            result['requirements']['tools'].extend(_strings(allowed_tools, 'allowed-tools'))

    # OpenAI's agent configuration declares MCP dependencies separately from
    # SKILL.md. Read only its known data shape; it cannot grant authorization.
    for filename, content in associated.items():
        if filename.replace('\\', '/') != 'agents/openai.yaml':
            continue
        try:
            agent_metadata = _yaml_subset(content)
            result.setdefault('raw_associated', {})[filename] = agent_metadata
            dependencies = agent_metadata.get('dependencies', {})
            if not isinstance(dependencies, dict):
                _fail('Agent dependencies must be a mapping')
            tools = dependencies.get('tools', [])
            if not isinstance(tools, list):
                _fail('Agent dependencies.tools must be a list')
            for dependency in tools:
                if not isinstance(dependency, dict) or not isinstance(dependency.get('type'), str) or not isinstance(dependency.get('value'), str) or not dependency['value'].strip():
                    _fail('Agent tool dependencies require string type and value')
                key = 'mcp_servers' if dependency['type'] == 'mcp' else 'tools'
                result['requirements'][key].append(dependency['value'])
                infer('requirements.' + key, dependency['value'], {'path': filename, 'method': 'declared_agent_dependency'})
        except DiscoveryError:
            observe('ASSOCIATED_PARSE_ERROR', 'Agent configuration uses malformed or unsupported metadata; review ' + filename)
            result['compatibility']['status'] = 'conditional'
            result['compatibility']['constraints'].append('Agent configuration dependencies need manual verification.')

    inspected = [('SKILL.md', text)] + list(associated.items())
    # These are triage indicators, not proof of malicious intent. Evidence records
    # locations only, avoiding accidental disclosure of matched credential values.
    checks = [
        ('prompt_injection', r'ignore\s+(?:(?:all|any|the|your)\s+)?(?:previous|prior|system|developer)\s+(?:instructions|prompts)|忽略.{0,8}(?:系统|之前|先前).{0,8}指令|(?:bypass|disable)\s+(?:all\s+)?(?:approval|security|safety)\s+(?:checks|polic(?:y|ies)|controls)', True, None),
        ('credential_exfiltration', r'(?:send|upload|exfiltrate|transmit).{0,70}(?:api[_ -]?keys?|credentials|secrets?|passwords?)', True, 'credentials'),
        ('remote_code_execution', r'(?:curl|wget)\b[^\r\n]{0,500}\|\s*(?:ba)?sh\b|(?:iwr|invoke-webrequest)\b[^\r\n]{0,500}\|\s*(?:iex|invoke-expression)\b', True, 'execute_commands'),
        ('destructive_command', r'\brm\s+-[a-z]*r[a-z]*f[a-z]*\s+/(?:\s|$)|\bformat\s+[a-z]:|Remove-Item\s+[^\r\n]{0,150}-Recurse[^\r\n]{0,150}["\']?[A-Z]:[\\/]["\']?(?:\s|$)', True, 'filesystem_write'),
        ('command_execution', r'\b(?:subprocess\.(?:run|Popen|call)|os\.system|eval\s*\(|exec\s*\(|shell=True|bash\s+-c|powershell\s+-command)|```(?:bash|sh|powershell|shell)\b', False, 'execute_commands'),
        ('network_access', r'\b(?:curl|wget|requests\.(?:get|post)|urllib\.request|fetch\s*\(|httpx\.)|(?:download|fetch|upload|request)\s+(?:from\s+|to\s+)?https?://', False, 'network'),
        ('credentials_access', r'\b(?:API[_ -]?KEY|ACCESS[_ -]?TOKEN|SECRET[_ -]?KEY|PASSWORD|os\.environ|process\.env)\b|\.aws/credentials|\.ssh/id_', False, 'credentials'),
        ('filesystem_write', r'\b(?:write_text|write_bytes|mkdir|Remove-Item|Set-Content|shutil\.(?:copy|move|rmtree))\b|open\([^\r\n]{0,150},\s*["\'][wax]|\b(?:write|save|create|delete|overwrite)\s+(?:a\s+|the\s+)?(?:file|files|directory|output)\b', False, 'filesystem_write'),
        ('filesystem_read', r'\b(?:read_text|read_bytes|Get-Content)\b|open\([^\r\n]{0,150},\s*["\']r|\b(?:read|inspect)\s+(?:a\s+|the\s+)?(?:file|files|directory)\b', False, 'filesystem_read'),
        ('external_dependencies', r'\b(?:pip3?\s+install|npm\s+(?:install|i)\b|npx\s|uv\s+(?:pip\s+install|add|tool)|apt(?:-get)?\s+install|brew\s+install)', False, 'install_dependencies'),
    ]
    for filename, content in inspected:
        for flag, pattern, blocked, permission in checks:
            match = re.search(pattern, content, re.I)
            if match:
                if flag not in result['security']['risk_flags']:
                    result['security']['risk_flags'].append(flag)
                if permission and permission not in result['security']['permissions_required']:
                    result['security']['permissions_required'].append(permission)
                infer('security.risk_flags', flag, {'path': filename, 'line': content.count('\n', 0, match.start()) + 1, 'method': 'static_pattern'})
                if blocked:
                    result['security']['review_status'] = 'blocked'
        for server in re.findall(r'\bmcp__([A-Za-z0-9_-]+)__[A-Za-z0-9_-]+', content):
            result['requirements']['mcp_servers'].append(server)
            infer('requirements.mcp_servers', server, {'path': filename, 'method': 'tool_reference'})
        if re.search(r'\bClaude Code\b|~[/\\]\.claude|\b(?:computer|bash|text_editor)_20[0-9]+\b|\b(?:Bash|Read|Write|Edit|WebFetch|Task) tool\b', content, re.I):
            result['compatibility']['constraints'].append('Claude-specific tool or environment reference requires an explicit Codex mapping.')
            result['compatibility']['status'] = 'conditional'
            infer('compatibility.constraints', 'claude_specific_reference', {'path': filename, 'method': 'static_pattern'})
        for platform in ('Windows', 'Linux', 'macOS'):
            if re.search(r'\b' + platform + r'[- ]only\b|\brequires?\s+' + platform + r'\b', content, re.I):
                result['requirements']['environment'].append(platform)
                result['compatibility']['constraints'].append(platform + ' requirement needs environment verification.')
                result['compatibility']['status'] = 'conditional'
                infer('requirements.environment', platform, {'path': filename, 'method': 'static_pattern'})
    if any(re.match(r'^(?:Bash|Read|Write|Edit|Glob|Grep|WebFetch|WebSearch|Task|AskUserQuestion)(?:\(|$)', tool) for tool in result['requirements']['tools']):
        result['compatibility']['constraints'].append('Declared agent tool names require mapping to available Codex tools.')
        result['compatibility']['status'] = 'conditional'
    for tool in result['requirements']['tools']:
        name = tool.split('(', 1)[0]
        permission = {'Bash': 'execute_commands', 'Write': 'filesystem_write', 'Edit': 'filesystem_write',
                      'Read': 'filesystem_read', 'Glob': 'filesystem_read', 'Grep': 'filesystem_read',
                      'WebFetch': 'network', 'WebSearch': 'network', 'Task': 'spawn_subagents'}.get(name)
        if permission:
            result['security']['permissions_required'].append(permission)
            infer('security.permissions_required', permission, {'path': 'SKILL.md', 'method': 'declared_tool'})

    references = re.findall(r'\[[^\]]*\]\(([^\s)]+)(?:\s+[^)]*)?\)', text)
    references += re.findall(r'`((?:scripts|references|assets|templates)/[^`\s]+)`', text)
    for ref in dict.fromkeys(references):
        ref = unquote(ref.split('#', 1)[0].split('?', 1)[0].strip('<>')).replace('\\', '/')
        if not ref or (urlsplit(ref).scheme and not re.match(r'^[A-Za-z]:/', ref)) or ref.startswith('//') or any(token in ref for token in ('*', '{', '$')):
            continue
        normalized = posixpath.normpath(ref)
        if normalized.startswith(('../', '/')) or normalized == '..' or re.match(r'^[A-Za-z]:/', normalized):
            result['security']['risk_flags'].append('resource_path_escape')
            result['security']['review_status'] = 'blocked'
            observe('RESOURCE_PATH_ESCAPE', 'Referenced resource escapes the Skill root: ' + ref)
        elif resources is not None and normalized not in normalized_resources and not any(path.startswith(normalized.rstrip('/') + '/') for path in normalized_resources):
            result['compatibility']['status'] = 'blocked'
            result['compatibility']['constraints'].append('Missing referenced resource: ' + ref)
            observe('MISSING_RESOURCE', ref)
    for collection in (result['requirements'],):
        for key, values in collection.items():
            collection[key] = list(dict.fromkeys(values))
    for key in ('risk_flags', 'permissions_required'):
        result['security'][key] = list(dict.fromkeys(result['security'][key]))
    result['compatibility']['constraints'] = list(dict.fromkeys(result['compatibility']['constraints']))
    if any(result['requirements'].values()) and result['compatibility']['status'] == 'unknown':
        result['compatibility']['status'] = 'conditional'
    validate_candidate(result)
    return result


def validate_candidate(candidate: dict) -> None:
    """Validate cached/adapter candidates, including nested JSON field types.

    Validation is structural, never authorization. Unknown extra JSON fields are
    retained for future adapters; security and compatibility enums fail closed.
    """
    def error(message):
        _fail(message, 'SCHEMA_ERROR')

    def object_at(parent, key):
        value = parent.get(key)
        if not isinstance(value, dict):
            error(key + ' must be an object')
        return value

    def string_at(parent, key, nullable=False):
        value = parent.get(key)
        if key not in parent or (value is None and not nullable) or (value is not None and (not isinstance(value, str) or not value.strip())):
            error(key + ' must be a nonempty string' + (' or null' if nullable else ''))
        return value

    def strings_at(parent, key):
        value = parent.get(key)
        if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
            error(key + ' must be an array of nonempty strings')

    def enum_at(parent, key, choices):
        if parent.get(key) not in choices:
            error(key + ' has an unknown value')

    if not isinstance(candidate, dict):
        error('Candidate must be an object')
    for key in ('id', 'name', 'description'):
        string_at(candidate, key)
    if not _name_valid(candidate['name']) or len(candidate['description']) > 1024:
        error('Invalid name or description')
    source = object_at(candidate, 'source')
    _check_source(source)
    if candidate['id'] != _identity(source):
        error('Candidate identity does not match its source')
    for key in ('capabilities', 'tags', 'resources'):
        strings_at(candidate, key)
    compatibility = object_at(candidate, 'compatibility')
    string_at(compatibility, 'specification', nullable=True)
    for key in ('agents', 'constraints'):
        strings_at(compatibility, key)
    enum_at(compatibility, 'status', ('unknown', 'conditional', 'blocked', 'compatible'))
    requirements = object_at(candidate, 'requirements')
    for key in ('tools', 'mcp_servers', 'dependencies', 'environment'):
        strings_at(requirements, key)
    security = object_at(candidate, 'security')
    string_at(security, 'trust_level')
    enum_at(security, 'review_status', ('review_required', 'blocked'))
    for key in ('risk_flags', 'permissions_required'):
        strings_at(security, key)
    provenance = object_at(candidate, 'provenance')
    string_at(provenance, 'source_method')
    for key in ('discovered_at', 'verified_at'):
        value = string_at(provenance, key, nullable=(key == 'verified_at'))
        if value is not None:
            try:
                parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
                if parsed.tzinfo is None:
                    error(key + ' requires an explicit timezone')
            except ValueError:
                error(key + ' must be an ISO timestamp')
    license_info = object_at(candidate, 'license')
    string_at(license_info, 'identifier', nullable=True)
    enum_at(license_info, 'status', ('unknown', 'declared', 'verified'))
    object_at(candidate, 'raw')
    for key, fields in (('inferred', ('field', 'value', 'evidence')), ('observations', ('code', 'message'))):
        items = candidate.get(key)
        if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
            error(key + ' must be an array of objects')
        for item in items:
            for field in fields:
                if field not in item:
                    error(key + ' is missing ' + field)
            for field in (('field',) if key == 'inferred' else fields):
                string_at(item, field)
    def json_value(value, depth=0):
        if depth > 64:
            error('Candidate nesting exceeds 64 levels')
        if value is None or isinstance(value, (str, bool, int)):
            return
        if isinstance(value, float):
            if not math.isfinite(value):
                error('Candidate numbers must be finite')
            return
        if isinstance(value, list):
            for item in value:
                json_value(item, depth + 1)
            return
        if isinstance(value, dict) and all(isinstance(key, str) for key in value):
            for item in value.values():
                json_value(item, depth + 1)
            return
        error('Candidate values and object keys must have JSON types')

    json_value(candidate)
    try:
        json.dumps(candidate, allow_nan=False)
    except (TypeError, ValueError, RecursionError):
        error('Candidate must contain only finite JSON-serializable values')
