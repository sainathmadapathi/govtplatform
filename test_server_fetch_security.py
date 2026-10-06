"""Every server-side fetch of an external document goes through the one guarded fetch, once.

Research extraction used to check a finding's URL with `fetch_checked`, throw the body away, and hand the
URL to the document loader -- which fetched it a second time with TLS certificate checks switched off,
urllib's redirect handler following any Location (a private address, ftp:), and no size limit. The builder's
own fetch (`exam_authoring.sources.fetch`, behind every load_html / load_pdf / load_document) was that same
unguarded fetch. Now:

  * research extraction fetches once and parses the bytes it got (`request_count == 1`);
  * the builder's fetch IS the guarded fetch: every hop validated and resolved to a public address before
    connecting, TLS verified, size and time bounded, no file: or scheme-less URL read from disk.

Real local servers stand in for the web: a "public" site (let past the URL rule and the resolver for its
exact origin only, as test_live_resources does), a "private" target whose hit count must stay zero, and
HTTPS servers with certificates from a CA minted per run (valid, self-signed, wrong host name).

Run: python -m pytest test_server_fetch_security.py -q
"""
from __future__ import annotations

import datetime
import os
import socket
import ssl
import tempfile
import threading
import time
import types
import unittest
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

import app as govos
from test_live_resources import fixture_origin, public_host
from tools.claude_cli import discovery
from tools.exam_authoring import sources

MB = 1024 * 1024
#: `sources`' view of the clock with sleeps skipped, so retries are instant. Patching time.sleep itself would
#: also stop the stand-in servers from trickling, which is what the timeout tests depend on.
_NO_WAIT = types.SimpleNamespace(sleep=lambda s: None, time=time.time, strftime=time.strftime, monotonic=time.monotonic)
TEXT = 'Staff Selection Commission Combined Graduate Level Examination 2026: last date for applications 25-06-2026.'
# A text layer long enough that the builder's scan heuristic (under 200 characters a page) reads it as text.
PDF_LINES = [TEXT, 'Para 13.8: Tier-I is a computer based examination of four parts, each of 25 questions.',
             'Para 16.1: minimum qualifying marks are UR 30 per cent, OBC and EWS 25 per cent, others 20 per cent.']


def text_pdf() -> bytes:
    content = zlib.compress(b'BT /F1 11 Tf ' + b' '.join(b'1 0 0 1 40 %d Tm (%s) Tj' % (700 - 20 * i, l.encode()) for i, l in enumerate(PDF_LINES)) + b' ET')
    objs = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
            b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>',
            b'<< /Length %d /Filter /FlateDecode >>\nstream\n' % len(content) + content + b'\nendstream']
    out, offs = b'%PDF-1.4\n', []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += b'%d 0 obj\n' % i + o + b'\nendobj\n'
    x = len(out)
    out += b'xref\n0 5\n0000000000 65535 f \n' + b''.join(b'%010d 00000 n \n' % o for o in offs)
    return out + b'trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % x


class _Site:
    """A local HTTP(S) server that counts every request by path."""

    def __init__(self, routes, tls_context=None):
        self.hits: dict = {}
        site = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                site.hits[self.path] = site.hits.get(self.path, 0) + 1
                route = routes.get(self.path)
                if route is None:
                    self.send_response(404)
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return
                route(self)

            do_HEAD = do_GET

            def log_message(self, *a):
                pass

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        if tls_context is not None:
            self.server.socket = tls_context.wrap_socket(self.server.socket, server_side=True)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.port = self.server.server_address[1]

    def total(self):
        return sum(self.hits.values())

    def close(self):
        self.server.shutdown()


def body(data: bytes, ctype: str):
    def answer(h):
        h.send_response(200)
        h.send_header('Content-Type', ctype)
        h.send_header('Content-Length', str(len(data)))
        h.end_headers()
        h.wfile.write(data)
    return answer


def redirect(location: str):
    def answer(h):
        h.send_response(302)
        h.send_header('Location', location)
        h.send_header('Content-Length', '0')
        h.end_headers()
    return answer


def stream(total: int, ctype='application/pdf'):
    def answer(h):
        h.send_response(200)
        h.send_header('Content-Type', ctype)
        h.send_header('Content-Length', str(total))
        h.end_headers()
        try:
            sent = 0
            while sent < total:
                h.wfile.write(b'%PDF-' if sent == 0 else b'\0' * min(MB, total - sent))
                sent += 5 if sent == 0 else min(MB, total - sent)
        except OSError:
            pass
    return answer


def drip(h):
    h.send_response(200)
    h.send_header('Content-Type', 'text/html')
    h.send_header('Content-Length', '100000')
    h.end_headers()
    try:
        for _ in range(100):
            h.wfile.write(b'<p>')
            h.wfile.flush()
            time.sleep(0.2)
    except OSError:
        pass


class _Fixture(unittest.TestCase):
    """A public stand-in site and a private target, for every test; the builder cache in a temp dir."""

    def setUp(self):
        self.private = _Site({'/secret': body(b'PRIVATE', 'text/plain')})
        pdf = text_pdf()
        html = ('<html><body><h1>Notice</h1><p>' + TEXT + '</p><img src="/tracker"><a href="/tracker">x</a>'
                '<iframe src="/tracker"></iframe></body></html>').encode()
        self.pdf, self.html = pdf, html
        self.site = _Site({
            '/notice.html': body(html, 'text/html; charset=utf-8'),
            '/notice.pdf': body(pdf, 'application/pdf'),
            '/viewer': body(pdf, 'application/octet-stream'),          # a PDF behind a route with no extension
            '/archive.zip': body(b'PK\x03\x04' + b'\0' * 64, 'application/zip'),
            '/broken.pdf': body(b'%PDF-1.7\nthis is not a PDF at all', 'application/pdf'),
            '/to-notice': redirect('/notice.html'),
            '/to-loopback': redirect(f'http://127.0.0.1:{self.private.port}/secret'),
            '/to-localhost': redirect(f'http://localhost:{self.private.port}/secret'),
            '/to-private': redirect('http://10.0.0.5/secret'),
            '/to-metadata': redirect('http://169.254.169.254/latest/meta-data'),
            '/to-mapped': redirect('http://[::ffff:127.0.0.1]/secret'),
            '/to-dns-private': redirect('http://intranet.example.org/secret'),
            '/to-file': redirect('file:///C:/Windows/win.ini'),
            '/to-ftp': redirect('ftp://example.org/x'),
            '/loop': redirect('/loop'),
            '/big': stream(3 * MB),
            '/slow': drip,
            '/tracker': body(b'tracked', 'text/plain'),
        })
        self.base = f'http://127.0.0.1:{self.site.port}'
        cache = tempfile.mkdtemp()
        for patch in (mock.patch.object(sources, 'CACHE_DIR', cache), fixture_origin(self.base)):
            patch.start()
            self.addCleanup(patch.stop)
        patch, self.asked = public_host('127.0.0.1')
        patch.start()
        self.addCleanup(patch.stop)
        real = socket.getaddrinfo

        def resolver(host, *a, **kw):                     # no real DNS: two names that resolve privately
            table = {'intranet.example.org': '10.0.0.9', 'metadata.example.org': '169.254.169.254'}
            if host in table:
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (table[host], 0))]
            return real(host, *a, **kw)
        patch = mock.patch.object(socket, 'getaddrinfo', resolver)
        patch.start()
        self.addCleanup(patch.stop)

    def tearDown(self):
        self.site.close()
        self.private.close()


# --------------------------------------------------------------------------- research extraction
class ResearchExtractTests(_Fixture):

    def extract(self, path):
        return govos._fetch_source_text(self.base + path)

    def test_1_a_public_page_is_fetched_exactly_once(self):
        text, failure, reason = self.extract('/notice.html')
        self.assertEqual((failure, reason), (None, None))
        self.assertIn('25-06-2026', text)
        self.assertEqual(self.site.hits.get('/notice.html'), 1, 'request_count must be 1')
        self.assertEqual(self.site.total(), 1)

    def test_1b_a_pdf_is_fetched_exactly_once_and_read(self):
        text, failure, _ = self.extract('/notice.pdf')
        self.assertIsNone(failure)
        self.assertIn('Combined Graduate Level', text)
        self.assertEqual(self.site.total(), 1)

    def test_2_the_parser_receives_the_fetched_bytes_and_the_url_is_never_loaded(self):
        seen = []
        real = sources.document_from_bytes
        with mock.patch.object(sources, 'document_from_bytes', lambda url, data: seen.append(data) or real(url, data)), \
                mock.patch.object(sources, 'fetch', side_effect=AssertionError('second fetch')), \
                mock.patch.object(sources, 'load_document', side_effect=AssertionError('second fetch')):
            text, failure, _ = self.extract('/viewer')
        self.assertIsNone(failure)
        self.assertEqual(seen, [self.pdf])
        self.assertEqual(self.site.hits, {'/viewer': 1})

    def test_3_parsing_cannot_make_another_request(self):
        self.extract('/notice.html')                    # the page links, embeds and frames /tracker
        self.assertNotIn('/tracker', self.site.hits)
        self.assertEqual(self.site.total(), 1)

    def test_4_a_redirect_to_a_private_or_loopback_address_is_stopped_before_it_connects(self):
        for path in ('/to-loopback', '/to-localhost', '/to-private', '/to-metadata', '/to-mapped'):
            with self.subTest(path=path):
                text, failure, reason = self.extract(path)
                self.assertEqual((text, failure), (None, 'SOURCE_FETCH_FAILURE'))
                self.assertIn('blocked hop', reason)
        self.assertEqual(self.private.total(), 0, 'the private target was contacted')

    def test_5_a_redirect_to_a_name_that_resolves_privately_is_stopped(self):
        text, failure, reason = self.extract('/to-dns-private')
        self.assertEqual((failure, reason), ('SOURCE_FETCH_FAILURE', 'blocked hop: host resolves to a private or reserved address'))

    def test_5b_unsupported_schemes_excessive_redirects_and_malformed_urls_are_refused(self):
        for path, words in (('/to-file', 'blocked hop'), ('/to-ftp', 'blocked hop'), ('/loop', 'too many redirects')):
            with self.subTest(path=path):
                self.assertIn(words, self.extract(path)[2])
        for url in ('file:///C:/Windows/win.ini', 'ftp://example.org/x', 'http://[x/', 'http://2130706433/', 'http://127.1/',
                    'http://0x7f.0.0.1/', 'http://10.0.0.1/', 'http://100.64.0.1/', 'http://[::ffff:10.0.0.1]/'):
            with self.subTest(url=url):
                text, failure, reason = govos._fetch_source_text(url)
                self.assertEqual((text, failure), (None, 'SOURCE_FETCH_FAILURE'))
                self.assertIn('blocked hop', reason)

    def test_6_an_oversized_response_is_refused_and_not_parsed(self):
        with mock.patch.object(sources, 'SOURCE_MAX_BYTES', 1 * MB), \
                mock.patch.object(sources, 'document_from_bytes', side_effect=AssertionError('parsed')):
            text, failure, reason = self.extract('/big')
        self.assertEqual((text, failure), (None, 'SOURCE_FETCH_FAILURE'))
        self.assertIn('larger than 1 MB', reason)

    def test_7_a_malformed_or_unsupported_response_is_handled_cleanly(self):
        text, failure, reason = self.extract('/broken.pdf')
        self.assertEqual((text, failure), (None, 'SOURCE_FETCH_FAILURE'))
        self.assertIn('could not be read', reason)
        text, failure, reason = self.extract('/archive.zip')
        self.assertIn('not a PDF or a web page', reason)

    def test_8_a_download_that_trickles_is_stopped_by_its_deadline(self):
        started = time.time()
        with mock.patch.object(sources, 'SOURCE_MAX_SECONDS', 1.0):
            text, failure, reason = self.extract('/slow')
        self.assertLess(time.time() - started, 5)
        self.assertEqual((failure, reason), ('SOURCE_FETCH_FAILURE', 'download took too long'))

    def test_9_the_route_fetches_once_and_stores_the_text(self):
        govos.DB_FILE, original = tempfile.mkstemp(suffix='.db')[1], govos.DB_FILE
        try:
            govos.init_database()
            conn = govos.get_db_connection()
            run_id = conn.execute("INSERT INTO research_runs (query, mode) VALUES ('q', 'OFFICIAL')").lastrowid
            cur = conn.execute("INSERT INTO research_findings (run_id, title, url, trust_level) VALUES (?, 'Notice', ?, 'OFFICIAL')",
                               (run_id, self.base + '/notice.pdf'))
            fid = cur.lastrowid
            conn.commit()
            conn.close()
            r = govos.app.test_client().post('/api/research/extract', json={'finding_id': fid})
            self.assertEqual(r.status_code, 200, r.get_data(as_text=True)[:300])
            result = r.get_json()['results'][0]
            self.assertFalse(result.get('failed'), result)
            self.assertEqual(self.site.hits, {'/notice.pdf': 1})
        finally:
            govos.DB_FILE = original


# --------------------------------------------------------------------------- the builder's fetch
class BuilderFetchTests(_Fixture):

    def setUp(self):
        super().setUp()
        patch = mock.patch.object(sources, 'time', _NO_WAIT)       # retries without waiting (sources' own clock only)
        patch.start()
        self.addCleanup(patch.stop)

    def test_1_a_source_is_fetched_once_through_the_guarded_fetch(self):
        doc = sources.load_document(self.base + '/viewer', use_cache=False)
        self.assertEqual(doc.kind, 'PDF')
        self.assertIn('Combined Graduate Level', doc.all_text())
        self.assertEqual(self.site.hits, {'/viewer': 1}, 'load_document fetched once (it used to re-fetch via load_pdf)')

    def test_1b_a_normal_redirect_is_followed_and_http_still_works(self):
        doc = sources.load_html(self.base + '/to-notice', use_cache=False)
        self.assertIn('25-06-2026', doc.text)
        self.assertEqual(self.site.hits, {'/to-notice': 1, '/notice.html': 1})

    def test_3_no_certificate_check_is_switched_off_anywhere_in_the_fetch_path(self):
        for module in (sources, discovery):
            source = open(module.__file__, encoding='utf-8').read()
            for bypass in ('CERT_NONE', 'check_hostname = False', 'check_hostname=False', '_create_unverified_context',
                           'verify=False', 'urlopen('):
                self.assertNotIn(bypass, source, f'{module.__name__} contains {bypass}')

    def test_4_and_5_private_and_loopback_addresses_are_refused_without_connecting(self):
        for url in (f'http://127.0.0.1:{self.private.port}/secret', f'http://localhost:{self.private.port}/secret',
                    'http://10.0.0.5/x', 'http://192.168.1.10/x', 'http://169.254.169.254/latest', 'http://100.64.0.1/x',
                    'http://[::1]/x', 'http://[::ffff:127.0.0.1]/x', 'http://2130706433/x', 'http://127.1/x'):
            with self.subTest(url=url):
                with self.assertRaises(sources.FetchError) as ctx:
                    sources.fetch(url, use_cache=False)
                self.assertIn('blocked hop', str(ctx.exception))
                self.assertIn('1 attempt:', str(ctx.exception), 'a refused address is not retried')
        self.assertEqual(self.private.total(), 0)

    def test_5b_a_malformed_url_is_a_fetch_error_not_a_crash(self):
        for url in ('http://[x/', 'http://[::1/', 'https://exa mple.org/'):
            with self.subTest(url=url), self.assertRaises(sources.FetchError):
                sources.fetch(url, use_cache=False)

    def test_6_a_name_that_resolves_privately_is_refused(self):
        with self.assertRaises(sources.FetchError) as ctx:
            sources.fetch('https://intranet.example.org/notice.pdf', use_cache=False)
        self.assertIn('private or reserved address', str(ctx.exception))

    def test_7_a_redirect_to_a_private_address_is_refused_before_it_connects(self):
        for path in ('/to-loopback', '/to-private', '/to-dns-private', '/to-file', '/to-ftp'):
            with self.subTest(path=path), self.assertRaises(sources.FetchError) as ctx:
                sources.fetch(self.base + path, use_cache=False)
            self.assertIn('blocked hop', str(ctx.exception))
        self.assertEqual(self.private.total(), 0, 'the private target was contacted')

    def test_8_an_oversized_source_is_refused_whole(self):
        with mock.patch.object(sources, 'SOURCE_MAX_BYTES', 1 * MB), self.assertRaises(sources.FetchError) as ctx:
            sources.fetch(self.base + '/big', use_cache=False)
        self.assertIn('larger than 1 MB', str(ctx.exception))

    def test_9_a_trickling_source_times_out_cleanly_and_is_retried(self):
        with mock.patch.object(sources, 'SOURCE_MAX_SECONDS', 0.8), self.assertRaises(sources.FetchError) as ctx:
            sources.fetch(self.base + '/slow', use_cache=False)
        self.assertIn('download took too long', str(ctx.exception))
        self.assertEqual(self.site.hits.get('/slow'), sources._RETRIES, 'a timeout is retried, as a flaky host deserves')

    def test_a_file_or_scheme_less_path_is_never_read_from_disk(self):
        for url in ('file:///C:/Windows/win.ini', 'C:/Windows/win.ini', '/etc/passwd', 'win.ini', 'ftp://example.org/a'):
            with self.subTest(url=url), self.assertRaises(sources.FetchError):
                sources.fetch(url, use_cache=False)

    def test_only_what_the_guarded_fetch_returned_is_cached(self):
        sources.fetch(self.base + '/notice.html')
        sources.fetch(self.base + '/notice.html')                       # served from the cache
        self.assertEqual(self.site.hits, {'/notice.html': 1})
        names = os.listdir(sources.CACHE_DIR)
        self.assertTrue(names and all('.checked.' in n for n in names), names)


# --------------------------------------------------------------------------- TLS, with real certificates
def _certificates(directory):
    """A CA, a leaf it signs for the stand-in host, a leaf it signs for another host, and a self-signed leaf."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    now = datetime.datetime.now(datetime.timezone.utc)

    def name(cn):
        return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])

    def write(path, data):
        with open(path, 'wb') as fh:
            fh.write(data)
        return path

    def key_pem(key):
        return key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())

    ca_key = ec.generate_private_key(ec.SECP256R1())
    ca = (x509.CertificateBuilder().subject_name(name('GovOS test CA')).issuer_name(name('GovOS test CA'))
          .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
          .not_valid_before(now - datetime.timedelta(days=1)).not_valid_after(now + datetime.timedelta(days=2))
          .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True).sign(ca_key, hashes.SHA256()))

    def leaf(host, issuer_cert, issuer_key, self_signed=False):
        key = ec.generate_private_key(ec.SECP256R1())
        builder = (x509.CertificateBuilder().subject_name(name(host))
                   .issuer_name(name(host) if self_signed else issuer_cert.subject).public_key(key.public_key())
                   .serial_number(x509.random_serial_number()).not_valid_before(now - datetime.timedelta(days=1))
                   .not_valid_after(now + datetime.timedelta(days=2))
                   .add_extension(x509.SubjectAlternativeName([x509.DNSName(host)]), critical=False))
        cert = builder.sign(key if self_signed else issuer_key, hashes.SHA256())
        return (write(os.path.join(directory, f'{host}-{self_signed}.crt'), cert.public_bytes(serialization.Encoding.PEM)),
                write(os.path.join(directory, f'{host}-{self_signed}.key'), key_pem(key)))

    return {'ca': write(os.path.join(directory, 'ca.crt'), ca.public_bytes(serialization.Encoding.PEM)),
            'good': leaf('docs.fixture-authority.test', ca, ca_key),
            'wrong_host': leaf('someone-else.example', ca, ca_key),
            'self_signed': leaf('docs.fixture-authority.test', None, None, self_signed=True)}


try:
    import cryptography  # noqa: F401
    HAVE_CRYPTO = True
except ImportError:
    HAVE_CRYPTO = False


@unittest.skipUnless(HAVE_CRYPTO, 'the cryptography package is needed to mint test certificates')
class TlsTests(unittest.TestCase):
    HOST = 'docs.fixture-authority.test'

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp()
        cls.certs = _certificates(cls.dir)
        cls.sites = {}
        for kind in ('good', 'wrong_host', 'self_signed'):
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(*cls.certs[kind])
            cls.sites[kind] = _Site({'/notice.html': body(f'<p>{TEXT}</p>'.encode(), 'text/html')}, tls_context=ctx)

    @classmethod
    def tearDownClass(cls):
        for s in cls.sites.values():
            s.close()

    def setUp(self):
        # The machine's trust store is replaced by the test CA alone; verification itself is the real one.
        real_ctx = ssl.create_default_context
        ca = self.certs['ca']
        patches = [mock.patch.object(ssl, 'create_default_context', lambda *a, **k: real_ctx(cafile=ca)),
                   mock.patch.object(sources, 'CACHE_DIR', tempfile.mkdtemp()),
                   mock.patch.object(sources, 'time', _NO_WAIT)]
        real_gai = socket.getaddrinfo
        patches.append(mock.patch.object(socket, 'getaddrinfo', lambda host, *a, **k: (
            [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', a[0] if a else 0))] if host == self.HOST else real_gai(host, *a, **k))))
        pub, _ = public_host(self.HOST)
        patches.append(pub)
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def url(self, kind):
        origin = f'https://{self.HOST}:{self.sites[kind].port}'
        patch = fixture_origin(origin)
        patch.start()
        self.addCleanup(patch.stop)
        return origin + '/notice.html'

    def test_1_a_valid_https_source_works(self):
        doc = sources.load_html(self.url('good'), use_cache=False)
        self.assertIn('25-06-2026', doc.text)

    def test_2_a_self_signed_certificate_is_refused_and_not_retried(self):
        with self.assertRaises(sources.FetchError) as ctx:
            sources.fetch(self.url('self_signed'), use_cache=False)
        self.assertIn('1 attempt:', str(ctx.exception))
        self.assertIn('TLS certificate could not be verified', str(ctx.exception))
        self.assertEqual(self.sites['self_signed'].total(), 0, 'no request was sent over an unverified connection')

    def test_2b_a_certificate_for_another_host_is_refused(self):
        with self.assertRaises(sources.FetchError):
            sources.fetch(self.url('wrong_host'), use_cache=False)
        self.assertEqual(self.sites['wrong_host'].total(), 0)

    def test_2c_the_failure_is_reported_as_tls(self):
        res = discovery.fetch_checked(self.url('self_signed'))
        self.assertEqual((res.ok, res.error_kind), (False, 'TLS'))

    def test_research_extraction_refuses_an_unverified_certificate_too(self):
        text, failure, reason = govos._fetch_source_text(self.url('self_signed'))
        self.assertEqual((text, failure), (None, 'SOURCE_FETCH_FAILURE'))
        self.assertIn('TLS certificate could not be verified', reason)


if __name__ == '__main__':
    unittest.main()
