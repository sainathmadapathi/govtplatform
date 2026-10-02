"""The authorisation boundary of the Claude endpoints (security.py): the admin check, the per-job
access tokens and the rate limiter.

`admin_check` is a pure function of (remote address, headers, environment), so every case here
passes those in directly; nothing touches the process environment except the one test that proves
the default really is `os.environ`.
"""
from __future__ import annotations

import os
import threading
import unittest
from unittest import mock

from werkzeug.datastructures import Headers

from tools.claude_cli import security
from tools.claude_cli.config import ENV_ADMIN_TOKEN
from tools.claude_cli.security import (ADMIN_HEADER, JOB_TOKEN_HEADER, RateLimiter, admin_check,
                                       admin_token_required, hash_token, new_job_token, token_matches)

TOKEN_ENV = {ENV_ADMIN_TOKEN: 's3cret-admin-token'}
NO_TOKEN_ENV: dict = {}


class FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


# =========================================================================== admin: token mode
class AdminTokenConfigured(unittest.TestCase):
    def test_correct_token_is_accepted(self):
        ok, why = admin_check('203.0.113.9', {ADMIN_HEADER: 's3cret-admin-token'}, TOKEN_ENV)
        self.assertTrue(ok)
        self.assertEqual(why, 'token')

    def test_token_is_accepted_from_any_address(self):
        for addr in ('127.0.0.1', '::1', '10.1.2.3', '203.0.113.9', '', None):
            with self.subTest(addr=addr):
                self.assertTrue(admin_check(addr, {ADMIN_HEADER: 's3cret-admin-token'}, TOKEN_ENV)[0])

    def test_missing_token_is_refused(self):
        ok, why = admin_check('127.0.0.1', {}, TOKEN_ENV)
        self.assertFalse(ok)
        self.assertIn('token', why)

    def test_wrong_token_is_refused(self):
        for bad in ('wrong', 's3cret-admin-token-x', 's3cret-admin-toke', 'S3CRET-ADMIN-TOKEN', 'x' * 500):
            with self.subTest(bad=bad[:20]):
                self.assertFalse(admin_check('127.0.0.1', {ADMIN_HEADER: bad}, TOKEN_ENV)[0])

    def test_empty_and_whitespace_token_header_is_refused(self):
        for bad in ('', '   ', '\t'):
            with self.subTest(bad=repr(bad)):
                self.assertFalse(admin_check('127.0.0.1', {ADMIN_HEADER: bad}, TOKEN_ENV)[0])

    def test_loopback_is_not_enough_once_a_token_is_configured(self):
        """The loopback shortcut exists only while no token is set."""
        for addr in ('127.0.0.1', '::1', '::ffff:127.0.0.1'):
            with self.subTest(addr=addr):
                self.assertFalse(admin_check(addr, {}, TOKEN_ENV)[0])

    def test_surrounding_whitespace_is_trimmed_on_both_sides(self):
        self.assertTrue(admin_check('1.2.3.4', {ADMIN_HEADER: '  s3cret-admin-token \n'}, TOKEN_ENV)[0])
        self.assertTrue(admin_check('1.2.3.4', {ADMIN_HEADER: 'abc'}, {ENV_ADMIN_TOKEN: '  abc  '})[0])

    def test_token_authorises_even_with_proxy_and_origin_headers(self):
        """A secret that was presented is the credential; the proxy and Origin guards only exist to
        protect the tokenless local mode."""
        headers = {ADMIN_HEADER: 's3cret-admin-token', 'X-Forwarded-For': '198.51.100.7',
                   'Origin': 'https://admin.example.org'}
        self.assertTrue(admin_check('10.0.0.2', headers, TOKEN_ENV)[0])

    def test_comparison_is_constant_time(self):
        """The comparison goes through hmac.compare_digest, never `==`."""
        with mock.patch.object(security.hmac, 'compare_digest', wraps=security.hmac.compare_digest) as spy:
            admin_check('127.0.0.1', {ADMIN_HEADER: 'whatever'}, TOKEN_ENV)
        spy.assert_called_once()
        a, b = spy.call_args[0]
        self.assertEqual({type(a), type(b)}, {bytes})

    def test_non_ascii_token_does_not_raise(self):
        env = {ENV_ADMIN_TOKEN: 'tökén-✓'}
        self.assertTrue(admin_check('1.2.3.4', {ADMIN_HEADER: 'tökén-✓'}, env)[0])
        self.assertFalse(admin_check('1.2.3.4', {ADMIN_HEADER: 'token'}, env)[0])

    def test_refusal_does_not_echo_the_token(self):
        ok, why = admin_check('127.0.0.1', {ADMIN_HEADER: 'guess'}, TOKEN_ENV)
        self.assertFalse(ok)
        self.assertNotIn('s3cret', why)
        self.assertNotIn('guess', why)

    def test_a_blank_configured_token_means_no_token(self):
        for blank in ('', '   '):
            with self.subTest(blank=repr(blank)):
                env = {ENV_ADMIN_TOKEN: blank}
                self.assertFalse(admin_token_required(env))
                self.assertTrue(admin_check('127.0.0.1', {}, env)[0])      # falls back to loopback
                self.assertFalse(admin_check('203.0.113.9', {ADMIN_HEADER: ''}, env)[0])     # an empty header is no key

    def test_header_lookup_is_case_insensitive_with_real_request_headers(self):
        headers = Headers([('x-govos-admin-token', 's3cret-admin-token')])
        self.assertTrue(admin_check('1.2.3.4', headers, TOKEN_ENV)[0])


# ======================================================================== admin: loopback mode
class AdminLoopbackOnly(unittest.TestCase):
    def test_loopback_without_proxy_headers_is_allowed(self):
        for addr in ('127.0.0.1', '::1', '::ffff:127.0.0.1'):
            with self.subTest(addr=addr):
                ok, why = admin_check(addr, {}, NO_TOKEN_ENV)
                self.assertTrue(ok)
                self.assertEqual(why, 'loopback')

    def test_non_loopback_is_refused(self):
        for addr in ('203.0.113.9', '10.0.0.5', '192.168.1.20', '172.16.0.1', '0.0.0.0', '::2',
                     '2001:db8::1', '127.0.0.2', '127.0.0.1.evil', 'localhost', ''):
            with self.subTest(addr=addr):
                ok, why = admin_check(addr, {}, NO_TOKEN_ENV)
                self.assertFalse(ok)
                self.assertIn('local-only', why)

    def test_unknown_remote_address_is_refused(self):
        self.assertFalse(admin_check(None, {}, NO_TOKEN_ENV)[0])

    def test_any_proxy_header_refuses_even_from_loopback(self):
        """A reverse proxy on the same machine makes every client look like loopback."""
        for header in ('X-Forwarded-For', 'Forwarded', 'X-Real-IP', 'X-Forwarded-Host'):
            with self.subTest(header=header):
                ok, why = admin_check('127.0.0.1', {header: '198.51.100.7'}, NO_TOKEN_ENV)
                self.assertFalse(ok)
                self.assertIn('proxied', why)
                self.assertIn('GOVOS_CLAUDE_ADMIN_TOKEN', why)

    def test_proxy_header_with_loopback_value_still_refuses(self):
        self.assertFalse(admin_check('127.0.0.1', {'X-Forwarded-For': '127.0.0.1'}, NO_TOKEN_ENV)[0])
        self.assertFalse(admin_check('::1', {'Forwarded': 'for=127.0.0.1'}, NO_TOKEN_ENV)[0])

    def test_proxy_header_names_are_case_insensitive_on_real_headers(self):
        headers = Headers([('x-forwarded-for', '1.2.3.4')])
        self.assertFalse(admin_check('127.0.0.1', headers, NO_TOKEN_ENV)[0])

    def test_proxy_header_does_not_help_a_remote_caller(self):
        self.assertFalse(admin_check('203.0.113.9', {'X-Forwarded-For': '127.0.0.1'}, NO_TOKEN_ENV)[0])

    def test_cross_origin_page_is_refused_without_a_token(self):
        """A web page on another site can make this browser call 127.0.0.1; that must not be admin."""
        for origin in ('https://evil.example', 'http://evil.example:3000', 'http://localhost.evil.com',
                       'http://127.0.0.1.evil.com', 'null', 'file://', 'https://govos.example.org'):
            with self.subTest(origin=origin):
                ok, why = admin_check('127.0.0.1', {'Origin': origin}, NO_TOKEN_ENV)
                self.assertFalse(ok)
                self.assertIn('cross-origin', why)

    def test_a_page_served_from_this_machine_is_allowed(self):
        for origin in ('http://localhost:3000', 'http://localhost:5000', 'http://127.0.0.1:5000',
                       'http://[::1]:5000', 'https://LOCALHOST', 'http://localhost'):
            with self.subTest(origin=origin):
                self.assertTrue(admin_check('127.0.0.1', {'Origin': origin}, NO_TOKEN_ENV)[0])

    def test_empty_origin_is_treated_as_absent(self):
        self.assertTrue(admin_check('127.0.0.1', {'Origin': ''}, NO_TOKEN_ENV)[0])
        self.assertTrue(admin_check('127.0.0.1', {'Origin': '   '}, NO_TOKEN_ENV)[0])

    def test_local_origin_does_not_help_a_remote_caller(self):
        self.assertFalse(admin_check('203.0.113.9', {'Origin': 'http://localhost:3000'}, NO_TOKEN_ENV)[0])

    def test_job_token_header_is_not_an_admin_credential(self):
        """The candidate's per-job token never grants admin."""
        self.assertFalse(admin_check('203.0.113.9', {JOB_TOKEN_HEADER: 'anything'}, NO_TOKEN_ENV)[0])
        self.assertFalse(admin_check('203.0.113.9', {JOB_TOKEN_HEADER: 's3cret-admin-token'}, TOKEN_ENV)[0])

    def test_the_default_environment_is_the_process_environment(self):
        with mock.patch.dict(os.environ, {ENV_ADMIN_TOKEN: 'from-process-env'}):
            self.assertTrue(admin_token_required())
            self.assertTrue(admin_check('9.9.9.9', {ADMIN_HEADER: 'from-process-env'})[0])
            self.assertFalse(admin_check('127.0.0.1', {})[0])
        with mock.patch.dict(os.environ):
            os.environ.pop(ENV_ADMIN_TOKEN, None)
            self.assertFalse(admin_token_required())
            self.assertTrue(admin_check('127.0.0.1', {})[0])

    def test_admin_token_required_reflects_configuration(self):
        self.assertTrue(admin_token_required(TOKEN_ENV))
        self.assertFalse(admin_token_required(NO_TOKEN_ENV))


# ================================================================================ job tokens
class JobTokens(unittest.TestCase):
    def test_new_tokens_are_unique_urlsafe_and_long_enough(self):
        tokens = {new_job_token() for _ in range(200)}
        self.assertEqual(len(tokens), 200)
        for t in tokens:
            self.assertGreaterEqual(len(t), 32)                       # 24 random bytes
            self.assertRegex(t, r'^[A-Za-z0-9_-]+$')

    def test_hash_is_sha256_hex_deterministic_and_not_the_token(self):
        t = new_job_token()
        h = hash_token(t)
        self.assertRegex(h, r'^[0-9a-f]{64}$')
        self.assertEqual(h, hash_token(t))
        self.assertNotEqual(h, t)
        self.assertNotIn(t, h)
        self.assertNotEqual(h, hash_token(t + 'x'))

    def test_hash_of_nothing_is_defined(self):
        self.assertEqual(hash_token(''), hash_token(None))            # type: ignore[arg-type]

    def test_the_right_token_matches_its_hash(self):
        t = new_job_token()
        self.assertTrue(token_matches(t, hash_token(t)))

    def test_a_different_token_does_not_match(self):
        a, b = new_job_token(), new_job_token()
        self.assertFalse(token_matches(a, hash_token(b)))
        self.assertFalse(token_matches(a + ' ', hash_token(a)))
        self.assertFalse(token_matches(a.upper(), hash_token(a)))

    def test_empty_token_or_empty_hash_never_matches(self):
        t = new_job_token()
        self.assertFalse(token_matches('', hash_token('')))           # the hash of "" must not unlock anything
        self.assertFalse(token_matches('', hash_token(t)))
        self.assertFalse(token_matches(t, ''))
        self.assertFalse(token_matches(None, hash_token(t)))          # type: ignore[arg-type]
        self.assertFalse(token_matches(t, None))                      # type: ignore[arg-type]

    def test_presenting_the_stored_hash_is_not_the_token(self):
        """A leaked database row must not be usable as the credential."""
        t = new_job_token()
        self.assertFalse(token_matches(hash_token(t), hash_token(t)))

    def test_match_uses_constant_time_compare(self):
        t = new_job_token()
        with mock.patch.object(security.hmac, 'compare_digest', wraps=security.hmac.compare_digest) as spy:
            token_matches(t, hash_token(t))
        spy.assert_called_once()

    def test_header_names_are_the_documented_ones(self):
        self.assertEqual(ADMIN_HEADER, 'X-GovOS-Admin-Token')
        self.assertEqual(JOB_TOKEN_HEADER, 'X-GovOS-Job-Token')


# ============================================================================== rate limiter
class RateLimiterTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.limiter = RateLimiter(clock=self.clock)

    def test_allows_up_to_the_limit_then_refuses(self):
        for i in range(8):
            ok, wait = self.limiter.allow('ask:1.2.3.4', 8, 60)
            self.assertTrue(ok, f'hit {i}')
            self.assertEqual(wait, 0)
        ok, wait = self.limiter.allow('ask:1.2.3.4', 8, 60)
        self.assertFalse(ok)
        self.assertGreaterEqual(wait, 1)

    def test_the_wait_is_when_the_oldest_hit_leaves_the_window(self):
        self.limiter.allow('k', 2, 60)                    # t = 1000
        self.clock.advance(10)
        self.limiter.allow('k', 2, 60)                    # t = 1010
        self.clock.advance(10)                            # t = 1020: oldest leaves at 1060 -> 40 s (+1 rounding)
        ok, wait = self.limiter.allow('k', 2, 60)
        self.assertFalse(ok)
        self.assertIn(wait, (40, 41))

    def test_the_window_slides(self):
        self.assertTrue(self.limiter.allow('k', 2, 60)[0])
        self.clock.advance(30)
        self.assertTrue(self.limiter.allow('k', 2, 60)[0])
        self.assertFalse(self.limiter.allow('k', 2, 60)[0])
        self.clock.advance(31)                            # the first hit (t=0) is now 61 s old
        self.assertTrue(self.limiter.allow('k', 2, 60)[0])
        self.assertFalse(self.limiter.allow('k', 2, 60)[0])   # the second (t=30) and the new one remain
        self.clock.advance(30)                            # t=30 hit is now 61 s old
        self.assertTrue(self.limiter.allow('k', 2, 60)[0])

    def test_everything_is_allowed_again_after_a_full_window(self):
        for _ in range(4):
            self.assertTrue(self.limiter.allow('k', 4, 60)[0])
        self.assertFalse(self.limiter.allow('k', 4, 60)[0])
        self.clock.advance(61)
        for _ in range(4):
            self.assertTrue(self.limiter.allow('k', 4, 60)[0])

    def test_a_refused_hit_is_not_recorded(self):
        """Hammering a closed door must not keep it closed."""
        self.assertTrue(self.limiter.allow('k', 1, 60)[0])
        for _ in range(50):
            self.assertFalse(self.limiter.allow('k', 1, 60)[0])
            self.clock.advance(1)
        self.clock.advance(20)                            # 70 s after the one recorded hit
        self.assertTrue(self.limiter.allow('k', 1, 60)[0])

    def test_keys_are_independent(self):
        for _ in range(4):
            self.assertTrue(self.limiter.allow('practice:1.1.1.1', 4, 60)[0])
        self.assertFalse(self.limiter.allow('practice:1.1.1.1', 4, 60)[0])
        self.assertTrue(self.limiter.allow('practice:2.2.2.2', 4, 60)[0])
        self.assertTrue(self.limiter.allow('ask:1.1.1.1', 4, 60)[0])

    def test_limits_and_windows_are_per_call(self):
        self.assertTrue(self.limiter.allow('k', 1, 5)[0])
        self.assertFalse(self.limiter.allow('k', 1, 5)[0])
        self.clock.advance(6)
        self.assertTrue(self.limiter.allow('k', 1, 5)[0])

    def test_wait_is_at_least_one_second(self):
        self.limiter.allow('k', 1, 60)
        self.clock.advance(59.9)
        ok, wait = self.limiter.allow('k', 1, 60)
        self.assertFalse(ok)
        self.assertGreaterEqual(wait, 1)

    def test_zero_limit_always_refuses(self):
        ok, wait = self.limiter.allow('k', 0, 60)
        self.assertFalse(ok)

    def test_reset_clears_every_key(self):
        for key in ('a', 'b'):
            self.assertTrue(self.limiter.allow(key, 1, 60)[0])
            self.assertFalse(self.limiter.allow(key, 1, 60)[0])
        self.limiter.reset()
        for key in ('a', 'b'):
            self.assertTrue(self.limiter.allow(key, 1, 60)[0])

    def test_concurrent_callers_never_exceed_the_limit(self):
        results: list = []
        lock = threading.Lock()
        barrier = threading.Barrier(16)

        def hit():
            barrier.wait()
            for _ in range(5):
                r = self.limiter.allow('shared', 10, 60)[0]
                with lock:
                    results.append(r)

        threads = [threading.Thread(target=hit) for _ in range(16)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        self.assertEqual(len(results), 80)
        self.assertEqual(sum(results), 10)

    def test_default_clock_is_monotonic(self):
        limiter = RateLimiter()
        self.assertTrue(limiter.allow('k', 1, 60)[0])
        self.assertFalse(limiter.allow('k', 1, 60)[0])


if __name__ == '__main__':
    unittest.main()
