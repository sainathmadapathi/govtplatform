"""Live resources: feeds served from their cache without making a request wait on the upstream, and
a link checker that reaches only the public internet.

A stale copy is served at once and refreshed behind it; one upstream fetch runs per feed at a time;
a failed upstream is not retried by every request. The link checker answers any caller, so it refuses
private, loopback and non-http addresses, on the first hop and on every redirect. No network: the
fetchers are stand-ins and every refused address is refused before a connection is made.

Run: python -m pytest test_live_resources.py -q
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from unittest import mock

import app as govos


class _ThreadingProxy:
    """app's `threading`, except that every Thread it starts is recorded, so a test can wait for them."""

    def __init__(self, started):
        real, record = threading, started.append

        class Thread(real.Thread):
            def start(self):
                record(self)
                super().start()
        self.Thread = Thread

    def __getattr__(self, name):
        return getattr(threading, name)


class _TempDb(unittest.TestCase):
    """Every test on its own temporary database: govos.db is never touched.

    The routes start background work (a new URL's health check, a stale feed's refresh) on their own threads.
    Each one the test started is joined before the real database path is put back: a thread that outlived
    its test used to write its result into govos.db."""

    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        self._orig_db = govos.DB_FILE
        govos.DB_FILE = self.path
        govos.init_database()
        govos._feed_failures.clear()
        self.calls = 0
        self._started = []
        self._threading = mock.patch.object(govos, 'threading', _ThreadingProxy(self._started))
        self._threading.start()

    def tearDown(self):
        self._threading.stop()
        for t in self._started:
            t.join(timeout=15)
        self.assertFalse([t.name for t in self._started if t.is_alive()], 'a background thread outlived its test')
        govos.DB_FILE = self._orig_db
        govos._feed_failures.clear()
        try:
            os.remove(self.path)
        except OSError:
            pass

class FeedCacheTests(_TempDb):

    def fetch(self, items=('a',), delay=0.0, fail=False):
        def run(previous):
            self.calls += 1
            if delay:
                time.sleep(delay)
            if fail:
                raise OSError('upstream down')
            return list(items)
        return run

    def make_stale(self, key, payload):
        govos._cache_put(key, payload)
        conn = govos.get_db_connection()
        conn.execute('UPDATE live_feed_cache SET fetched_at = ? WHERE cache_key = ?', ('2000-01-01T00:00:00', key))
        conn.commit()
        conn.close()

    def test_a_fresh_copy_is_served_without_fetching(self):
        govos._cache_put('feed', ['old'])
        got = govos._feed_cached('feed', self.fetch())
        self.assertEqual((got['payload'], self.calls), (['old'], 0))

    def test_a_stale_copy_is_served_at_once_and_refreshed_behind_it(self):
        self.make_stale('feed', ['old'])
        started = time.time()
        got = govos._feed_cached('feed', self.fetch(items=('new',), delay=0.5))
        self.assertLess(time.time() - started, 0.4, 'the request waited on the upstream')
        self.assertEqual((got['payload'], got['stale']), (['old'], True))
        for _ in range(50):
            if govos._cache_get('feed', govos.FEED_MAX_AGE_SECONDS)['payload'] == ['new']:
                break
            time.sleep(0.05)
        self.assertEqual(govos._cache_get('feed', govos.FEED_MAX_AGE_SECONDS)['payload'], ['new'])
        self.assertEqual(self.calls, 1)

    def test_concurrent_first_reads_share_one_fetch(self):
        out = []
        fetch = self.fetch(items=('x',), delay=0.3)
        threads = [threading.Thread(target=lambda: out.append(govos._feed_cached('feed', fetch))) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(self.calls, 1)
        self.assertTrue(all(o['payload'] == ['x'] for o in out), out)

    def test_a_failed_upstream_is_not_retried_by_every_request(self):
        first = govos._feed_cached('feed', self.fetch(fail=True))
        self.assertEqual((first['payload'], first['stale']), ([], True))
        self.assertIn('upstream down', first['error'])
        again = govos._feed_cached('feed', self.fetch(fail=True))
        self.assertEqual(self.calls, 1)
        self.assertIn('upstream down', again['error'])
        # ... and a last good copy keeps being served, saying its refresh failed.
        self.make_stale('kept', ['good'])
        govos._feed_failures['kept'] = (time.time(), 'upstream down')
        kept = govos._feed_cached('kept', self.fetch())
        self.assertEqual((kept['payload'], self.calls), (['good'], 1))
        self.assertIn('refresh failed', kept['error'])

    def test_a_forced_refresh_of_a_fresh_copy_does_not_hammer_the_upstream(self):
        govos._cache_put('feed', ['old'])
        got = govos._feed_cached('feed', self.fetch(items=('new',)), force=True)
        self.assertEqual((got['payload'], self.calls), (['old'], 0))

    # ------------------------------------------------- failure under concurrent load: shared, bounded
    def concurrently(self, n, fn):
        out, lat = [], []

        def one():
            t = time.time()
            out.append(fn())
            lat.append(time.time() - t)
        threads = [threading.Thread(target=one) for _ in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return out, max(lat)

    def test_concurrent_stale_requests_are_served_at_once_with_one_refresh_behind_them(self):
        self.make_stale('feed', ['old'])
        out, slowest = self.concurrently(6, lambda: govos._feed_cached('feed', self.fetch(items=('new',), delay=0.4)))
        self.assertTrue(all(o['payload'] == ['old'] and o['stale'] for o in out))
        self.assertLess(slowest, 0.3, 'a request waited on the upstream')
        for _ in range(40):
            if govos._cache_get('feed', govos.FEED_MAX_AGE_SECONDS)['payload'] == ['new']:
                break
            time.sleep(0.05)
        self.assertEqual(self.calls, 1)

    def test_with_nothing_cached_and_the_upstream_down_waiting_requests_share_one_failed_fetch(self):
        # They used to queue on a lock and fetch again one after another: up to 60 s + 25 s each.
        out, slowest = self.concurrently(6, lambda: govos._feed_cached('feed', self.fetch(delay=0.5, fail=True)))
        self.assertEqual(self.calls, 1, 'every waiting request fetched the failing upstream again')
        self.assertLess(slowest, 1.2, f'the slowest request took {slowest:.2f}s: bounded by one fetch')
        for o in out:
            self.assertEqual((o['payload'], o['stale']), ([], True))
            self.assertIn('upstream down', o['error'])
        # ... and the requests after it are inside the back-off: answered at once, no fetch.
        t = time.time()
        later = govos._feed_cached('feed', self.fetch(fail=True))
        self.assertLess(time.time() - t, 0.1)
        self.assertEqual((self.calls, later['payload']), (1, []))

    def test_stale_data_stays_available_after_a_failed_refresh(self):
        self.make_stale('feed', ['good'])
        got = govos._feed_cached('feed', self.fetch(fail=True), in_request=False)
        self.assertEqual((got['payload'], got['stale']), (['good'], True))
        self.assertIn('refresh failed', got['error'])
        self.assertEqual(govos._cache_get('feed', govos.FEED_MAX_AGE_SECONDS)['payload'], ['good'])
        again = govos._feed_cached('feed', self.fetch(fail=True))
        self.assertEqual((again['payload'], self.calls), (['good'], 1))

    def test_the_feed_recovers_once_the_back_off_is_over(self):
        govos._feed_cached('feed', self.fetch(fail=True))
        self.assertIn('feed', govos._feed_failures)
        failed_at, error = govos._feed_failures['feed']
        govos._feed_failures['feed'] = (failed_at - govos.FEED_RETRY_AFTER_FAILURE_SECONDS - 1, error)
        got = govos._feed_cached('feed', self.fetch(items=('back',)))
        self.assertEqual((got['payload'], got['stale'], got['error']), (['back'], False, None))
        self.assertNotIn('feed', govos._feed_failures)
        self.assertEqual(self.calls, 2)

    def test_a_forced_refresh_still_fetches_through_the_back_off_and_concurrent_ones_share_it(self):
        govos._feed_cached('feed', self.fetch(fail=True))
        self.assertEqual(self.calls, 1)
        out, _ = self.concurrently(4, lambda: govos._feed_cached('feed', self.fetch(items=('forced',), delay=0.3),
                                                                 force=True))
        self.assertEqual(self.calls, 2, 'concurrent forced refreshes each fetched')
        self.assertTrue(all(o['payload'] == ['forced'] for o in out))
        self.assertNotIn('feed', govos._feed_failures)

    def test_expired_failures_are_dropped_so_the_table_stays_bounded(self):
        govos._feed_failures['old-feed'] = (time.time() - govos.FEED_RETRY_AFTER_FAILURE_SECONDS - 1, 'x')
        govos._feed_cached('feed', self.fetch(fail=True))
        self.assertEqual(set(govos._feed_failures), {'feed'})

    def test_the_background_loop_fetches_a_stale_copy_now(self):
        self.make_stale('feed', ['old'])
        got = govos._feed_cached('feed', self.fetch(items=('new',)), in_request=False)
        self.assertEqual((got['payload'], got['stale'], self.calls), (['new'], False, 1))



class RequestLimitTests(_TempDb):

    def test_a_non_numeric_limit_is_not_a_server_error(self):
        orig = govos._fetch_ssc_notices
        govos._fetch_ssc_notices = lambda: [{'id': 1, 'headline': 'CGL notice', 'createdAt': '2026-09-01', 'files': [], 'isCgl': True}]
        try:
            r = govos.app.test_client().get('/api/resources/live/ssc-notices?limit=abc')
        finally:
            govos._fetch_ssc_notices = orig
        self.assertEqual(r.status_code, 200)

    def test_an_oversized_body_is_refused_before_it_is_read(self):
        r = govos.app.test_client().post('/api/sqlite/sync-all', data=b'x' * (17 * 1024 * 1024),
                                         content_type='application/json')
        self.assertEqual(r.status_code, 413)


#: Every class of address the link checker must refuse before it builds a request, by family.
REFUSED = {
    'malformed hostname': ['http://a..com/', 'http://' + 'a' * 64 + '.com/', 'http://-/'],
    'malformed syntax': ['http://[x/', 'http://[::1/', 'http://[fe80::1%zz]/'],
    'missing hostname': ['http://', 'http:///path', 'https://:443/'],
    'unsupported scheme': ['file:///etc/passwd', 'gopher://example.org/', 'ftp://example.org/', 'javascript:alert(1)'],
    'private IPv4': ['http://10.0.0.1/', 'http://192.168.1.1/admin', 'http://172.16.0.1/'],
    'loopback': ['http://127.0.0.1:5000/api/sqlite/status', 'http://localhost/', 'http://[::1]/', 'http://0.0.0.0/'],
    'link-local': ['http://169.254.169.254/latest/meta-data', 'http://[fe80::1]/'],
    'CGNAT': ['http://100.64.0.1/'],
    'IPv4-mapped': ['http://[::ffff:127.0.0.1]/', 'http://[::ffff:10.0.0.1]/', 'http://[::ffff:7f00:1]/'],
    'decimal/octal/short IP': ['http://2130706433/', 'http://017700000001/', 'http://0x7f.0.0.1/', 'http://127.1/'],
}
MALFORMED = REFUSED['malformed hostname'] + REFUSED['malformed syntax']


def _ok_response(url, code=200):
    """A stand-in for an opener's response: the public-URL path is exercised with no network."""
    class Resp:
        def getcode(self):
            return code

        def geturl(self):
            return url

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False
    return Resp()


_REAL_GETADDRINFO = socket.getaddrinfo


def _offline_getaddrinfo(host, port=None, *args, **kwargs):
    """The system resolver without DNS. A numeric host (dotted, decimal, hex, octal, short, IPv6) is
    parsed exactly as the system parses it, so "2130706433" resolves to 127.0.0.1 here as it would for
    real; localhost resolves to loopback; any other name would need a DNS query, which a test must not
    make, so it does not resolve. A name is encoded first, as the real resolver does: a malformed one
    ("a..com", a label over 63 letters) raises UnicodeError here exactly as it does there."""
    try:
        return _REAL_GETADDRINFO(host, port, *args, **{**kwargs, 'flags': socket.AI_NUMERICHOST})
    except socket.gaierror:
        pass
    if str(host).rstrip('.').lower() == 'localhost':
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', port or 0))]
    str(host).encode('idna')
    raise socket.gaierror(socket.EAI_NONAME, 'does not resolve (no DNS in tests)')


def offline_dns(test):
    """Install the DNS-free resolver for one test."""
    patch = mock.patch.object(socket, 'getaddrinfo', _offline_getaddrinfo)
    patch.start()
    test.addCleanup(patch.stop)


class _StubOpener:
    def open(self, req, timeout=None):
        return _ok_response(req.full_url)


def fixture_origin(origin):
    """Let exactly `origin` (a stand-in site on this machine, e.g. http://127.0.0.1:53211) past the URL rule's
    IP-literal and port checks; every other URL -- every redirect target included -- meets the real rule."""
    from tools.claude_cli import discovery
    real = discovery.validate_url_syntax

    def rule(url):
        return (True, '') if isinstance(url, str) and url.startswith(origin + '/') else real(url)
    return mock.patch.object(discovery, 'validate_url_syntax', rule)


def public_host(*hosts):
    """Treat `hosts` as public (a stand-in for a real public site); every other host gets the real check."""
    from tools.claude_cli import discovery
    real = discovery.resolves_public
    asked = []

    def resolver(host, resolver=None):
        asked.append(host)
        return (True, '') if host in hosts else real(host, resolver)
    return mock.patch.object(discovery, 'resolves_public', resolver), asked


class LinkCheckTests(unittest.TestCase):
    """The checker answers any caller: it must refuse every non-public address before a request is
    built, and a malformed one must be refused too -- never raise."""

    def setUp(self):
        offline_dns(self)

    def test_every_refused_address_is_refused_before_any_request_and_never_raises(self):
        with mock.patch.object(govos.urllib.request, 'build_opener', side_effect=AssertionError('a request was built')):
            for family, urls in REFUSED.items():
                for url in urls:
                    with self.subTest(family=family, url=url):
                        got = govos._check_one_link(url)                 # must not raise
                        self.assertEqual((got['status'], got['httpCode']), ('UNREACHABLE', 0))
                        self.assertTrue(got.get('refused'))
                        self.assertEqual(got['url'], url)

    def test_decimal_octal_and_short_forms_are_refused_because_they_are_loopback(self):
        # The system parses these to 127.0.0.1. The link checker now applies GovOS's one URL rule
        # (validate_url_syntax) first, which refuses an IP literal or legacy IPv4 form before any DNS
        # lookup; and were that rule ever bypassed, the resolver check would still refuse each of them
        # as what it resolves to.
        from tools.claude_cli.discovery import resolves_public
        syntax_refusals = ('URL names an IP address, not a host name', 'URL has no public host name')
        with mock.patch.object(govos.urllib.request, 'build_opener', side_effect=AssertionError('a request was built')):
            for url in REFUSED['decimal/octal/short IP'] + REFUSED['IPv4-mapped'][:1]:
                with self.subTest(url=url):
                    self.assertIn(govos._check_one_link(url)['refused'], syntax_refusals)
                    host = urllib.parse.urlparse(url).hostname
                    self.assertEqual(resolves_public(host), (False, 'host resolves to a private or reserved address'))

    def test_a_malformed_address_is_named_as_invalid_not_as_private(self):
        for url in ('http://a..com/', 'http://[x/'):
            refused = govos._check_one_link(url)['refused']
            self.assertTrue(refused.startswith('not a valid web address') or refused == 'URL is malformed', refused)
        ok, why = govos._public_link('http://a..com/')
        self.assertEqual((ok, why.startswith('not a valid web address')), (False, True))

    def test_a_public_address_is_still_checked(self):
        patch, asked = public_host('portal.example.gov.in')
        with patch, mock.patch.object(govos.urllib.request, 'build_opener', return_value=_StubOpener()):
            got = govos._check_one_link('https://portal.example.gov.in/notice')
        self.assertEqual((got['status'], got['httpCode']), ('HEALTHY', 200))
        self.assertNotIn('refused', got)
        self.assertEqual(asked, ['portal.example.gov.in'])

    def test_a_redirect_handler_refuses_private_and_malformed_targets(self):
        req = urllib.request.Request('https://example.org/')
        for target in ('http://127.0.0.1/secret', 'http://[::ffff:10.0.0.1]/', 'http://a..com/', 'file:///etc/passwd'):
            with self.subTest(target=target), self.assertRaises(urllib.error.URLError):
                govos._PublicRedirects().redirect_request(req, None, 302, 'Found', {}, target)


class RedirectThroughTheCheckerTests(unittest.TestCase):
    """Redirects through the checker's own opener: a stand-in site on this machine, treated as public,
    redirects to a private, an IPv4-mapped or a malformed address, and to itself."""

    @classmethod
    def setUpClass(cls):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        cls.hits = []

        class Site(BaseHTTPRequestHandler):
            def _answer(self):
                cls.hits.append((self.command, self.path))
                targets = {'/to-private': 'http://10.0.0.1/secret', '/to-mapped': 'http://[::ffff:192.168.1.1]/',
                           '/to-malformed': 'http://a..com/', '/to-self': '/ok'}
                if self.path in targets:
                    self.send_response(302)
                    self.send_header('Location', targets[self.path])
                else:
                    self.send_response(200)
                self.send_header('Content-Length', '0')
                self.end_headers()
            do_HEAD = do_GET = _answer

            def log_message(self, *a):
                pass

        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Site)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f'http://127.0.0.1:{cls.server.server_address[1]}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        offline_dns(self)

    def check(self, path):
        patch, asked = public_host('127.0.0.1')
        started = time.time()
        with patch, fixture_origin(self.base):
            got = govos._check_one_link(self.base + path)
        return got, asked, time.time() - started

    def test_a_redirect_to_a_private_or_malformed_address_is_not_followed(self):
        # Each target is refused on the redirect hop by the real rules -- the URL rule (an IP literal) or
        # the resolver -- and never connected to.
        for path in ('/to-private', '/to-mapped', '/to-malformed'):
            with self.subTest(path=path):
                got, asked, took = self.check(path)
                self.assertEqual((got['status'], got['httpCode']), ('UNREACHABLE', 0))
                self.assertLess(took, 5, 'the private target was connected to (a timeout), not refused')
                self.assertIn(('GET', path), self.hits)

    def test_a_redirect_to_a_public_address_is_followed(self):
        got, asked, _ = self.check('/to-self')
        self.assertEqual((got['status'], got['httpCode']), ('HEALTHY', 200))
        self.assertIn(('GET', '/ok'), self.hits)      # urllib follows a 302 with a GET, whatever the first method


class LinkBatchTests(_TempDb):
    """One malformed URL must not stop the rest of a batch -- in the routes or in the scheduled sweep."""

    BATCH = ['http://a..com/', 'https://portal.example.gov.in/notice', 'http://[x/', 'http://10.0.0.1/',
             'https://portal.example.gov.in/syllabus']

    def setUp(self):
        super().setUp()
        offline_dns(self)

    def run_stubbed(self, fn):
        patch, _ = public_host('portal.example.gov.in')
        with patch, mock.patch.object(govos.urllib.request, 'build_opener', return_value=_StubOpener()):
            return fn()

    def stored(self):
        conn = govos.get_db_connection()
        rows = {r['url']: (r['status'], r['checked_at']) for r in
                conn.execute('SELECT url, status, checked_at FROM resource_link_health').fetchall()}
        conn.close()
        return rows

    def test_a_batch_with_malformed_urls_checks_and_stores_every_url(self):
        self.assertTrue(self.run_stubbed(lambda: govos._recheck_links(self.BATCH)))
        rows = self.stored()
        self.assertEqual(set(rows), set(self.BATCH))
        self.assertEqual(rows['https://portal.example.gov.in/notice'][0], 'HEALTHY')
        self.assertEqual(rows['https://portal.example.gov.in/syllabus'][0], 'HEALTHY')
        for url in ('http://a..com/', 'http://[x/', 'http://10.0.0.1/'):
            self.assertEqual(rows[url][0], 'UNREACHABLE', url)

    def test_the_routes_answer_every_url_even_with_a_malformed_one(self):
        client = govos.app.test_client()
        for route in ('/api/resources/verify-links', '/api/resources/health/recheck'):
            with self.subTest(route=route):
                r = self.run_stubbed(lambda: client.post(route, json={'urls': self.BATCH}))
                self.assertEqual(r.status_code, 200, r.get_data(as_text=True)[:200])
                results = {x['url']: x['status'] for x in r.get_json()['results']}
                self.assertEqual(set(results), set(self.BATCH))
                self.assertEqual(results['https://portal.example.gov.in/notice'], 'HEALTHY')
                self.assertEqual(results['http://a..com/'], 'UNREACHABLE')

    def test_the_scheduled_sweep_completes_with_a_malformed_url_registered(self):
        # As health/sync registers them: pending rows, never checked -- then the hourly loop's own step.
        conn = govos.get_db_connection()
        for u in self.BATCH:
            conn.execute('INSERT INTO resource_link_health (url, status, http_code, checked_at) VALUES (?, ?, ?, ?)',
                         (u, 'PENDING', 0, None))
        conn.commit()
        conn.close()
        due = govos._health_due()
        self.assertEqual(set(due), set(self.BATCH))
        self.assertTrue(self.run_stubbed(lambda: govos._recheck_links(due[:80])))
        self.assertTrue(all(checked for _, checked in self.stored().values()))
        self.assertEqual(govos._health_due(), [], 'every URL, the malformed ones too, was checked and is not due again')


if __name__ == '__main__':
    unittest.main()
