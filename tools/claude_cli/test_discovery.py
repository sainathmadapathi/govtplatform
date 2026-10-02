"""Source discovery: what Claude proposes is a CANDIDATE, and deterministic code decides what it is.

Covered: URL syntax, the server-side-request guard (every hop re-validated), suffix-based trust,
redirect handling, reachability recorded as reasons, the identity hint, OFFICIAL-only scoping, the
audit manifest, the "Claude cannot make anything official" rules, DiscoveryUnavailable with no
silent fallback to any other service, the builder's `search.py` adapter, and the memo helpers.

No test starts the real Claude CLI or touches the network. Claude is a scripted `FakeClaude`; page
fetches are fakes (`discover(fetch=...)`) or a fake opener plus an injected DNS resolver under
`fetch_checked`; and a `NoNetwork` guard fails any test that reaches for a socket.
"""
from __future__ import annotations

import functools
import json
import socket
import threading
import unittest
import urllib.error
from unittest import mock

from . import discovery
from .audit import MemoryAuditSink
from .client import job_scope
from .discovery import (DiscoveryUnavailable, FetchResult, MAX_REDIRECTS, MAX_URL_LENGTH, classify_host,
                        classify_url, discover, fetch_checked, identity_hint, memo_clear, memo_get, memo_put,
                        resolves_public, validate_url_syntax)
from .exam_fixtures import NoNetwork
from .prompts import TEMPLATES
from .schemas import OPERATION_SCHEMAS, InfraStatus, Operation
from .testing import FakeClaude, envelope, use_gateway

from tools.exam_builder import search as builder_search
from tools.exam_builder.search import Hit, SearchUnavailable, search

OFFICIAL = 'https://notice.example-commission.gov.in/ao-2031.pdf'
OTHER_OFFICIAL = 'https://www.example-board.nic.in/recruitment'
COACHING = 'https://bestcoaching-hub.com/example-commission-official-notice'
QUERY = 'Example Commission Assistant Officer Examination 2031 notice'


def cand(url: str, title: str = 'Notice of Examination', **kw) -> dict:
    out = {'title': title, 'url': url, 'authority_name': 'Example Commission', 'document_kind': 'NOTIFICATION',
           'why_relevant': 'Looks like the notice of the examination.', 'snippet': 'Applications are invited.'}
    out.update(kw)
    return out


def reply(*cands: dict, searched=('example commission assistant officer 2031',), notes: str = '') -> dict:
    return {'candidates': list(cands), 'searched_queries': list(searched), 'notes': notes}


def web(structured: dict, *, searches: int = 2, fetches: int = 3, turns: int = 6) -> dict:
    return envelope(structured, web_search=searches, web_fetch=fetches, turns=turns)


def page_ok(url: str, text: str = 'Example Commission Assistant Officer Examination 2031 notice', final: str = '') -> FetchResult:
    return FetchResult(ok=True, status=200, final_url=final or url, content_type='text/html', text=text, hops=[url])


class FakeFetch:
    """A `discover(fetch=...)` stand-in: url -> FetchResult. Unknown URLs are unreachable."""

    def __init__(self, pages: dict | None = None) -> None:
        self.pages = pages or {}
        self.calls: list = []

    def __call__(self, url: str) -> FetchResult:
        self.calls.append(url)
        return self.pages.get(url, FetchResult(ok=False, error='no such page'))


class FakeDns:
    """An injected resolver: host -> list of addresses; unknown hosts do not resolve."""

    def __init__(self, table: dict | None = None, default: str | None = '93.184.216.34') -> None:
        self.table, self.default, self.calls = table or {}, default, []

    def __call__(self, host, port=None):
        self.calls.append(host)
        addrs = self.table.get(host, [self.default] if self.default else [])
        if not addrs:
            raise socket.gaierror(f'cannot resolve {host}')
        return [(socket.AF_INET6 if ':' in a else socket.AF_INET, socket.SOCK_STREAM, 6, '', (a, 0)) for a in addrs]


class FakeResponse:
    def __init__(self, status: int, content_type: str, body: bytes) -> None:
        self.status, self.headers, self._body, self.read_sizes = status, {'Content-Type': content_type}, body, []

    def getcode(self) -> int:
        return self.status

    def read(self, n: int = -1) -> bytes:
        self.read_sizes.append(n)
        return self._body if n < 0 else self._body[:n]

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> bool:
        return False


class FakeWeb:
    """A fake urllib opener. Routes: ('page', ctype, body) | ('redirect', code, location) |
    ('http', code) | ('raise', exception). It records every URL it was asked to open and every
    handler `build_opener` was given."""

    def __init__(self, routes: dict) -> None:
        self.routes, self.opened, self.handlers, self.timeouts, self.responses = routes, [], [], [], []

    def build_opener(self, *handlers):
        self.handlers = list(handlers)
        return self

    def open(self, req, timeout=None):
        url = req.full_url
        self.opened.append(url)
        self.timeouts.append(timeout)
        kind, *rest = self.routes.get(url, ('raise', urllib.error.URLError('no route')))
        if kind == 'page':
            resp = FakeResponse(200, rest[0], rest[1])
            self.responses.append(resp)
            return resp
        if kind == 'redirect':
            raise urllib.error.HTTPError(url, rest[0], 'moved', {'Location': rest[1]}, None)
        if kind == 'http':
            raise urllib.error.HTTPError(url, rest[0], 'status', {}, None)
        raise rest[0]

    def patched(self):
        return mock.patch.object(discovery.urllib.request, 'build_opener', self.build_opener)


class NetCase(unittest.TestCase):
    """A TestCase that fails if anything reached for the network, and starts with an empty memo."""

    def setUp(self):
        super().setUp()
        memo_clear()
        self.addCleanup(memo_clear)
        self.net = NoNetwork()
        self.net.__enter__()
        self.addCleanup(self._check_network)

    def _check_network(self):
        self.net.__exit__(None, None, None)
        self.assertEqual(self.net.attempts, [], 'the test reached for the network')


# ================================================================================ trust classes
class ClassificationTests(unittest.TestCase):
    def test_indian_government_suffixes_are_official(self):
        for host in ('ssc.gov.in', 'www.ssc.gov.in', 'upsconline.nic.in', 'SSC.GOV.IN', 'ssc.gov.in.',
                     'a.b.c.example.gov.in'):
            self.assertEqual(classify_host(host), 'OFFICIAL', host)

    def test_academic_suffixes_are_trusted_public_but_never_official(self):
        for host in ('iitd.ac.in', 'www.mit.edu', 'cs.example.edu.in', 'ncl.res.in'):
            self.assertEqual(classify_host(host), 'TRUSTED_PUBLIC', host)

    def test_lookalike_hosts_are_not_official(self):
        for host in ('ssc.gov.in.evil.com', 'gov.in.attacker.net', 'ssc.gov.in-login.com', 'ssc-gov.in',
                     'evilgov.in', 'notgov.in', 'fakenic.in', 'nic.in.example.org', 'ssc.gov.in.nic.in.evil.io',
                     'gov.in', 'nic.in', 'ac.in.evil.com', 'fakeac.in', 'mit.edu.evil.com'):
            self.assertEqual(classify_host(host), 'UNVERIFIED', host)

    def test_a_bare_gov_is_the_united_states_not_india(self):
        for host in ('epa.gov', 'insurance.ca.gov', 'nasa.gov', 'ssc.gov', 'www.upsc.gov'):
            self.assertEqual(classify_host(host), 'UNVERIFIED', host)

    def test_other_domains_and_empty_hosts_are_unverified(self):
        for host in ('bestcoaching-hub.com', 'prsindia.org', 'youtube.com', '', None):
            self.assertEqual(classify_host(host), 'UNVERIFIED', host)

    def test_a_url_is_classified_by_its_real_host_not_by_what_the_url_text_says(self):
        for url in ('https://evil.example/ssc.gov.in', 'https://evil.example/?next=https://ssc.gov.in',
                    'https://ssc.gov.in@evil.example/', 'https://evil.example#ssc.gov.in',
                    'https://ssc.gov.in.evil.example/notice', 'not a url', ''):
            self.assertEqual(classify_url(url), 'UNVERIFIED', url)
        self.assertEqual(classify_url('https://ssc.gov.in/notice'), 'OFFICIAL')
        self.assertEqual(classify_url('http://www.upsc.gov.in:80/x?y=z#frag'), 'OFFICIAL')


# ===================================================================================== syntax
class UrlSyntaxTests(unittest.TestCase):
    def test_plain_http_and_https_pages_pass(self):
        for url in (OFFICIAL, OTHER_OFFICIAL, 'http://upsc.gov.in/a/b?c=d#e', 'https://x.example:443/p',
                    'http://x.example:80/p', 'https://ssc.gov.in./notice'):
            self.assertEqual(validate_url_syntax(url), (True, ''), url)

    def test_only_http_and_https_schemes_are_accepted(self):
        for url in ('ftp://ssc.gov.in/a', 'file:///etc/passwd', 'javascript:alert(1)', 'data:text/html,hi',
                    'gopher://ssc.gov.in/', '//ssc.gov.in/a', 'ssc.gov.in/a', 'HTTPS-ish://ssc.gov.in',
                    'mailto:a@b.gov.in', 'ws://ssc.gov.in/'):
            ok, why = validate_url_syntax(url)
            self.assertFalse(ok, url)
            self.assertTrue(why)

    def test_empty_and_non_string_values_are_rejected(self):
        for bad in ('', '   ', None, 12, [], {}, b'https://ssc.gov.in'):
            self.assertFalse(validate_url_syntax(bad)[0], repr(bad))

    def test_credentials_in_the_url_are_rejected(self):
        for url in ('https://user:pw@ssc.gov.in/', 'https://user@ssc.gov.in/', 'https://ssc.gov.in@evil.example/',
                    'https://:pw@ssc.gov.in/', r'https://evil.example\@ssc.gov.in/'):
            ok, why = validate_url_syntax(url)
            self.assertFalse(ok, url)
            self.assertIn('credentials', why)

    def test_local_and_internal_names_are_rejected(self):
        for url in ('https://localhost/', 'http://localhost:80/', 'https://app.localhost/', 'https://printer.local/',
                    'https://metadata.google.internal/', 'https://router.lan/', 'https://intranet/',
                    'https://LOCALHOST/', 'https://x.localhost./'):
            self.assertFalse(validate_url_syntax(url)[0], url)

    def test_ip_literals_are_rejected_in_every_form(self):
        for url in ('https://127.0.0.1/', 'http://10.0.0.1/', 'http://192.168.1.5/', 'http://172.16.0.9/',
                    'http://169.254.169.254/latest/meta-data/', 'http://8.8.8.8/', 'https://[::1]/',
                    'https://[fe80::1]/', 'https://[2001:4860:4860::8888]/', 'http://0.0.0.0/',
                    'https://127.1/', 'https://0x7f.1/', 'https://0x7f.0.0.1/', 'https://2130706433/',
                    'https://017700000001/', 'https://10.1/', 'https://192.168.257/', 'http://1.2.3.4.5/'):
            self.assertFalse(validate_url_syntax(url)[0], url)

    def test_non_standard_ports_are_rejected_and_out_of_range_ports_are_malformed(self):
        for url in ('https://ssc.gov.in:8080/', 'https://ssc.gov.in:22/', 'http://ssc.gov.in:8443/',
                    'https://ssc.gov.in:6379/', 'https://ssc.gov.in:0/'):
            ok, why = validate_url_syntax(url)
            self.assertFalse(ok, url)
        self.assertEqual(validate_url_syntax('https://ssc.gov.in:99999/'), (False, 'URL is malformed'))
        self.assertEqual(validate_url_syntax('https://ssc.gov.in:abc/'), (False, 'URL is malformed'))

    def test_length_whitespace_and_control_characters_are_rejected(self):
        self.assertEqual(validate_url_syntax('https://ssc.gov.in/' + 'a' * MAX_URL_LENGTH), (False, 'URL is too long'))
        self.assertTrue(validate_url_syntax('https://ssc.gov.in/' + 'a' * (MAX_URL_LENGTH - 20))[0])
        for url in ('https://ssc.gov.in/a b', 'https://ssc.gov.in/\x00', 'https://ssc.gov.in/\nHost: evil',
                    'https://ssc.gov.in/\r\n', 'https://ssc.gov.in/\t', 'https://ssc.gov.in/\x7f',
                    ' https://ssc.gov.in/', 'https://ssc.gov.in/\u0085'.replace('\u0085', '\x1b')):
            self.assertFalse(validate_url_syntax(url)[0], repr(url))

    def test_hosts_without_a_dot_or_with_unexpected_characters_are_rejected(self):
        for url in ('https://intranet/', 'https://ssc_gov.in/', 'https://ssc.gov.in%00.evil.com/',
                    'https://exämple.gov.in/', 'https://ssc.gov.in%2eevil/'):
            self.assertFalse(validate_url_syntax(url)[0], url)


# ====================================================================================== SSRF guard
class ResolvesPublicTests(unittest.TestCase):
    def check(self, *addrs: str):
        return resolves_public('x.example.gov.in', FakeDns({'x.example.gov.in': list(addrs)}))

    def test_public_addresses_pass(self):
        self.assertEqual(self.check('93.184.216.34'), (True, ''))
        self.assertEqual(self.check('8.8.8.8', '1.1.1.1'), (True, ''))
        self.assertEqual(self.check('2001:4860:4860::8888'), (True, ''))

    def test_private_loopback_link_local_and_metadata_addresses_are_refused(self):
        for addr in ('10.0.0.5', '172.16.5.5', '192.168.0.10', '127.0.0.1', '169.254.169.254', '100.64.0.1',
                     '0.0.0.0', '255.255.255.255', '203.0.113.9', '::1', 'fc00::1', 'fe80::1', 'fe80::1%eth0',
                     '::ffff:127.0.0.1', '::ffff:10.0.0.1', '2002:7f00:1::'):
            ok, why = self.check(addr)
            self.assertFalse(ok, addr)
            self.assertIn('private or reserved', why)

    def test_one_private_record_among_public_ones_refuses_the_host(self):
        ok, why = self.check('8.8.8.8', '10.0.0.5')
        self.assertFalse(ok)
        self.assertFalse(self.check('93.184.216.34', '::1')[0])

    def test_an_unresolvable_host_and_an_empty_answer_are_refused_with_a_reason(self):
        self.assertEqual(resolves_public('nope.example.gov.in', FakeDns({}, default=None)),
                         (False, 'host name does not resolve'))
        self.assertEqual(self.check(), (False, 'host name does not resolve'))
        self.assertEqual(resolves_public('x.example', lambda h, p: []), (False, 'host name does not resolve'))

        def boom(host, port):
            raise OSError('dns down')
        self.assertEqual(resolves_public('x.example', boom), (False, 'host name does not resolve'))

    def test_an_unreadable_address_is_refused(self):
        resolver = lambda host, port: [(2, 1, 6, '', ('not-an-ip', 0))]
        self.assertEqual(resolves_public('x.example', resolver), (False, 'host resolves to an unreadable address'))


# ======================================================================================== fetching
class FetchCheckedTests(NetCase):
    def run_fetch(self, url: str, web_: FakeWeb, dns: FakeDns | None = None, **kw) -> FetchResult:
        with web_.patched():
            return fetch_checked(url, resolver=dns or FakeDns(), **kw)

    def test_a_reachable_page_is_returned_with_its_text_and_hop_list(self):
        web_ = FakeWeb({OFFICIAL: ('page', 'text/html; charset=utf-8', b'<html>Example Commission 2031</html>')})
        r = self.run_fetch(OFFICIAL, web_)
        self.assertTrue(r.ok)
        self.assertEqual((r.status, r.final_url, r.content_type, r.hops), (200, OFFICIAL, 'text/html', [OFFICIAL]))
        self.assertIn('Example Commission 2031', r.text)
        self.assertEqual(r.error, '')

    def test_urllib_is_never_allowed_to_follow_redirects_on_its_own(self):
        web_ = FakeWeb({OFFICIAL: ('page', 'text/html', b'x')})
        self.run_fetch(OFFICIAL, web_)
        self.assertIn(discovery._NoRedirect, web_.handlers)
        self.assertIsNone(discovery._NoRedirect().redirect_request(None, None, 302, 'x', {}, 'https://evil.example/'))

    def test_only_a_bounded_amount_is_read_and_a_pdf_body_is_not_decoded(self):
        web_ = FakeWeb({OFFICIAL: ('page', 'application/pdf', b'%PDF-1.7 ' + b'x' * 100)})
        r = self.run_fetch(OFFICIAL, web_, max_bytes=40)
        self.assertTrue(r.ok)
        self.assertEqual(r.text, '')
        self.assertEqual(web_.responses[0].read_sizes, [40])
        self.assertEqual(web_.timeouts, [discovery.FETCH_TIMEOUT])

    def test_a_host_that_resolves_to_a_private_address_is_never_contacted(self):
        dns = FakeDns({'notice.example-commission.gov.in': ['10.0.0.5']})
        web_ = FakeWeb({OFFICIAL: ('page', 'text/html', b'secret internal page')})
        r = self.run_fetch(OFFICIAL, web_, dns)
        self.assertFalse(r.ok)
        self.assertIn('blocked hop', r.error)
        self.assertIn('private or reserved', r.error)
        self.assertEqual(web_.opened, [])
        self.assertEqual((r.status, r.text), (0, ''))

    def test_an_unresolvable_host_is_a_recorded_reason_not_a_fact(self):
        r = self.run_fetch(OFFICIAL, FakeWeb({}), FakeDns({}, default=None))
        self.assertFalse(r.ok)
        self.assertEqual(r.error, 'blocked hop: host name does not resolve')

    def test_a_syntactically_bad_url_is_blocked_before_any_lookup(self):
        dns = FakeDns()
        web_ = FakeWeb({})
        for url in ('http://127.0.0.1/admin', 'https://localhost/', 'file:///etc/passwd', 'ftp://ssc.gov.in/'):
            r = self.run_fetch(url, web_, dns)
            self.assertFalse(r.ok, url)
            self.assertIn('blocked hop', r.error)
        self.assertEqual((web_.opened, dns.calls), ([], []))

    def test_a_redirect_is_followed_and_each_hop_is_resolved_again(self):
        start, mid, end = 'https://a.example-commission.gov.in/x', 'https://b.example-commission.gov.in/y', OFFICIAL
        web_ = FakeWeb({start: ('redirect', 302, mid), mid: ('redirect', 301, '/ao-2031.pdf'),
                        'https://b.example-commission.gov.in/ao-2031.pdf': ('page', 'text/html', b'final')})
        dns = FakeDns()
        r = self.run_fetch(start, web_, dns)
        self.assertTrue(r.ok)
        self.assertEqual(r.final_url, 'https://b.example-commission.gov.in/ao-2031.pdf')
        self.assertEqual(r.hops, [start, mid, 'https://b.example-commission.gov.in/ao-2031.pdf'])
        self.assertEqual(dns.calls, ['a.example-commission.gov.in', 'b.example-commission.gov.in',
                                     'b.example-commission.gov.in'])
        self.assertNotIn(end, web_.opened)

    def test_a_redirect_to_a_private_address_is_blocked_at_that_hop(self):
        internal = 'https://intranet.example-commission.gov.in/admin'
        web_ = FakeWeb({OFFICIAL: ('redirect', 302, internal), internal: ('page', 'text/html', b'ADMIN')})
        dns = FakeDns({'intranet.example-commission.gov.in': ['10.1.2.3']})
        r = self.run_fetch(OFFICIAL, web_, dns)
        self.assertFalse(r.ok)
        self.assertIn('blocked hop', r.error)
        self.assertEqual(r.hops, [OFFICIAL])
        self.assertEqual(web_.opened, [OFFICIAL])

    def test_a_redirect_to_a_forbidden_form_of_url_is_blocked(self):
        for location in ('http://127.0.0.1:9000/admin', 'http://169.254.169.254/latest/meta-data/',
                         'file:///etc/passwd', 'https://user:pw@ssc.gov.in/', 'http://localhost/', 'ftp://x.gov.in/f',
                         'https://ssc.gov.in:8443/'):
            web_ = FakeWeb({OFFICIAL: ('redirect', 302, location)})
            r = self.run_fetch(OFFICIAL, web_)
            self.assertFalse(r.ok, location)
            self.assertIn('blocked hop', r.error, location)
            self.assertEqual(web_.opened, [OFFICIAL], location)

    def test_a_redirect_loop_stops_with_a_reason(self):
        a, b = 'https://a.example-commission.gov.in/', 'https://b.example-commission.gov.in/'
        web_ = FakeWeb({a: ('redirect', 302, b), b: ('redirect', 302, a)})
        r = self.run_fetch(a, web_)
        self.assertFalse(r.ok)
        self.assertEqual(r.error, 'too many redirects')
        self.assertEqual(len(r.hops), MAX_REDIRECTS + 1)

    def test_an_http_error_is_recorded_with_its_status(self):
        r = self.run_fetch(OFFICIAL, FakeWeb({OFFICIAL: ('http', 404)}))
        self.assertEqual((r.ok, r.status, r.error, r.final_url), (False, 404, 'HTTP 404', OFFICIAL))
        r = self.run_fetch(OFFICIAL, FakeWeb({OFFICIAL: ('http', 503)}))
        self.assertEqual((r.ok, r.status, r.error), (False, 503, 'HTTP 503'))

    def test_a_redirect_status_without_a_location_is_an_error_not_a_loop(self):
        r = self.run_fetch(OFFICIAL, FakeWeb({OFFICIAL: ('http', 302)}))
        self.assertEqual((r.ok, r.status, r.error), (False, 302, 'HTTP 302'))

    def test_timeouts_and_connection_failures_are_reasons_named_by_type_only(self):
        for exc in (TimeoutError('secret path C:/x'), urllib.error.URLError('refused'), ConnectionResetError('x'),
                    RuntimeError('boom')):
            r = self.run_fetch(OFFICIAL, FakeWeb({OFFICIAL: ('raise', exc)}))
            self.assertFalse(r.ok)
            self.assertEqual(r.error, type(exc).__name__)
            self.assertNotIn('secret', r.error)
            self.assertEqual(r.status, 0)


# =========================================================================== the identity hint
class IdentityHintTests(unittest.TestCase):
    def test_a_page_carrying_the_queries_distinctive_words_matches(self):
        page = '<html><title>x</title><body><h1>Example Commission</h1><p>Assistant Officer examination 2031</p></body></html>'
        self.assertEqual(identity_hint(QUERY, 'Notice', page), 'MATCHED')

    def test_a_partial_overlap_is_weak_and_a_different_page_does_not_match(self):
        self.assertEqual(identity_hint(QUERY, 'Example Assistant', 'about the page'), 'WEAK')
        self.assertEqual(identity_hint(QUERY, 'Sample Board', 'Junior Clerk 2032 sample board clerk'), 'NOT_MATCHED')

    def test_nothing_to_compare_is_unchecked_never_matched(self):
        self.assertEqual(identity_hint(QUERY, '', ''), 'UNCHECKED')
        self.assertEqual(identity_hint('the official notification for', 'Anything', 'page'), 'UNCHECKED')
        self.assertEqual(identity_hint('', 'Example', 'Example'), 'UNCHECKED')

    def test_tags_and_entities_are_not_words_and_generic_words_do_not_count(self):
        page = '<div class="assistant officer 2031 example">hello</div><p>Example&nbsp;Commission</p>'
        self.assertEqual(identity_hint('assistant officer 2031', '', page), 'NOT_MATCHED')
        self.assertEqual(identity_hint('official notification exam commission', 'x', 'official notification exam commission'),
                         'UNCHECKED')

    def test_it_is_advisory_the_title_alone_can_carry_the_words(self):
        self.assertEqual(identity_hint('Example Assistant Officer 2031', 'Example Assistant Officer 2031', 'blank'),
                         'MATCHED')


# ======================================================================================= discover
class DiscoverTests(NetCase):
    def run_discover(self, gateway, *, fetch=None, **kw):
        kw.setdefault('fetch', fetch if fetch is not None else FakeFetch())
        return discover(QUERY, gateway=gateway, **kw)

    # ---------------------------------------------------------------- candidates only, never facts
    def test_candidates_pass_syntax_and_trust_checks_and_unusable_ones_are_rejected_with_reasons(self):
        proposed = [cand(OFFICIAL), cand('ftp://files.example-commission.gov.in/a.pdf'),
                    cand('http://localhost:8080/admin'), cand('https://10.0.0.1/x'), cand(COACHING),
                    cand(OFFICIAL + '#section-2'), cand('https://user:pw@notice.example-commission.gov.in/'),
                    cand('')]
        fetch = FakeFetch({OFFICIAL: page_ok(OFFICIAL)})
        m = self.run_discover(FakeClaude(web(reply(*proposed))), fetch=fetch)
        self.assertEqual([c.url for c in m.candidates], [OFFICIAL])
        self.assertEqual(m.candidates[0].trust, 'OFFICIAL')
        rejected = {r['url']: r['reasons'] for r in m.rejected}
        self.assertEqual(len(m.rejected), 7)
        self.assertIn('only http(s) URLs are accepted', rejected['ftp://files.example-commission.gov.in/a.pdf'])
        self.assertIn('URL has no public host name', rejected['http://localhost:8080/admin'])
        self.assertIn('URL names an IP address, not a host name', rejected['https://10.0.0.1/x'])
        self.assertTrue(any('official-only' in why for why in rejected[COACHING]))
        self.assertIn('duplicate of an earlier candidate', rejected[OFFICIAL + '#section-2'])
        # The credentials are never stored: the manifest keeps the URL with its user:password@ part redacted.
        self.assertIn('URL carries credentials', rejected['https://***@notice.example-commission.gov.in/'])
        self.assertNotIn('pw@', repr(m.as_dict()))
        self.assertIn('empty URL', rejected[''])
        self.assertEqual(fetch.calls, [OFFICIAL], 'only a syntactically valid, in-scope URL may ever be fetched')

    def test_claude_calling_a_coaching_site_official_does_not_make_it_so(self):
        lying = cand(COACHING, title='OFFICIAL Notification - Government of India', authority_name='Example Commission (OFFICIAL)',
                     why_relevant='This is the official government website of Example Commission.',
                     snippet='Official notification. Verified by the Government.')
        lookalike = cand('https://notice.example-commission.gov.in.evil.test/ao.pdf', why_relevant='official')
        fetch = FakeFetch({COACHING: page_ok(COACHING), lookalike['url']: page_ok(lookalike['url'])})
        m = self.run_discover(FakeClaude(web(reply(lying, lookalike))), fetch=fetch, official_only=False)
        self.assertEqual([c.trust for c in m.candidates], ['UNVERIFIED', 'UNVERIFIED'])
        self.assertEqual([c.final_trust for c in m.candidates], ['UNVERIFIED', 'UNVERIFIED'])
        for c in m.as_dict()['candidates']:
            self.assertEqual(c['trust'], 'UNVERIFIED')
            self.assertEqual(c['finalTrust'], 'UNVERIFIED')
        self.assertIn('official', m.candidates[0].why_relevant.lower())     # Claude's words are kept as words, only
        self.assertIn('None is official because Claude said so', m.as_dict()['note'])

    def test_in_official_only_mode_those_same_candidates_are_rejected_not_listed(self):
        lying = cand(COACHING, title='OFFICIAL Notification', why_relevant='the official site')
        lookalike = cand('https://ssc.gov.in.evil.test/notice')
        fetch = FakeFetch()
        m = self.run_discover(FakeClaude(web(reply(lying, lookalike))), fetch=fetch, official_only=True)
        self.assertEqual(m.candidates, [])
        self.assertEqual(len(m.rejected), 2)
        self.assertTrue(all('UNVERIFIED host' in r['reasons'][0] for r in m.rejected))
        self.assertEqual(fetch.calls, [], 'an out-of-scope host is not even fetched')

    def test_claude_cannot_carry_an_official_flag_the_schema_has_no_such_field(self):
        item = OPERATION_SCHEMAS[Operation.DISCOVER_SOURCES]['properties']['candidates']['items']
        self.assertIs(item['additionalProperties'], False)
        self.assertFalse({'official', 'is_official', 'trust', 'verified', 'trust_level'} & set(item['properties']))
        for extra in ({'official': True}, {'trust': 'OFFICIAL'}, {'verified': True}):
            with self.assertRaises(DiscoveryUnavailable) as ctx:
                self.run_discover(FakeClaude(web(reply(cand(OFFICIAL, **extra)))))
            self.assertEqual(ctx.exception.status, InfraStatus.CLAUDE_SCHEMA_REJECTED)

    # --------------------------------------------------------------------------- reachability
    def test_a_url_claude_invented_that_does_not_resolve_is_rejected_not_listed(self):
        invented = 'https://made-up-board.example-commission.gov.in/notice-2031.pdf'
        dns = FakeDns({}, default=None)
        fetch = functools.partial(fetch_checked, resolver=dns)
        web_ = FakeWeb({})
        with web_.patched():
            m = self.run_discover(FakeClaude(web(reply(cand(invented)))), fetch=fetch)
        self.assertEqual(m.candidates, [])
        self.assertEqual(m.rejected[0]['url'], invented)
        self.assertIn('not reachable', m.rejected[0]['reasons'][0])
        self.assertIn('host name does not resolve', m.rejected[0]['reasons'][0])
        self.assertEqual(web_.opened, [])

    def test_reachability_failures_are_recorded_as_reasons_and_never_as_facts_about_an_authority(self):
        pages = {'https://a.example-commission.gov.in/1': FetchResult(ok=False, status=404, error='HTTP 404'),
                 'https://a.example-commission.gov.in/2': FetchResult(ok=False, error='TimeoutError'),
                 'https://a.example-commission.gov.in/3': FetchResult(ok=False, status=503, error='HTTP 503')}
        m = self.run_discover(FakeClaude(web(reply(*[cand(u) for u in pages]))), fetch=FakeFetch(pages))
        self.assertEqual(m.candidates, [])
        reasons = [r['reasons'][0] for r in m.rejected]
        self.assertEqual(reasons, ['not reachable (HTTP 404)', 'not reachable (TimeoutError)', 'not reachable (HTTP 503)'])
        blob = json.dumps(m.as_dict())
        for fact_state in ('NOT_PUBLISHED', 'NOT_EXTRACTED', 'OFFICIALLY_VERIFIED', 'NEEDS_REVIEW'):
            self.assertNotIn(fact_state, blob)

    def test_an_unreachable_candidate_is_listed_when_verification_is_switched_off_but_never_marked_reachable(self):
        fetch = FakeFetch()
        m = self.run_discover(FakeClaude(web(reply(cand(OFFICIAL)))), fetch=fetch, verify=False)
        self.assertEqual(fetch.calls, [])
        (c,) = m.candidates
        self.assertIsNone(c.reachable)
        self.assertEqual((c.http_status, c.identity), (0, 'UNCHECKED'))
        self.assertEqual(c.trust, 'OFFICIAL')

    def test_the_identity_hint_is_recorded_per_candidate_and_stays_advisory(self):
        pages = {OFFICIAL: page_ok(OFFICIAL, 'Example Commission Assistant Officer Examination 2031'),
                 OTHER_OFFICIAL: page_ok(OTHER_OFFICIAL, 'Sample Board junior clerk 2032 recruitment')}
        m = self.run_discover(FakeClaude(web(reply(cand(OFFICIAL), cand(OTHER_OFFICIAL)))), fetch=FakeFetch(pages))
        self.assertEqual([c.identity for c in m.candidates], ['MATCHED', 'NOT_MATCHED'])
        self.assertEqual(len(m.candidates), 2, 'a poor identity hint does not remove a candidate; the builder gate decides')

    # ------------------------------------------------------------------------------ redirects
    def test_a_redirect_from_an_official_host_to_an_unofficial_one_lowers_trust(self):
        landed = 'https://bestcoaching-hub.com/landing'
        fetch = FakeFetch({OFFICIAL: page_ok(OFFICIAL, final=landed)})
        m = self.run_discover(FakeClaude(web(reply(cand(OFFICIAL)))), fetch=fetch, official_only=False)
        (c,) = m.candidates
        self.assertEqual((c.final_url, c.final_trust), (landed, 'UNVERIFIED'))
        self.assertEqual(c.trust, 'UNVERIFIED', 'the effective trust must follow the page the candidate lands on')
        self.assertTrue(any('redirects from a OFFICIAL host to a UNVERIFIED host' in r for r in c.reasons))

    def test_in_official_only_mode_a_redirect_off_the_official_domain_removes_the_candidate(self):
        landed = 'https://bestcoaching-hub.com/landing'
        fetch = FakeFetch({OFFICIAL: page_ok(OFFICIAL, final=landed)})
        m = self.run_discover(FakeClaude(web(reply(cand(OFFICIAL)))), fetch=fetch, official_only=True)
        self.assertEqual(m.candidates, [])
        self.assertEqual(m.rejected[0]['url'], OFFICIAL)
        self.assertTrue(any('UNVERIFIED' in why for why in m.rejected[0]['reasons']))

    def test_a_redirect_from_an_unofficial_host_to_an_official_one_never_raises_trust(self):
        landed = OFFICIAL
        fetch = FakeFetch({COACHING: page_ok(COACHING, final=landed)})
        m = self.run_discover(FakeClaude(web(reply(cand(COACHING)))), fetch=fetch, official_only=False)
        (c,) = m.candidates
        self.assertEqual(c.trust, 'UNVERIFIED')
        self.assertEqual(c.final_trust, 'OFFICIAL')

    def test_redirects_inside_the_official_domain_keep_the_trust(self):
        landed = 'https://www.example-commission.gov.in/ao-2031.pdf'
        fetch = FakeFetch({OFFICIAL: page_ok(OFFICIAL, final=landed)})
        m = self.run_discover(FakeClaude(web(reply(cand(OFFICIAL)))), fetch=fetch)
        (c,) = m.candidates
        self.assertEqual((c.trust, c.final_trust, c.reasons), ('OFFICIAL', 'OFFICIAL', []))

    def test_the_real_fetcher_blocks_an_official_url_that_redirects_into_the_private_network(self):
        internal = 'https://intranet.example-commission.gov.in/admin'
        web_ = FakeWeb({OFFICIAL: ('redirect', 302, internal), internal: ('page', 'text/html', b'ADMIN PANEL')})
        dns = FakeDns({'intranet.example-commission.gov.in': ['192.168.1.20']})
        with web_.patched():
            m = self.run_discover(FakeClaude(web(reply(cand(OFFICIAL)))), fetch=functools.partial(fetch_checked, resolver=dns))
        self.assertEqual(m.candidates, [])
        self.assertIn('blocked hop', m.rejected[0]['reasons'][0])
        self.assertEqual(web_.opened, [OFFICIAL])

    def test_the_real_fetcher_blocks_a_candidate_whose_host_resolves_to_a_private_address(self):
        dns = FakeDns({'notice.example-commission.gov.in': ['169.254.169.254']})
        web_ = FakeWeb({OFFICIAL: ('page', 'text/html', b'metadata')})
        with web_.patched():
            m = self.run_discover(FakeClaude(web(reply(cand(OFFICIAL)))), fetch=functools.partial(fetch_checked, resolver=dns))
        self.assertEqual(m.candidates, [])
        self.assertIn('private or reserved', m.rejected[0]['reasons'][0])
        self.assertEqual(web_.opened, [])

    # ------------------------------------------------------------------- the app's own classifier
    def test_a_supplied_classifier_decides_trust_for_the_candidate_and_its_final_page(self):
        statutory = lambda url: 'TRUSTED_PUBLIC' if 'prsindia.org' in url else classify_url(url)
        url = 'https://prsindia.org/billtrack/example'
        fetch = FakeFetch({url: page_ok(url)})
        m = self.run_discover(FakeClaude(web(reply(cand(url)))), fetch=fetch, official_only=False, classify=statutory)
        self.assertEqual((m.candidates[0].trust, m.candidates[0].final_trust), ('TRUSTED_PUBLIC', 'TRUSTED_PUBLIC'))
        strict = self.run_discover(FakeClaude(web(reply(cand(url)))), fetch=FakeFetch({url: page_ok(url)}),
                                   official_only=True, classify=statutory)
        self.assertEqual(strict.candidates, [])

    # ------------------------------------------------------------------------- the audit trail
    def test_the_manifest_records_what_claude_returned_what_was_checked_and_why(self):
        sink = MemoryAuditSink()
        proposed = [cand(OFFICIAL), cand(COACHING), cand('ftp://x.gov.in/a'), cand(OTHER_OFFICIAL)]
        gw = FakeClaude(web(reply(*proposed, searched=('q one', 'q two'), notes='two results looked stale'),
                            searches=2, fetches=3, turns=7), audit=sink)
        fetch = FakeFetch({OFFICIAL: page_ok(OFFICIAL), OTHER_OFFICIAL: FetchResult(ok=False, status=500, error='HTTP 500')})
        m = discover(QUERY, gateway=gw, fetch=fetch, job_id='job-42')
        d = m.as_dict()
        self.assertEqual(d['query'], QUERY)
        self.assertEqual(d['jobId'], 'job-42')
        self.assertEqual(d['templateVersion'], TEMPLATES[Operation.DISCOVER_SOURCES].version)
        self.assertEqual(d['status'], 'OK')
        self.assertEqual(d['rawCandidates'], proposed, 'Claude\'s own list is kept verbatim')
        self.assertEqual([c['url'] for c in d['candidates']], [OFFICIAL])
        self.assertEqual(len(d['rejected']), 3)
        self.assertEqual(d['searchedQueries'], ['q one', 'q two'])
        self.assertEqual(d['notes'], 'two results looked stale')
        self.assertEqual(d['webActivity'], {'webSearchRequests': 2, 'webFetchRequests': 3, 'turns': 7})
        self.assertTrue(d['startedAt'].endswith('Z') and d['endedAt'].endswith('Z') and d['endedAt'] >= d['startedAt'])
        for key in ('title', 'url', 'snippet', 'authorityName', 'documentKind', 'whyRelevant', 'trust', 'syntaxOk',
                    'reachable', 'httpStatus', 'finalUrl', 'finalTrust', 'identity', 'reasons'):
            self.assertIn(key, d['candidates'][0])
        json.dumps(d)                                                       # serialisable as stored
        (event,) = sink.events
        self.assertEqual((event['operation'], event['job_id'], event['web_search_requests'], event['web_fetch_requests']),
                         ('DISCOVER_SOURCES', 'job-42', 2, 3))
        self.assertNotIn(OFFICIAL, json.dumps(event), 'the audit row holds fingerprints, not the query or results')

    def test_discovery_gives_claude_only_the_web_tools_and_the_scope_hints(self):
        gw = FakeClaude(web(reply()))
        discover(QUERY, gateway=gw, fetch=FakeFetch(), official_only=True, max_results=5)
        argv, prompt = gw.argvs[0], gw.prompts[0]
        self.assertEqual(argv[argv.index('--tools') + 1], 'WebSearch,WebFetch')
        self.assertIn('PREFERRED DOMAIN SUFFIXES: .gov.in, .nic.in', prompt)
        self.assertIn('MAX RESULTS: 5', prompt)
        self.assertEqual(gw.ops, [Operation.DISCOVER_SOURCES])
        gw2 = FakeClaude(web(reply()))
        discover(QUERY, gateway=gw2, fetch=FakeFetch(), official_only=False)
        self.assertNotIn('PREFERRED DOMAIN SUFFIXES', gw2.prompts[0])

    def test_only_max_results_candidates_are_examined_but_all_of_claudes_list_is_kept(self):
        urls = [f'https://p{i}.example-commission.gov.in/n' for i in range(6)]
        fetch = FakeFetch({u: page_ok(u) for u in urls})
        m = self.run_discover(FakeClaude(web(reply(*[cand(u) for u in urls]))), fetch=fetch, max_results=2)
        self.assertEqual(len(m.raw_candidates), 6)
        self.assertEqual([c.url for c in m.candidates], urls[:2])
        self.assertEqual(fetch.calls, urls[:2])

    def test_an_empty_answer_is_an_empty_manifest_not_a_guess(self):
        m = self.run_discover(FakeClaude(web(reply())))
        self.assertEqual((m.candidates, m.rejected, m.raw_candidates), ([], [], []))
        self.assertEqual(m.status, 'OK')

    def test_candidate_host_ignores_www(self):
        self.assertEqual(discovery.Candidate(url='https://WWW.Example-Board.nic.in/x').host, 'example-board.nic.in')

    # ---------------------------------------------------------------- unavailable: never a fallback
    def test_when_discovery_cannot_run_it_raises_with_the_infrastructure_status(self):
        cases = [InfraStatus.CLAUDE_DISCOVERY_UNAVAILABLE, InfraStatus.CLAUDE_DISABLED,
                 InfraStatus.CLAUDE_CLI_NOT_INSTALLED, InfraStatus.CLAUDE_CLI_NOT_AUTHENTICATED,
                 InfraStatus.CLAUDE_CLI_UNSUPPORTED, InfraStatus.CLAUDE_CLI_TIMEOUT, InfraStatus.CLAUDE_CLI_BUSY,
                 InfraStatus.CLAUDE_CLI_FAILED, InfraStatus.CLAUDE_INVALID_OUTPUT, InfraStatus.CLAUDE_SCHEMA_REJECTED]
        for status in cases:
            with self.subTest(status.value):
                with self.assertRaises(DiscoveryUnavailable) as ctx:
                    self.run_discover(FakeClaude(fail=status))
                self.assertIs(ctx.exception.status, status)

    def test_a_cli_without_web_tools_reports_discovery_unavailable_and_uses_no_other_service(self):
        gw = FakeClaude(fail=InfraStatus.CLAUDE_DISCOVERY_UNAVAILABLE)
        with mock.patch.object(discovery, 'fetch_checked') as fetch_checked_mock, \
                mock.patch('urllib.request.urlopen') as urlopen, \
                mock.patch('urllib.request.build_opener') as opener, \
                mock.patch('http.client.HTTPSConnection') as https:
            with self.assertRaises(DiscoveryUnavailable) as ctx:
                discover(QUERY, gateway=gw)                               # default fetcher, default everything
        self.assertEqual(ctx.exception.status, InfraStatus.CLAUDE_DISCOVERY_UNAVAILABLE)
        for client in (fetch_checked_mock, urlopen, opener, https):
            client.assert_not_called()
        self.assertEqual(self.net.attempts, [])
        self.assertEqual(gw.ops, [Operation.DISCOVER_SOURCES])             # asked Claude once, and only about discovery
        self.assertNotIn(Operation.EXTRACT_FIELDS, gw.ops)

    def test_a_disabled_claude_never_reaches_a_fetcher_or_a_client(self):
        with mock.patch.object(discovery, 'fetch_checked') as fetch_checked_mock, \
                mock.patch('urllib.request.urlopen') as urlopen:
            with self.assertRaises(DiscoveryUnavailable):
                discover(QUERY, gateway=FakeClaude(enabled=False))
        fetch_checked_mock.assert_not_called()
        urlopen.assert_not_called()

    def test_a_cancelled_discovery_returns_a_cancelled_manifest_without_fetching_anything(self):
        event = threading.Event()
        event.set()
        fetch = FakeFetch()
        with job_scope('job-9', event):
            m = discover(QUERY, gateway=FakeClaude(web(reply(cand(OFFICIAL)))), fetch=fetch)
        self.assertEqual((m.status, m.candidates), ('CANCELLED', []))
        self.assertEqual(fetch.calls, [])

    def test_the_default_gateway_is_used_when_none_is_given(self):
        gw = FakeClaude(web(reply(cand(OFFICIAL))))
        with use_gateway(gw):
            m = discover(QUERY, fetch=FakeFetch({OFFICIAL: page_ok(OFFICIAL)}))
        self.assertEqual(gw.calls, 1)
        self.assertEqual(len(m.candidates), 1)


# ========================================================================= the builder's adapter
class BuilderSearchAdapterTests(NetCase):
    def run_search(self, gateway, pages: dict | None = None, **kw):
        fetch = FakeFetch(pages or {})
        with mock.patch.object(discovery, 'fetch_checked', fetch):
            return search(QUERY, gateway=gateway, **kw), fetch

    def test_claude_disabled_or_unavailable_raises_search_unavailable_and_never_returns_results(self):
        for status in (InfraStatus.CLAUDE_DISABLED, InfraStatus.CLAUDE_CLI_NOT_INSTALLED,
                       InfraStatus.CLAUDE_CLI_NOT_AUTHENTICATED, InfraStatus.CLAUDE_CLI_UNSUPPORTED,
                       InfraStatus.CLAUDE_DISCOVERY_UNAVAILABLE, InfraStatus.CLAUDE_CLI_TIMEOUT,
                       InfraStatus.CLAUDE_CLI_BUSY, InfraStatus.CLAUDE_INVALID_OUTPUT,
                       InfraStatus.CLAUDE_SCHEMA_REJECTED):
            with self.subTest(status.value):
                with self.assertRaises(SearchUnavailable) as ctx:
                    self.run_search(FakeClaude(fail=status))
                self.assertIn(status.value, str(ctx.exception))
                self.assertIsInstance(ctx.exception.__cause__, DiscoveryUnavailable)

    def test_the_default_gateway_being_disabled_is_search_unavailable_not_an_empty_list(self):
        with use_gateway(FakeClaude(enabled=False)):
            with mock.patch.object(discovery, 'fetch_checked') as fetch:
                with self.assertRaises(SearchUnavailable) as ctx:
                    search(QUERY)
        self.assertIn('CLAUDE_DISABLED', str(ctx.exception))
        fetch.assert_not_called()

    def test_search_unavailable_is_not_confused_with_no_results(self):
        hits, _ = self.run_search(FakeClaude(web(reply())))
        self.assertEqual(hits, [])

    def test_no_other_search_service_is_ever_called(self):
        with mock.patch('urllib.request.urlopen') as urlopen, mock.patch('http.client.HTTPSConnection') as https, \
                mock.patch('http.client.HTTPConnection.request') as request:
            with self.assertRaises(SearchUnavailable):
                self.run_search(FakeClaude(fail=InfraStatus.CLAUDE_DISABLED))
        for client in (urlopen, https, request):
            client.assert_not_called()
        self.assertEqual(self.net.attempts, [])

    def test_hits_are_the_official_candidates_that_were_reached_with_their_trust_and_text(self):
        proposed = [cand(OFFICIAL, title='Notice', snippet='Applications are invited.'),
                    cand(COACHING, title='Official SSC notice (coaching)'),
                    cand(OTHER_OFFICIAL, title='Board page', snippet='', why_relevant='the board recruitment page')]
        hits, fetch = self.run_search(FakeClaude(web(reply(*proposed))),
                                      {OFFICIAL: page_ok(OFFICIAL), OTHER_OFFICIAL: page_ok(OTHER_OFFICIAL),
                                       COACHING: page_ok(COACHING)})
        self.assertEqual([h.url for h in hits], [OFFICIAL, OTHER_OFFICIAL])
        self.assertEqual([h.trust for h in hits], ['OFFICIAL', 'OFFICIAL'])
        self.assertEqual(hits[0].content, 'Applications are invited.')
        self.assertEqual(hits[1].content, 'the board recruitment page')      # falls back to why_relevant
        self.assertIsInstance(hits[0], Hit)
        self.assertEqual(hits[0].host, 'notice.example-commission.gov.in')
        self.assertNotIn(COACHING, fetch.calls)

    def test_a_hit_never_comes_from_a_candidate_whose_final_page_is_unofficial(self):
        landed = 'https://bestcoaching-hub.com/landing'
        hits, _ = self.run_search(FakeClaude(web(reply(cand(OFFICIAL)))), {OFFICIAL: page_ok(OFFICIAL, final=landed)})
        self.assertEqual(hits, [])

    def test_the_hit_url_is_the_final_url_after_redirects(self):
        landed = 'https://www.example-commission.gov.in/ao-2031.pdf'
        hits, _ = self.run_search(FakeClaude(web(reply(cand(OFFICIAL)))), {OFFICIAL: page_ok(OFFICIAL, final=landed)})
        self.assertEqual([h.url for h in hits], [landed])

    def test_with_official_only_off_every_reachable_candidate_is_returned_with_its_own_trust(self):
        hits, _ = self.run_search(FakeClaude(web(reply(cand(OFFICIAL), cand(COACHING)))),
                                  {OFFICIAL: page_ok(OFFICIAL), COACHING: page_ok(COACHING)}, official_only=False)
        self.assertEqual({h.url: h.trust for h in hits}, {OFFICIAL: 'OFFICIAL', COACHING: 'UNVERIFIED'})

    def test_an_unreachable_or_invented_url_is_not_a_hit(self):
        hits, _ = self.run_search(FakeClaude(web(reply(cand(OFFICIAL)))), {})
        self.assertEqual(hits, [])

    def test_max_results_is_clamped_to_twelve_in_the_request(self):
        gw = FakeClaude(web(reply()))
        self.run_search(gw, max_results=50)
        self.assertIn('MAX RESULTS: 12', gw.prompts[0])

    def test_classify_is_the_shared_suffix_rule(self):
        for url in (OFFICIAL, COACHING, 'https://epa.gov/x', 'https://iitd.ac.in/'):
            self.assertEqual(builder_search.classify(url), classify_url(url))

    def test_results_are_remembered_briefly_for_the_shared_gateway_only(self):
        gw = FakeClaude(web(reply(cand(OFFICIAL))))
        pages = {OFFICIAL: page_ok(OFFICIAL)}
        with use_gateway(gw), mock.patch.object(discovery, 'fetch_checked', FakeFetch(pages)):
            first = search(QUERY)
            again = search(QUERY.upper())                  # same key: lower-cased
            self.assertEqual((gw.calls, len(first), len(again)), (1, 1, 1))
            search(QUERY, max_results=5)                   # a different request is a different key
            self.assertEqual(gw.calls, 2)
            search(QUERY, official_only=False)
            self.assertEqual(gw.calls, 3)
        explicit = FakeClaude(web(reply(cand(OFFICIAL))))
        with mock.patch.object(discovery, 'fetch_checked', FakeFetch(pages)):
            search(QUERY, gateway=explicit)
            search(QUERY, gateway=explicit)
        self.assertEqual(explicit.calls, 2, 'an explicitly supplied gateway bypasses the memo')

    def test_an_unavailable_result_is_not_remembered(self):
        with use_gateway(FakeClaude(enabled=False)):
            with self.assertRaises(SearchUnavailable):
                search(QUERY)
        good = FakeClaude(web(reply(cand(OFFICIAL))))
        with use_gateway(good), mock.patch.object(discovery, 'fetch_checked', FakeFetch({OFFICIAL: page_ok(OFFICIAL)})):
            self.assertEqual(len(search(QUERY)), 1)
        self.assertEqual(good.calls, 1)


# ============================================================================== the memo helpers
class MemoTests(unittest.TestCase):
    def setUp(self):
        memo_clear()
        self.addCleanup(memo_clear)

    def test_a_stored_value_is_returned_until_cleared(self):
        self.assertIsNone(memo_get('k'))
        memo_put('k', ['v'])
        self.assertEqual(memo_get('k'), ['v'])
        memo_clear()
        self.assertIsNone(memo_get('k'))

    def test_entries_expire_after_the_ttl(self):
        clock = [1000.0]
        with mock.patch.object(discovery.time, 'monotonic', lambda: clock[0]):
            memo_put('k', 'v')
            clock[0] += discovery.MEMO_TTL_SECONDS - 1
            self.assertEqual(memo_get('k'), 'v')
            clock[0] += 2
            self.assertIsNone(memo_get('k'))
            self.assertNotIn('k', discovery._MEMO)

    def test_the_memo_is_bounded_and_drops_the_oldest_first(self):
        for i in range(260):
            memo_put(('q', i), i)
        self.assertLessEqual(len(discovery._MEMO), 200)
        self.assertIsNone(memo_get(('q', 0)))
        self.assertEqual(memo_get(('q', 259)), 259)

    def test_keys_are_independent(self):
        memo_put(('a', 1, True), 'x')
        memo_put(('a', 1, False), 'y')
        self.assertEqual((memo_get(('a', 1, True)), memo_get(('a', 1, False))), ('x', 'y'))


if __name__ == '__main__':
    unittest.main()
