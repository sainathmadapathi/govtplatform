"""Usage statistics read from the CLI's JSON envelope.

Verified against the real CLI (Claude Code 2.1.286): `usage.server_tool_use` stays 0 even when WebSearch ran;
the search count is in `modelUsage.<model>.webSearchRequests`. A stat that always reads 0 would make the
discovery manifest and the audit trail claim that no web tool was used.

Run: python -m unittest tools.claude_cli.test_usage_stats
"""
from __future__ import annotations

import unittest

from .client import ClaudeGateway


class TestStats(unittest.TestCase):

    def test_the_search_count_is_read_from_the_per_model_usage(self):
        env = {'num_turns': 2, 'usage': {'server_tool_use': {'web_search_requests': 0}},
               'modelUsage': {'main-model': {'webSearchRequests': 0}, 'helper-model': {'webSearchRequests': 1}}}
        self.assertEqual(ClaudeGateway._stats(env)['webSearchRequests'], 1)

    def test_the_older_location_still_counts(self):
        env = {'usage': {'server_tool_use': {'web_search_requests': 2}}}
        self.assertEqual(ClaudeGateway._stats(env)['webSearchRequests'], 2)

    def test_turns_are_reported_because_fetch_has_no_counter(self):
        self.assertEqual(ClaudeGateway._stats({'num_turns': 4})['turns'], 4)

    def test_junk_in_the_envelope_reads_as_zero_and_never_raises(self):
        for env in ({}, {'usage': None, 'modelUsage': 'x'}, {'modelUsage': {'m': 'junk'}},
                    {'modelUsage': {'m': {'webSearchRequests': True}}}, {'num_turns': 'many'}):
            with self.subTest(env=env):
                stats = ClaudeGateway._stats(env)
                self.assertEqual((stats['webSearchRequests'], stats['webFetchRequests']), (0, 0))


if __name__ == '__main__':
    unittest.main()
