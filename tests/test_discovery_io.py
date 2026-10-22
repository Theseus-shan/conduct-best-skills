"""Discovery transport/cache invariants using fake responses, never live HTTP."""
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
from urllib.error import HTTPError, URLError
from urllib.request import Request

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/conduct-best-skills/scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import discovery_io as dio

URL = "https://api.github.com/search/repositories?q=csv"


class FakeResponse:
    def __init__(self, raw):
        self.raw = raw
        self.read_sizes = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size):
        self.read_sizes.append(size)
        return self.raw[:size]


class FakeOpener:
    def __init__(self, *effects):
        self.effects = list(effects)
        self.calls = []

    def open(self, request, timeout):
        self.calls.append((request, timeout))
        if not self.effects:
            raise AssertionError("Unexpected HTTP attempt")
        result = self.effects.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result


def response(value):
    return FakeResponse(json.dumps(value).encode("utf-8"))


class DiscoveryIOTests(unittest.TestCase):
    def test_streaming_body_checks_budget_between_chunks(self):
        budget = dio.Budget(seconds=1, retries=0)
        class StreamingResponse(FakeResponse):
            def read1(self, size):
                budget.deadline = 0
                return b'{' + b' ' * 5
        client = dio.HttpClient(budget=budget, opener=FakeOpener(StreamingResponse(b'')))
        self.assert_error('BUDGET', lambda: client.get_json(URL, provider='github'))

    def test_unicode_escaped_credential_reflection_is_discarded(self):
        token = 'secretToken123'
        raw = b'{"echo":"\\u0073ecretToken123"}'
        client = dio.HttpClient(cache=self.cache, opener=FakeOpener(FakeResponse(raw)))
        self.assert_error('SECRET_REFLECTION', lambda: client.get_json(URL, provider='github',
                          headers={'Authorization': 'Bearer ' + token}))
        self.assertFalse(list(self.root.rglob('*.json')))

    def test_response_crossing_deadline_does_not_become_fresh_evidence(self):
        budget = dio.Budget(seconds=1, retries=0)
        class LateResponse(FakeResponse):
            def read(self, size):
                budget.deadline = 0
                return super().read(size)
        client = dio.HttpClient(budget=budget, opener=FakeOpener(LateResponse(b'{}')))
        self.assert_error('BUDGET', lambda: client.get_json(URL, provider='github'))

    def setUp(self):
        scratch = ROOT / "local" / "discovery-io-tests"
        scratch.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix="io-", dir=scratch)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.now = 1000.0
        self.cache = dio.Cache(self.root, clock=lambda: self.now)

    def assert_error(self, code, operation):
        with self.assertRaises(dio.DiscoveryError) as caught:
            operation()
        self.assertEqual(caught.exception.code, code)
        return caught.exception

    def test_request_budget_counts_retries_and_caps_network_calls(self):
        opener = FakeOpener(URLError("temporary"))
        client = dio.HttpClient(budget=dio.Budget(requests=1, retries=2), opener=opener)
        self.assert_error("BUDGET", lambda: client.get_json(URL, provider="github"))
        self.assertEqual(len(opener.calls), 1)
        self.assertEqual(client.budget.used, 1)

    def test_deadline_prevents_calls_and_caps_socket_timeout(self):
        with mock.patch.object(dio.time, "monotonic", return_value=100):
            budget = dio.Budget(seconds=2, timeout=10)
        opener = FakeOpener(response({"ok": True}))
        client = dio.HttpClient(budget=budget, opener=opener)
        with mock.patch.object(dio.time, "monotonic", return_value=101.5):
            self.assertEqual(client.get_json(URL, provider="github"), {"ok": True})
        self.assertEqual(opener.calls[0][1], 0.5)
        with mock.patch.object(dio.time, "monotonic", return_value=102):
            self.assert_error("BUDGET", lambda: client.get_json(URL, provider="github"))
        self.assertEqual(len(opener.calls), 1)

    def test_invalid_budgets_rejected(self):
        for options in ({"requests": -1}, {"requests": True}, {"requests": 201},
                        {"seconds": 0}, {"seconds": float("nan")},
                        {"timeout": float("inf")}, {"retries": 3}):
            with self.subTest(options=options):
                self.assert_error("CONFIG", lambda: dio.Budget(**options))

    def test_size_limit_reads_only_boundary_plus_one(self):
        oversized = FakeResponse(b"a" * 2_000_001)
        client = dio.HttpClient(opener=FakeOpener(oversized))
        self.assert_error("SIZE_LIMIT", lambda: client.get_text(URL, provider="github"))
        self.assertEqual(oversized.read_sizes, [2_000_001])
        exact = FakeResponse(b"a" * 2_000_000)
        self.assertEqual(len(dio.HttpClient(opener=FakeOpener(exact)).get_text(
            URL, provider="github")), 2_000_000)

    def test_auth_permission_and_rate_errors_never_retry(self):
        for status, code in ((401, "AUTH"), (403, "RATE_LIMIT"), (429, "RATE_LIMIT")):
            with self.subTest(status=status):
                error = HTTPError(URL, status, "secret in remote reason", {"Retry-After": "120"},
                                  io.BytesIO(b"sensitive remote body"))
                opener = FakeOpener(error)
                client = dio.HttpClient(budget=dio.Budget(retries=2), opener=opener)
                failure = self.assert_error(code, lambda: client.get_json(URL, provider="github"))
                self.assertEqual(len(opener.calls), 1)
                self.assertNotIn("secret", str(failure))
                self.assertNotIn("sensitive", str(failure))

    def test_temporary_502_retries_within_budget(self):
        opener = FakeOpener(HTTPError(URL, 502, "bad gateway", {}, None), response({"found": 1}))
        client = dio.HttpClient(opener=opener, budget=dio.Budget(retries=1))
        self.assertEqual(client.get_json(URL, provider="github"), {"found": 1})
        self.assertEqual(len(opener.calls), 2)

    def test_retry_after_stops_retries_and_only_records_safe_value(self):
        for header, recorded in (("120", "120"), ("private-token/date", "service-specified")):
            with self.subTest(header=header):
                opener = FakeOpener(HTTPError(URL, 503, "temporary", {"Retry-After": header}, None))
                client = dio.HttpClient(opener=opener, budget=dio.Budget(retries=2))
                self.assert_error("HTTP", lambda: client.get_json(URL, provider="github"))
                self.assertEqual(len(opener.calls), 1)
                self.assertEqual(client.events[-1]["status"], "RETRY_LATER")
                self.assertEqual(client.events[-1]["retry_after"], recorded)
                self.assertNotIn("private-token", json.dumps(client.events))

    def test_skillsmp_http_errors_never_retry_uncertain_charges(self):
        url = "https://skillsmp.com/api/v1/skills/search?q=csv"
        for status in (500, 502, 503, 504):
            with self.subTest(status=status):
                opener = FakeOpener(HTTPError(url, status, "uncertain", {}, io.BytesIO(
                    b'{"error":{"code":"SEARCH_COMPLETION_UNCERTAIN"}}')))
                client = dio.HttpClient(opener=opener, budget=dio.Budget(retries=2))
                self.assert_error("HTTP", lambda: client.get_json(url, provider="skillsmp"))
                self.assertEqual(len(opener.calls), 1)

    def test_timeout_and_urlerror_are_bounded_and_sanitized(self):
        for error in (TimeoutError("private token"), URLError("private endpoint")):
            with self.subTest(error=type(error).__name__):
                opener = FakeOpener(error, error)
                client = dio.HttpClient(opener=opener, budget=dio.Budget(retries=1))
                failure = self.assert_error("NETWORK", lambda: client.get_json(URL, provider="github"))
                self.assertEqual(len(opener.calls), 2)
                self.assertNotIn("private", str(failure))
                # Another provider/client still works after this source's failure.
                other = dio.HttpClient(opener=FakeOpener(response([1])))
                self.assertEqual(other.get_json("https://skillsmp.com/api/v1/skills/search?q=csv",
                                                provider="skillsmp"), [1])

    def test_redirect_handler_blocks_location_before_following(self):
        handler = dio.NoRedirect()
        self.assert_error("REDIRECT", lambda: handler.redirect_request(
            Request(URL), None, 302, "moved", {}, "https://evil.example/steal"))

    def test_untrusted_urls_rejected_without_network(self):
        opener = FakeOpener()
        client = dio.HttpClient(opener=opener)
        for url in ("http://api.github.com/x", "https://evil.example/x",
                    "https://api.github.com.evil.example/x", "https://127.0.0.1/x",
                    "https://name:password@api.github.com/x", "https://api.github.com:8443/x",
                    "https://api.github.com:bad/x", "https://api.github.com:99999/x",
                    "https://api.github.com/x#fragment"):
            with self.subTest(url=url):
                self.assert_error("URL_POLICY", lambda: client.get_json(url, provider="github"))
        self.assertFalse(opener.calls)

    def test_invalid_response_does_not_retry_or_cache(self):
        for raw in (b"not json", b"\xff\xfe\xff"):
            opener = FakeOpener(FakeResponse(raw))
            client = dio.HttpClient(cache=self.cache, opener=opener)
            self.assert_error("RESPONSE", lambda: client.get_json(URL, provider="github"))
            self.assertEqual(len(opener.calls), 1)
        self.assertFalse(list(self.root.rglob("*.json")))

    def test_credentials_are_explicit_opt_in_and_names_allowlisted(self):
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": "test-only-secret"}):
            self.assertIsNone(dio.HttpClient().credential("GITHUB_TOKEN"))
            client = dio.HttpClient(allow_credentials=True)
            self.assertEqual(client.credential("GITHUB_TOKEN"), "test-only-secret")
            self.assert_error("CONFIG", lambda: client.credential("UNRELATED_SECRET"))

    def test_headers_scope_caches_without_persisting_credentials(self):
        opener = FakeOpener(response({"scope": "first"}), response({"scope": "second"}))
        client = dio.HttpClient(cache=self.cache, opener=opener)
        headers_a = {"Authorization": "Bearer synthetic-token-a"}
        headers_b = {"Authorization": "Bearer synthetic-token-b"}
        self.assertEqual(client.get_json(URL, provider="github", headers=headers_a)["scope"], "first")
        self.assertEqual(client.get_json(URL, provider="github", headers=headers_b)["scope"], "second")
        self.assertEqual(client.get_json(URL, provider="github", headers=headers_a)["scope"], "first")
        self.assertEqual(len(opener.calls), 2)
        files = list(self.root.rglob("*.json"))
        self.assertEqual(len(files), 2)
        stored = "".join(path.read_text(encoding="utf-8") for path in files) + json.dumps(client.events)
        self.assertNotIn("synthetic-token", stored)
        self.assertNotIn(URL, stored)

    def test_reflected_credentials_discarded_before_cache_or_logs(self):
        for headers in ({"Authorization": "Bearer synthetic-secret"},
                        {"x-vercel-oidc-token": "synthetic-secret"}):
            client = dio.HttpClient(cache=self.cache, opener=FakeOpener(
                response({"data": "synthetic-secret"})))
            error = self.assert_error("SECRET_REFLECTION", lambda: client.get_json(
                URL, provider="github", headers=headers))
            self.assertNotIn("synthetic-secret", str(error) + json.dumps(client.events))
        self.assertFalse(list(self.root.rglob("*.json")))

    def test_ttl_expiry_refresh_and_source_specific_refresh(self):
        opener = FakeOpener(response({"v": 1}), response({"v": 2}), response({"v": 3}))
        client = dio.HttpClient(cache=self.cache, opener=opener)
        self.assertEqual(client.get_json(URL, provider="github", ttl=10), {"v": 1})
        self.now += 5
        self.assertEqual(client.get_json(URL, provider="github", ttl=10), {"v": 1})
        self.now += 6
        self.assertEqual(client.get_json(URL, provider="github", ttl=10), {"v": 2})
        other_refresh = dio.HttpClient(cache=self.cache, opener=opener, refresh=["skillsmp"])
        self.assertEqual(other_refresh.get_json(URL, provider="github"), {"v": 2})
        matching_refresh = dio.HttpClient(cache=self.cache, opener=opener, refresh=["github"])
        self.assertEqual(matching_refresh.get_json(URL, provider="github"), {"v": 3})
        self.assertEqual(len(opener.calls), 3)

    def test_offline_uses_fresh_or_bounded_stale_without_http(self):
        online = dio.HttpClient(cache=self.cache, opener=FakeOpener(response({"cached": 1})))
        online.get_json(URL, provider="github", ttl=10)
        opener = FakeOpener()
        client = dio.HttpClient(cache=self.cache, opener=opener, offline=True)
        self.assertEqual(client.get_json(URL, provider="github"), {"cached": 1})
        self.assertEqual(client.events[-1]["cache"], "HIT")
        self.now += 11
        self.assertEqual(client.get_json(URL, provider="github"), {"cached": 1})
        self.assertEqual(client.events[-1]["cache"], "STALE_FALLBACK")
        self.assertEqual(client.events[-1]["reason"], "OFFLINE")
        self.now += 604801
        self.assert_error("OFFLINE", lambda: client.get_json(URL, provider="github"))
        self.assertFalse(opener.calls)

    def test_auth_error_cannot_be_hidden_by_stale_cache(self):
        dio.HttpClient(cache=self.cache, opener=FakeOpener(response({"cached": 1}))).get_json(
            URL, provider="github", ttl=1)
        self.now += 2
        opener = FakeOpener(HTTPError(URL, 401, "no", {}, None))
        client = dio.HttpClient(cache=self.cache, opener=opener)
        self.assert_error("AUTH", lambda: client.get_json(URL, provider="github"))
        self.assertFalse(any(e["cache"] == "STALE_FALLBACK" for e in client.events))

    def test_malformed_future_and_oversized_cache_are_misses(self):
        path = self.cache.path("search", "key")
        path.parent.mkdir(parents=True, exist_ok=True)
        for data in ("{broken", "[]", '{}', '{"schema_version": 9}', "x" * 4_000_001,
                     json.dumps({"schema_version": 1, "saved_at": self.now + 1, "ttl": 10, "payload": 1})):
            path.write_text(data, encoding="utf-8")
            self.assertIsNone(self.cache.get("search", "key", stale=True))

    def test_nonfinite_invalid_cache_times_and_ttls_are_rejected(self):
        path = self.cache.path("search", "key")
        path.parent.mkdir(parents=True, exist_ok=True)
        for field in ("saved_at", "ttl"):
            for value in (float("nan"), float("inf"), -float("inf"), True, "10", None):
                row = {"schema_version": 1, "saved_at": self.now, "ttl": 60, "payload": 1}
                row[field] = value
                with self.subTest(field=field, value=value):
                    path.write_text(json.dumps(row), encoding="utf-8")
                    self.assertIsNone(self.cache.get("search", "key", stale=True))
        for ttl in (float("nan"), float("inf"), -1, 604801, True, "60"):
            with self.subTest(ttl=ttl):
                self.assert_error("CONFIG", lambda: self.cache.put("search", "key", {}, ttl))

    def test_disabled_cache_writes_nothing_and_namespace_is_restricted(self):
        disabled = dio.Cache(self.root, directory="")
        disabled.put("search", "key", {"x": 1}, 60)
        self.assertIsNone(disabled.get("search", "key"))
        self.assertFalse(list(self.root.iterdir()))
        self.assert_error("CONFIG", lambda: self.cache.path("../../outside", "key"))

    def test_cache_symlink_cannot_redirect_writes_or_reads(self):
        outside = self.root / "outside"
        outside.mkdir()
        folder = self.root / ".conduct-discovery"
        folder.mkdir()
        link = folder / "search"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"Directory symlinks unsupported in this environment: {exc}")
        self.addCleanup(link.unlink)
        with self.assertRaises(ValueError):
            self.cache.put("search", "key", {"must_not_escape": True}, 60)
        self.assertIsNone(self.cache.get("search", "key", stale=True))
        self.assertFalse(list(outside.iterdir()))


if __name__ == "__main__":
    unittest.main()
