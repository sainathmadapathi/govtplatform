"""GovOS's unauthenticated network surface: what it serves, where it listens, and what one request may
make it fetch.

* Files: only the built frontend in dist/ is ever served. With no build, pages are a 503 -- the repository
  root (.env, govos.db, app.py) used to be served instead, at /<file> and at Flask's /static/<file>.
* Binding: `python app.py` listens on 127.0.0.1 unless GOVOS_HOST says otherwise (it was 0.0.0.0).
* Link checking (verify-links, health/sync, health/recheck, channel-uploads): a bounded number of URLs per
  request, GovOS's one URL rule (no odd ports, no IP literals, length cap), one shared worker pool, a
  per-request deadline, reuse of a recent check, one fetch per URL however many ask at once, a per-client
  rate limit and a global outbound budget -- and every SSRF refusal still holds through the routes.

No test reaches the network: DNS is replaced (test_live_resources.offline_dns) and the outbound fetch is
stubbed or pointed at a stand-in server on this machine. Every test uses its own temporary database.

Run: python -m pytest test_network_exposure.py -q
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
import unittest
from unittest import mock

import app as govos
from test_live_resources import REFUSED, _StubOpener, _TempDb, fixture_origin, offline_dns, public_host

PUBLIC = ('portal.example.gov.in', 'www.example.org', 'notices.example.nic.in')


class _Counted:
    """A stand-in for `_check_one_link` that counts outbound checks (optionally slowly)."""

    def __init__(self, delay=0.0):
        self.urls = []
        self.lock = threading.Lock()
        self.delay = delay

    def __call__(self, url):
        with self.lock:
            self.urls.append(url)
        if self.delay:
            time.sleep(self.delay)
        return {"url": url, "status": "HEALTHY", "httpCode": 200, "checkedAt": govos._now_iso()}


class _LinkRoutes(_TempDb):
    """The link routes with a fresh limiter, budget and reuse cache for every test."""

    def setUp(self):
        super().setUp()
        offline_dns(self)
        govos._link_limiter().reset()
        govos._recent_links.clear()
        self._budget = govos._LINK_BUDGET
        govos._LINK_BUDGET = govos._OutboundBudget(govos.LINK_OUTBOUND_PER_MINUTE)
        self.client = govos.app.test_client()

    def tearDown(self):
        govos._LINK_BUDGET = self._budget
        govos._link_limiter().reset()
        govos._recent_links.clear()
        super().tearDown()

    def post(self, route, urls):
        r = self.client.post(f'/api/resources/{route}', json={'urls': urls})
        return r.status_code, r.get_json(), r

    def counted(self, delay=0.0):
        stub = _Counted(delay)
        patch = mock.patch.object(govos, '_check_one_link', stub)
        patch.start()
        self.addCleanup(patch.stop)
        return stub


# --------------------------------------------------------------------------- 1. repository files
class RepositoryFileTests(unittest.TestCase):
    SENSITIVE = ['/.env', '/govos.db', '/app.py', '/requirements.txt', '/.env.example', '/tools/claude_cli/security.py',
                 '/static/.env', '/static/govos.db', '/static/app.py', '/../.env', '/%2e%2e/.env', '/..%2f.env',
                 '/dist/../app.py', '/.git/config', '/C:/Windows/win.ini', '/%5c..%5capp.py', '/src/ui.tsx']
    SECRET_MARKERS = (b'GOVOS_', b'SQLite format 3', b'def parse_result_document', b'Flask(__name__', b'export const')

    def setUp(self):
        self.client = govos.app.test_client()
        self._dist = govos.DIST_DIR

    def tearDown(self):
        govos.DIST_DIR = self._dist

    def make_dist(self):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, 'index.html'), 'w', encoding='utf-8') as fh:
            fh.write('<!doctype html><title>GovOS</title><div id="root">GOVOS-INDEX</div>')
        os.makedirs(os.path.join(d, 'assets'))
        with open(os.path.join(d, 'assets', 'app.js'), 'w', encoding='utf-8') as fh:
            fh.write('console.log("GOVOS-ASSET")')
        govos.DIST_DIR = d
        return d

    def assertNoRepositoryFile(self, r, path):
        for marker in self.SECRET_MARKERS:
            self.assertNotIn(marker, r.data, f'{path} returned repository content')

    def test_there_is_no_flask_static_route(self):
        self.assertNotIn('static', govos.app.view_functions)
        self.assertIsNone(govos.app.static_folder)

    def test_with_a_build_the_frontend_is_served(self):
        self.make_dist()
        for path in ('/', '/exam/ssc', '/some/client/route'):
            r = self.client.get(path)
            self.assertEqual(r.status_code, 200, path)
            self.assertIn(b'GOVOS-INDEX', r.data)
        r = self.client.get('/assets/app.js')
        self.assertEqual((r.status_code, b'GOVOS-ASSET' in r.data), (200, True))

    def test_with_a_build_no_repository_file_is_served(self):
        self.make_dist()
        for path in self.SENSITIVE:
            with self.subTest(path=path):
                r = self.client.get(path)
                self.assertIn(r.status_code, (400, 404), (path, r.status_code))
                self.assertNoRepositoryFile(r, path)

    def test_without_a_build_pages_are_a_controlled_503_and_no_file_is_served(self):
        govos.DIST_DIR = os.path.join(tempfile.mkdtemp(), 'no-dist-here')
        r = self.client.get('/')
        self.assertEqual((r.status_code, r.get_json()['error']), (503, 'FRONTEND_NOT_BUILT'))
        for path in self.SENSITIVE + ['/index.html', '/vite.config.ts', '/package.json']:
            with self.subTest(path=path):
                r = self.client.get(path)
                self.assertIn(r.status_code, (400, 404, 503), (path, r.status_code))
                self.assertNoRepositoryFile(r, path)

    def test_without_a_build_the_api_still_answers(self):
        govos.DIST_DIR = os.path.join(tempfile.mkdtemp(), 'no-dist-here')
        self.assertEqual(self.client.get('/api/sqlite/status').status_code, 200)


# --------------------------------------------------------------------------- 2. where the server listens
class BindTests(unittest.TestCase):

    def test_the_default_is_this_machine_only(self):
        self.assertEqual(govos._bind_host({}), '127.0.0.1')
        self.assertEqual(govos._bind_host({'GOVOS_HOST': '   '}), '127.0.0.1')
        self.assertEqual(govos._bind_host({'PORT': '8080'}), '127.0.0.1')

    def test_a_deployment_can_choose_a_public_bind_explicitly(self):
        self.assertEqual(govos._bind_host({'GOVOS_HOST': '0.0.0.0'}), '0.0.0.0')
        self.assertEqual(govos._bind_host({'GOVOS_HOST': '192.168.1.20'}), '192.168.1.20')

    def test_the_server_runs_on_the_chosen_host_and_never_on_a_hard_coded_one(self):
        source = open(govos.__file__, encoding='utf-8').read()
        main = source[source.index("if __name__ == '__main__':"):]
        self.assertIn('app.run(host=host,', main)
        self.assertNotIn("host='0.0.0.0'", source)

    def test_the_setting_is_read_from_env_like_every_govos_setting(self):
        self.assertTrue('GOVOS_HOST'.startswith('GOVOS_'))           # _load_dotenv reads GOVOS_* and PORT only
        example = open(os.path.join(govos.BASE_DIR, '.env.example'), encoding='utf-8').read()
        self.assertIn('GOVOS_HOST', example)

    def test_the_dev_proxy_targets_loopback(self):
        vite = open(os.path.join(govos.BASE_DIR, 'vite.config.ts'), encoding='utf-8').read()
        self.assertIn("target: 'http://127.0.0.1:5000'", vite)


# --------------------------------------------------------------------------- 3. link-health limits
class LinkLimitTests(_LinkRoutes):

    def test_more_urls_than_the_limit_is_refused_before_anything_is_fetched(self):
        stub = self.counted()
        urls = [f'https://portal.example.gov.in/p{i}' for i in range(govos.LINK_MAX_URLS + 1)]
        for route in ('verify-links', 'health/recheck', 'health/sync'):
            with self.subTest(route=route):
                status, body, _ = self.post(route, urls)
                self.assertEqual((status, body['error'], body['limit']), (413, 'TOO_MANY_URLS', govos.LINK_MAX_URLS))
        self.assertEqual(stub.urls, [])

    def test_a_huge_list_is_refused_by_its_length_alone(self):
        stub = self.counted()
        started = time.time()
        status, body, _ = self.post('verify-links', ['https://x.example.org/'] * 100_000)
        self.assertEqual(status, 413)
        self.assertLess(time.time() - started, 2)
        self.assertEqual(stub.urls, [])

    def test_the_largest_library_fits(self):
        self.assertGreaterEqual(govos.LINK_MAX_URLS, 38 + 20)       # SSC CGL's 38 links, plus additions

    def test_an_over_long_url_is_refused_without_a_fetch(self):
        with mock.patch.object(govos.urllib.request, 'build_opener', side_effect=AssertionError('fetched')):
            status, body, _ = self.post('verify-links', ['https://www.example.org/' + 'a' * 3000])
        self.assertEqual(status, 200)
        self.assertEqual(body['results'][0]['refused'], 'URL is too long')

    def test_unsupported_schemes_are_never_fetched(self):
        with mock.patch.object(govos.urllib.request, 'build_opener', side_effect=AssertionError('fetched')):
            status, body, _ = self.post('verify-links', REFUSED['unsupported scheme'])
        self.assertEqual(status, 400)                        # nothing http(s) left to check
        for url in REFUSED['unsupported scheme']:
            self.assertFalse(govos._public_link(url)[0], url)

    def test_a_non_standard_port_is_refused_without_a_fetch(self):
        patch, _ = public_host(*PUBLIC)
        with patch, mock.patch.object(govos.urllib.request, 'build_opener', side_effect=AssertionError('fetched')):
            status, body, _ = self.post('verify-links', ['https://www.example.org:8443/', 'http://www.example.org:22/',
                                                         'http://www.example.org:6379/'])
        self.assertEqual(status, 200)
        self.assertEqual({r['refused'] for r in body['results']}, {'URL uses a non-standard port'})

    def test_each_socket_operation_uses_the_bounded_timeout(self):
        seen = []

        class Recording(_StubOpener):
            def open(self, req, timeout=None):
                seen.append(timeout)
                return super().open(req, timeout)
        patch, _ = public_host(*PUBLIC)
        with patch, mock.patch.object(govos.urllib.request, 'build_opener', return_value=Recording()):
            govos._check_one_link('https://www.example.org/')
        self.assertEqual(seen, [govos.LINK_TIMEOUT_SECONDS])

    def test_a_request_waits_no_longer_than_its_deadline(self):
        self.counted(delay=3.0)
        with mock.patch.object(govos, 'LINK_REQUEST_DEADLINE_SECONDS', 0.3):
            started = time.time()
            status, body, _ = self.post('verify-links', ['https://www.example.org/slow'])
            took = time.time() - started
        self.assertEqual(status, 200)
        self.assertLess(took, 2, 'the request waited for the slow check')
        self.assertEqual(body['results'][0]['refused'], 'timed out')

    def test_redirects_are_capped(self):
        self.assertEqual(govos._PublicRedirects.max_redirections, govos.LINK_MAX_REDIRECTS)
        self.assertLessEqual(govos.LINK_MAX_REDIRECTS, 5)

    def test_identical_urls_in_one_request_are_fetched_once(self):
        stub = self.counted()
        status, body, _ = self.post('verify-links', ['https://www.example.org/a'] * 50)
        self.assertEqual((status, len(body['results']), stub.urls), (200, 1, ['https://www.example.org/a']))

    def test_a_recent_check_is_reused_not_fetched_again(self):
        stub = self.counted()
        urls = ['https://www.example.org/a', 'https://www.example.org/b']
        self.post('verify-links', urls)
        status, body, _ = self.post('health/recheck', urls)
        self.assertEqual(status, 200)
        self.assertEqual(len(stub.urls), 2, 'the second request fetched again')
        self.assertTrue(all(r.get('reused') for r in body['results']))

    def test_concurrent_requests_for_one_url_share_one_fetch(self):
        stub = self.counted(delay=0.5)
        barrier = threading.Barrier(5)
        codes = []

        def one():
            client = govos.app.test_client()
            barrier.wait()
            codes.append(client.post('/api/resources/verify-links', json={'urls': ['https://www.example.org/same']}).status_code)
        threads = [threading.Thread(target=one) for _ in range(5)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(sorted(codes), [200] * 5)
        self.assertEqual(stub.urls, ['https://www.example.org/same'])

    def test_a_client_over_its_rate_is_answered_429(self):
        self.counted()
        for route, scope in (('verify-links', 'verify'), ('health/recheck', 'recheck'), ('health/sync', 'sync')):
            with self.subTest(route=route):
                govos._link_limiter().reset()
                for i in range(govos.LINK_RATE[scope]):
                    self.assertNotEqual(self.post(route, [f'https://www.example.org/{route}/{i}'])[0], 429)
                status, body, r = self.post(route, ['https://www.example.org/over'])
                self.assertEqual((status, body['error']), (429, 'RATE_LIMITED'))
                self.assertGreaterEqual(int(r.headers['Retry-After']), 1)

    def test_the_global_outbound_budget_stops_a_burst_before_any_fetch(self):
        stub = self.counted()
        govos._LINK_BUDGET = govos._OutboundBudget(5)
        status, body, _ = self.post('verify-links', [f'https://www.example.org/{i}' for i in range(10)])
        self.assertEqual((status, body['error']), (429, 'OUTBOUND_BUDGET'))
        self.assertEqual(stub.urls, [])
        self.assertEqual(self.post('verify-links', ['https://www.example.org/x'])[0], 200)   # 1 of 5 still left

    def test_a_legitimate_small_batch_succeeds(self):
        patch, _ = public_host(*PUBLIC)
        urls = ['https://portal.example.gov.in/notice', 'https://www.example.org/syllabus', 'https://notices.example.nic.in/']
        with patch, mock.patch.object(govos.urllib.request, 'build_opener', return_value=_StubOpener()):
            for route in ('verify-links', 'health/recheck'):
                govos._recent_links.clear()
                status, body, _ = self.post(route, urls)
                self.assertEqual(status, 200, route)
                self.assertEqual([(r['url'], r['status'], r['httpCode']) for r in body['results']],
                                 [(u, 'HEALTHY', 200) for u in urls])


class HealthSyncTests(_LinkRoutes):

    def rows(self):
        conn = govos.get_db_connection()
        out = {r['url'] for r in conn.execute('SELECT url FROM resource_link_health').fetchall()}
        conn.close()
        return out

    def test_only_valid_urls_are_registered(self):
        self.counted()
        self.post('health/sync', ['https://www.example.org/a', 'https://www.example.org:8443/b', 'http://10.0.0.1/',
                                  'http://localhost/', 'https://www.example.org/' + 'x' * 3000])
        self.assertEqual(self.rows(), {'https://www.example.org/a'})

    def test_registration_stops_at_the_tracked_limit(self):
        self.counted()
        with mock.patch.object(govos, 'LINK_MAX_TRACKED', 3):
            self.post('health/sync', [f'https://www.example.org/{i}' for i in range(10)])
        self.assertEqual(len(self.rows()), 3)

    def test_registering_spends_the_outbound_budget(self):
        stub = self.counted()
        govos._LINK_BUDGET = govos._OutboundBudget(2)
        status, body, _ = self.post('health/sync', [f'https://www.example.org/{i}' for i in range(5)])
        time.sleep(0.3)
        self.assertEqual(status, 200)
        self.assertEqual(stub.urls, [], 'the background check ran beyond the budget')
        self.assertEqual(len(self.rows()), 5)        # registered; the hourly sweep will check them


class ChannelUploadsTests(_LinkRoutes):

    def setUp(self):
        super().setUp()
        self.asked = []
        patch = mock.patch.object(govos, '_channel_uploads_cached', lambda ids, **kw: self.asked.append(list(ids)) or {})
        patch.start()
        self.addCleanup(patch.stop)

    def get(self, ids):
        r = self.client.get('/api/resources/live/channel-uploads', query_string={'ids': ','.join(ids)})
        return r.status_code, r.get_json()

    def test_only_real_channel_ids_are_fetched(self):
        good = 'UC' + 'a' * 22
        self.get([good, 'UCjunk', 'UC' + 'b' * 40, 'UC' + 'c' * 21 + '!', good])
        self.assertEqual(self.asked, [[good]])

    def test_too_many_channels_is_refused(self):
        status, body = self.get(['UC' + str(i).zfill(22) for i in range(17)])
        self.assertEqual((status, body['error']), (413, 'TOO_MANY_CHANNELS'))
        self.assertEqual(self.asked, [])

    def test_channel_requests_are_rate_limited(self):
        for _ in range(govos.LINK_RATE['channels']):
            self.assertEqual(self.get(['UC' + 'a' * 22])[0], 200)
        self.assertEqual(self.get(['UC' + 'a' * 22])[0], 429)


# --------------------------------------------------------------------------- 4. a real response body is never read
class ResponseSizeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        cls.sent = []

        class Huge(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-Length', str(10 * 1024 ** 3))   # claims 10 GB
                self.end_headers()
                total = 0
                try:
                    for _ in range(4096):                                   # streams up to 4 GB if read
                        self.wfile.write(b'\0' * (1024 * 1024))
                        total += 1024 * 1024
                except OSError:
                    pass
                cls.sent.append(total)

            do_HEAD = do_GET

            def log_message(self, *a):
                pass
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Huge)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f'http://127.0.0.1:{cls.server.server_address[1]}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def test_a_huge_response_is_not_read(self):
        offline_dns(self)
        patch, _ = public_host('127.0.0.1')
        started = time.time()
        with patch, fixture_origin(self.base):
            got = govos._check_one_link(self.base + '/big')
        took = time.time() - started
        time.sleep(0.5)
        self.assertEqual((got['status'], got['httpCode']), ('HEALTHY', 200))
        self.assertLess(took, 3)
        self.assertTrue(self.sent and max(self.sent) < 64 * 1024 * 1024, f'server pushed {self.sent} bytes before the close')


# --------------------------------------------------------------------------- 5. SSRF still holds through the routes
class SsrfThroughTheRoutesTests(_LinkRoutes):

    def test_every_refused_family_is_refused_by_every_route_without_a_request(self):
        families = {k: v for k, v in REFUSED.items() if k != 'unsupported scheme'}
        urls = [u for v in families.values() for u in v]
        self.assertLessEqual(len(urls), govos.LINK_MAX_URLS)
        with mock.patch.object(govos.urllib.request, 'build_opener', side_effect=AssertionError('a request was built')):
            for route in ('verify-links', 'health/recheck'):
                govos._recent_links.clear()
                status, body, _ = self.post(route, urls)
                self.assertEqual(status, 200, route)
                http = [u for u in urls if u.startswith(('http://', 'https://'))]
                self.assertEqual({r['url'] for r in body['results']}, set(dict.fromkeys(http)))
                for r in body['results']:
                    self.assertEqual((r['status'], r['httpCode']), ('UNREACHABLE', 0), r)
                    self.assertTrue(r.get('refused'), r)

    def test_a_host_name_that_resolves_to_a_private_address_is_refused(self):
        real = socket.getaddrinfo

        def resolver(host, *a, **kw):
            if host == 'intranet.example.org':
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('10.0.0.5', 0))]
            if host == 'metadata.example.org':
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('169.254.169.254', 0))]
            return real(host, *a, **kw)
        with mock.patch.object(socket, 'getaddrinfo', resolver), \
                mock.patch.object(govos.urllib.request, 'build_opener', side_effect=AssertionError('a request was built')):
            status, body, _ = self.post('verify-links', ['https://intranet.example.org/', 'http://metadata.example.org/latest'])
        self.assertEqual(status, 200)
        self.assertEqual({r['refused'] for r in body['results']}, {'host resolves to a private or reserved address'})

    def test_registration_never_stores_a_refused_address(self):
        self.counted()
        self.post('health/sync', [u for v in REFUSED.values() for u in v if u.startswith(('http://', 'https://'))][:60])
        conn = govos.get_db_connection()
        n = conn.execute('SELECT COUNT(*) FROM resource_link_health').fetchone()[0]
        conn.close()
        # Syntax-refused addresses are never registered; a host name that only fails DNS may be (it costs a
        # refused lookup per sweep, never a connection to a private address).
        self.assertLessEqual(n, 3)


if __name__ == '__main__':
    unittest.main()
