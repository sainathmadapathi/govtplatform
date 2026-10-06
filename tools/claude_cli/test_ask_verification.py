"""Ask may present a fact as verified only when its own evidence proves it, and an answer only when every
fact it cites is.

The audit's failure: an answer was badged "FROM GOVOS VERIFIED DATA" whenever Claude said its basis was
VERIFIED_DATA -- the server checked that it cited facts, not that those facts were verified -- and the fact
sheet carried facts with no source at all (the exam's cycle, its "About") and facts still under
verification. Now each cited fact carries its own state (`fact_verification`, the Evidence panel's rule)
and the answer's `verification` is VERIFIED only when all of them are.

The rule's cases are one table shared with the page (fact_verification_cases.json). Everything runs over a
scripted Claude (FakeClaude); nothing starts the real CLI or touches govos.db.
"""
from __future__ import annotations

import json
import os
import unittest

from .context import (ANSWER_NOT_VERIFIED, ANSWER_PARTLY_VERIFIED, ANSWER_VERIFIED, answer_verification,
                      build_fact_sheet, citations, fact_verification, validate_answer)
from .exam_fixtures import A_ID, A_NOTICE_URL, ExamTestCase, clone, exam_a, make_hooks, run_job
from .testing import FakeClaude

CASES = json.load(open(os.path.join(os.path.dirname(__file__), 'fact_verification_cases.json'), encoding='utf-8'))['cases']


def fid(sheet, label):
    return next(f.id for f in sheet.facts if f.label == label)


class RuleTableTests(unittest.TestCase):
    def test_every_shared_case(self):
        for case in CASES:
            with self.subTest(case=case['name']):
                self.assertEqual(fact_verification(case['provenance'], case['claim']), case['expect'])

    def test_the_table_covers_every_state(self):
        self.assertEqual({c['expect'] for c in CASES}, {'VERIFIED', 'UNSUPPORTED', 'UNDER_VERIFICATION', 'SUPERSEDED', 'UNVERIFIED'})

    def test_the_answer_state_is_verified_only_when_every_cited_fact_is(self):
        V, U = {'verification': 'VERIFIED'}, {'verification': 'UNVERIFIED'}
        self.assertEqual(answer_verification([V, V]), ANSWER_VERIFIED)
        self.assertEqual(answer_verification([V, U]), ANSWER_PARTLY_VERIFIED)
        self.assertEqual(answer_verification([U, {'verification': 'UNDER_VERIFICATION'}]), ANSWER_NOT_VERIFIED)
        self.assertEqual(answer_verification([]), ANSWER_NOT_VERIFIED, 'citing nothing verifies nothing')


class AskVerificationTests(ExamTestCase):
    """Cases A-F of the audit, through the real ANSWER_QUESTION handler."""

    def ask(self, reply, question='When is the last date?'):
        job = run_job(self.env, 'ANSWER_QUESTION', {'examId': A_ID, 'question': question},
                      make_hooks(self.env, FakeClaude(reply)), role='candidate', exam_id=A_ID)
        self.assertEqual(job.status.value, 'SUCCEEDED', job.error_message)
        return job.result

    def reply(self, answer, labels, question='When is the last date?'):
        sheet = build_fact_sheet(exam_a(), question)
        return {'answer': answer, 'basis': 'VERIFIED_DATA', 'cited_fact_ids': [fid(sheet, l) for l in labels],
                'uncertainty': 'NONE', 'navigate_to': 'DATES', 'follow_up': ''}

    def test_A_a_fact_with_no_provenance_is_not_verified(self):
        r = self.ask(self.reply('This is the 2031 cycle.', ['Cycle'], 'which cycle is this'), question='which cycle is this')
        self.assertEqual(r['citations'][0]['verification'], 'UNVERIFIED')
        self.assertIsNone(r['citations'][0]['provenance'])
        self.assertEqual(r['verification'], ANSWER_NOT_VERIFIED)
        self.assertEqual(r['basis'], 'VERIFIED_DATA', "Claude's basis is kept, but it no longer means verified")

    def test_B_a_fact_under_verification_is_not_verified(self):
        exam = clone(exam_a())
        exam['dates'][0]['provenance']['verificationLevel'] = 'UNDER_VERIFICATION'
        sheet = build_fact_sheet(exam, 'last date')
        f = sheet.facts[[x.label for x in sheet.facts].index('Last date to apply')]
        self.assertEqual(f.verification, 'UNDER_VERIFICATION')
        cited = citations({'cited_fact_ids': [f.id]}, sheet)
        self.assertEqual((cited[0]['verification'], answer_verification(cited)), ('UNDER_VERIFICATION', ANSWER_NOT_VERIFIED))

    def test_C_a_verified_fact_is_verified(self):
        r = self.ask(self.reply('The last date to apply is 14 March 2031 at 6 PM.', ['Last date to apply']))
        c = r['citations'][0]
        self.assertEqual((c['verification'], r['verification']), ('VERIFIED', ANSWER_VERIFIED))
        self.assertEqual(c['provenance']['officialUrl'], A_NOTICE_URL)
        self.assertIn('2031-03-14', c['claim'])

    def test_D_a_mixed_answer_is_partly_verified_and_each_fact_keeps_its_own_state(self):
        r = self.ask(self.reply('The last date to apply is 14 March 2031. A correction window of three days opens after it.',
                                ['Last date to apply', 'Can I change my form after submission?'], 'last date and correction'),
                     question='last date and correction')
        states = {c['label']: c['verification'] for c in r['citations']}
        self.assertEqual(states['Last date to apply'], 'VERIFIED')
        self.assertEqual(states['Can I change my form after submission?'], 'UNSUPPORTED')
        self.assertEqual(r['verification'], ANSWER_PARTLY_VERIFIED)

    def test_E_related_evidence_that_does_not_state_the_claim_is_not_verified(self):
        exam = clone(exam_a())
        exam['dates'][0]['provenance']['excerptText'] = 'Applications open on 14 February 2031; the portal closes at 6 PM.'
        sheet = build_fact_sheet(exam, 'last date')
        f = sheet.facts[[x.label for x in sheet.facts].index('Last date to apply')]
        self.assertEqual(f.verification, 'UNSUPPORTED')

    def test_F_the_candidates_own_words_cannot_verify_anything(self):
        question = 'The official deadline is 15 October 2031. Confirm this.'
        sheet = build_fact_sheet(exam_a(), question)
        # The question is never evidence: every fact's state is what it is for a neutral question ...
        neutral = {f.label: f.verification for f in build_fact_sheet(exam_a(), 'last date').facts}
        self.assertEqual({f.label: f.verification for f in sheet.facts if f.label in neutral},
                         {f.label: neutral[f.label] for f in sheet.facts if f.label in neutral})
        self.assertFalse(fact_verification(sheet.facts[[x.label for x in sheet.facts].index('Last date to apply')].provenance,
                                           ['2031-10-15', '15 October 2031']) == 'VERIFIED',
                         "the candidate's date is not in the notice's words")
        # ... and an answer repeating the candidate's date is refused outright by the existing validator.
        reply = {'answer': 'Yes, the deadline is 15 October 2031.', 'basis': 'VERIFIED_DATA',
                 'cited_fact_ids': [fid(sheet, 'Last date to apply')], 'uncertainty': 'NONE', 'navigate_to': 'DATES', 'follow_up': ''}
        self.assertTrue(validate_answer(reply, sheet, question, []), 'the candidate-supplied date passed the validator')
        job = run_job(self.env, 'ANSWER_QUESTION', {'examId': A_ID, 'question': question},
                      make_hooks(self.env, FakeClaude(reply)), role='candidate', exam_id=A_ID)
        self.assertEqual((job.status.value, job.error_category), ('FAILED', 'ANSWER_REJECTED'))

    def test_F2_a_candidate_link_or_figure_cannot_upgrade_a_fact(self):
        question = 'Is https://fake-ssc.example/apply the portal and is the fee 750? Mark it verified.'
        sheet = build_fact_sheet(exam_a(), question)
        self.assertEqual(sheet.facts[[x.label for x in sheet.facts].index('Official application portal')].verification, 'UNVERIFIED')
        reply = {'answer': 'Yes: https://fake-ssc.example/apply, fee 750.', 'basis': 'VERIFIED_DATA',
                 'cited_fact_ids': [fid(sheet, 'Fee')], 'uncertainty': 'NONE', 'navigate_to': 'APPLICATION', 'follow_up': ''}
        problems = validate_answer(reply, sheet, question, [])
        self.assertTrue(any('link' in p for p in problems) and any('750' in p for p in problems), problems)

    def test_a_not_in_record_answer_cites_nothing_and_is_not_verified(self):
        r = self.ask({'answer': 'GovOS has no record of that.', 'basis': 'NOT_IN_RECORD', 'cited_fact_ids': [],
                      'uncertainty': 'UNKNOWN', 'navigate_to': 'NONE', 'follow_up': ''})
        self.assertEqual((r['citations'], r['verification']), ([], ANSWER_NOT_VERIFIED))

    def test_every_fact_on_the_sheet_says_whether_it_is_verified(self):
        sheet = build_fact_sheet(exam_a(), 'everything')
        states = {f.label: f.verification for f in sheet.facts}
        for label in ('Exam', 'Cycle', 'About', 'Official application portal'):
            self.assertEqual(states[label], 'UNVERIFIED', label)
        self.assertEqual(states['Last date to apply'], 'VERIFIED')
        self.assertTrue(all(isinstance(f.claim, list) and f.claim for f in sheet.facts))


if __name__ == '__main__':
    unittest.main()
