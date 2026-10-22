"""Bounded public GET transport and task-local caches; never executes a Skill."""
import hashlib
import json
import math
import os
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

from conduct import atomic_json, local_path
from discovery_core import DiscoveryError


class Budget:
    def __init__(self, requests=30, seconds=60, timeout=10, retries=1):
        if not (type(requests) is int and 0 <= requests <= 200 and
                type(retries) is int and 0 <= retries <= 2 and
                isinstance(seconds, (int, float)) and math.isfinite(seconds) and 0 < seconds <= 600 and
                isinstance(timeout, (int, float)) and math.isfinite(timeout) and 0 < timeout <= 30):
            raise DiscoveryError('CONFIG', 'Invalid discovery request/time/retry budget')
        self.limit, self.used = requests, 0
        self.deadline = time.monotonic() + seconds
        self.timeout, self.retries = timeout, retries

    def check(self):
        if time.monotonic() >= self.deadline:
            raise DiscoveryError('BUDGET', 'Discovery time budget exhausted')

    def take(self):
        self.check()
        if self.used >= self.limit:
            raise DiscoveryError('BUDGET', 'Discovery request budget exhausted')
        self.used += 1
        return min(self.timeout, max(0.001, self.deadline - time.monotonic()))


class Cache:
    """Versioned JSON envelopes. Cache is data, never an approval record."""
    def __init__(self, workspace, directory='.conduct-discovery', clock=time.time):
        self.root = Path(workspace).resolve()
        self.folder = local_path(self.root, directory) if directory else None
        self.clock, self.events = clock, []

    def path(self, bucket, key):
        if bucket not in {'metadata', 'search'}:
            raise DiscoveryError('CONFIG', 'Unknown cache namespace')
        name = hashlib.sha256(key.encode('utf-8')).hexdigest() + '.json'
        relative = (self.folder.relative_to(self.root) / bucket / name).as_posix()
        return local_path(self.root, relative)

    def get(self, bucket, key, stale=False):
        if self.folder is None:
            return None
        try:
            path = self.path(bucket, key)
            if path.stat().st_size > 12_000_000:
                return None
            row = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(row, dict):
                return None
            if not all(type(row.get(k)) in (int, float) and math.isfinite(row[k]) for k in ('saved_at', 'ttl')) or not 0 <= row['ttl'] <= 604800:
                return None
            age = self.clock() - row['saved_at']
            if row['schema_version'] != 1 or age < 0:
                return None
            expired = age > row['ttl']
            if age > row['ttl'] + 604800 or (expired and not stale):
                return None
            return {'payload': row['payload'], 'stale': expired, 'saved_at': row['saved_at']}
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def put(self, bucket, key, payload, ttl):
        if type(ttl) not in (int, float) or not math.isfinite(ttl) or not 0 <= ttl <= 604800:
            raise DiscoveryError('CONFIG', 'Invalid cache TTL')
        if self.folder is None:
            return
        path = self.path(bucket, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Recheck after mkdir, including symlinks and Windows junctions.
        path = self.path(bucket, key)
        atomic_json(path, {'schema_version': 1, 'saved_at': self.clock(), 'ttl': ttl, 'payload': payload})


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise DiscoveryError('REDIRECT', 'Redirect refused; review the source endpoint')


class HttpClient:
    HOSTS = {'api.github.com', 'raw.githubusercontent.com', 'skills.sh', 'skillsmp.com'}

    def __init__(self, budget=None, cache=None, offline=False, refresh=(), allow_credentials=False, opener=None):
        self.budget = budget or Budget()
        self.cache, self.offline = cache, offline
        self.refresh, self.allow_credentials = set(refresh), allow_credentials
        self.opener = opener or build_opener(NoRedirect())
        self.events = []

    def credential(self, name):
        if not self.allow_credentials:
            return None
        if name not in {'GITHUB_TOKEN', 'SKILLSMP_API_KEY', 'VERCEL_OIDC_TOKEN'}:
            raise DiscoveryError('CONFIG', 'Unsupported credential variable')
        return os.environ.get(name) or None

    def get_json(self, url, *, provider, bucket='search', headers=None, ttl=None, max_bytes=2_000_000):
        return self._get(url, provider, bucket, headers, ttl, True, max_bytes)

    def get_text(self, url, *, provider, bucket='metadata', headers=None, ttl=None):
        return self._get(url, provider, bucket, headers, ttl, False, 2_000_000)

    def _get(self, url, provider, bucket, headers, ttl, as_json, max_bytes):
        if type(max_bytes) is not int or not 1 <= max_bytes <= 8_000_000:
            raise DiscoveryError('CONFIG', 'Response limit must be between 1 and 8000000 bytes')
        try:
            parsed = urlsplit(url)
            port = parsed.port
        except ValueError as exc:
            raise DiscoveryError('URL_POLICY', 'Invalid public endpoint URL') from exc
        if (parsed.scheme != 'https' or parsed.hostname not in self.HOSTS or parsed.username or
                parsed.password or port not in {None, 443} or parsed.fragment):
            raise DiscoveryError('URL_POLICY', 'Only configured public HTTPS service endpoints are allowed')
        headers = dict(headers or {})
        # Do not persist header values, request URLs, or error bodies. Scope caches
        # to the credential identity without storing the credential itself.
        scope = hashlib.sha256(json.dumps(headers, sort_keys=True).encode()).hexdigest()
        key = json.dumps([provider, url, scope, as_json, max_bytes])
        fresh = self.cache.get(bucket, key) if self.cache else None
        if fresh and provider not in self.refresh:
            self.events.append({'provider': provider, 'cache': 'HIT', 'bucket': bucket, 'saved_at': fresh['saved_at']})
            return fresh['payload']
        failure = DiscoveryError('OFFLINE', 'Network disabled; no current cached response')
        if not self.offline:
            for attempt in range(self.budget.retries + 1):
                try:
                    timeout = self.budget.take()
                    req = Request(url, headers={'User-Agent': 'conduct-best-skills-discovery/1', **headers}, method='GET')
                    with self.opener.open(req, timeout=timeout) as response:
                        if hasattr(response, 'read1'):
                            chunks, length = [], 0
                            while length <= max_bytes:
                                self.budget.check()
                                chunk = response.read1(min(65536, max_bytes + 1 - length))
                                self.budget.check()
                                if not chunk:
                                    break
                                chunks.append(chunk)
                                length += len(chunk)
                            raw = b''.join(chunks)
                        else:
                            raw = response.read(max_bytes + 1)
                    self.budget.check()
                    if len(raw) > max_bytes:
                        raise DiscoveryError('SIZE_LIMIT', 'Response exceeds metadata size budget')
                    text = raw.decode('utf-8-sig')
                    data = json.loads(text) if as_json else text
                    # A service must not reflect our credential into logs or caches.
                    secrets = [v for k, v in headers.items() if k.lower() in {'authorization', 'x-vercel-oidc-token'}]
                    for secret in secrets:
                        token = secret.removeprefix('Bearer ')
                        decoded = json.dumps(data, ensure_ascii=False) if as_json else text
                        if token and (token in text or token in decoded):
                            raise DiscoveryError('SECRET_REFLECTION', 'Service reflected credential; response discarded')
                    if self.cache:
                        try:
                            self.cache.put(bucket, key, data, ttl if ttl is not None else (3600 if bucket == 'search' else 86400))
                        except (OSError, ValueError):
                            self.events.append({'provider': provider, 'cache': 'WRITE_FAILED', 'bucket': bucket})
                    self.events.append({'provider': provider, 'cache': 'MISS', 'bucket': bucket})
                    return data
                except HTTPError as exc:
                    code = 'AUTH' if exc.code == 401 else 'RATE_LIMIT' if exc.code in {403, 429} else 'HTTP'
                    failure = DiscoveryError(code, f'Public service returned HTTP {exc.code}')
                    # Do not wait out service limits inside a discovery budget;
                    # stop this source so the host may retry after the indicated time.
                    retry_after = exc.headers.get('Retry-After') if exc.headers else None
                    exc.close()
                    if retry_after:
                        self.events.append({'provider': provider, 'status': 'RETRY_LATER',
                                            'retry_after': retry_after if retry_after.isdigit() else 'service-specified'})
                    if exc.code not in {502, 503, 504} or retry_after or provider == 'skillsmp':
                        break
                except (TimeoutError, URLError, OSError):
                    failure = DiscoveryError('NETWORK', 'Public service timed out or could not be reached')
                except (UnicodeError, json.JSONDecodeError):
                    failure = DiscoveryError('RESPONSE', 'Invalid service response encoding or JSON')
                    break
                except DiscoveryError as exc:
                    failure = exc
                    break
        # Never disguise denied authentication, permissions, or rate limits as success.
        if failure.code in {'OFFLINE', 'NETWORK', 'HTTP', 'BUDGET'} and self.cache:
            old = self.cache.get(bucket, key, stale=True)
            if old:
                self.events.append({'provider': provider, 'cache': 'STALE_FALLBACK', 'bucket': bucket,
                                    'reason': failure.code, 'saved_at': old['saved_at']})
                return old['payload']
        raise failure
