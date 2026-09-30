"""Designation identity: the additive mode for exams named only by common words.

Fixtures are title blocks written in one real authority's own wording (a central bank's Grade
'B' recruitment, used only as the validation case); nothing in the code under test names it.
The local model is replaced by a fake provider, so these tests never need a running server.

Run: python -m unittest tools.exam_builder.test_designation
"""
from __future__ import annotations

import json
import unittest
from dataclasses import replace
from types import SimpleNamespace

from . import build as B
from . import designation as D
from .discover import DocKind, Relevance, gate, page_is_specific_to
from .identity import ExamIdentity, IdentityVerdict, designation_mode, field_is_attributable, verify
from .pattern import may_supply_pattern

AUTH = 'Reserve Bank of India'
DOMAIN = 'https://opportunities.example.gov.in'
QUERY = 'RBI Officers in Grade B (DR) 2026'


def target(**kw) -> ExamIdentity:
    base = dict(exam_id='exam-x', query=QUERY, official_name=QUERY, year='2026',
                authority_name=AUTH, authority_domain=DOMAIN)
    base.update(kw)
    return ExamIdentity(**base)


def page(title: str, body: str = 'Applications are invited from eligible candidates.') -> str:
    return f'Reserve Bank of India Date : Apr 29, 2026 {title} {body}'


ADVERT = page("Direct Recruitment for the Posts of Officers in Grade ‘B’ (Direct Recruit-DR) "
              "(On Probation-OP) (General/DEPR/DSIM) Cadres - Panel Year - 2026 in Reserve Bank "
              "of India (RBI)",
              "Post Number of Vacancies GEN/UR EWS OBC SC ST Total 1 Officers in Grade ‘B’ (DR) - "
              "General Cadre 16 4 9 7 4 40 2 Officers in Grade ‘B’ (DR) – DEPR Cadre 4 1 1 3 1 10 "
              "3 Officers in Grade ‘B’ (DR) – DSIM Cadre 4 1 4 1 - 10")
RESULT_GENERAL = page("Direct Recruitment for the Posts of Officers in Grade ‘B’ (DR) - General Cadre "
                      "- PY 2026: Result of Phase-II Examination held on July 25, 2026")
RESULT_DEPR = page("Direct Recruitment for the Posts of Officers in Grade ‘B’ (DR) - DEPR Cadre - PY "
                   "2026: Result of Phase-II Examination held on July 26, 2026")
SCORECARD = page("Scorecard and Cut-off marks for Phase-I Examination for Recruitment of Officers in "
                 "Grade ‘B’ (DR) – General Cadre – PY 2026")
HANDOUT = page("1 Information Handout Recruitment of Officers in Grade ‘B’ (DR) - General Cadre - "
               "Panel Year – 2026 Phase-II Examination")
SINGULAR = page("Recruitment for the post of Officer in Grade ‘B’ (DR) - DEPR Cadre - PY 2026")
SPELLED_OUT = page("Recruitment of Officers in Grade ‘B’ (Direct Recruit) - Panel Year 2026")

OTHER_CYCLE = page("Direct Recruitment for the Posts of Officers in Grade ‘B’ (DR) - General Cadre - "
                   "PY 2025: Result of Phase-II Examination")
LEGAL = page("Recruitment for the post of Legal Officer in Grade ‘B’ - Panel Year 2026")
IT_STREAM = page("Direct Recruitment for the Posts of Officers in Grade ‘B’ (Information Technology) - "
                 "Panel Year - 2026 in Reserve Bank of India (RBI)")
GRADE_A = page("Recruitment for the Posts of Assistant Manager in Grade ‘A’ - Panel Year 2026")
MIXED = page("Recruitment of Officers in Grade ‘B’ (DR) - PY 2026 and Recruitment of Legal Officer in "
             "Grade ‘B’ - PY 2026")
UNDECLARED_STREAM = page("Recruitment of Officers in Grade ‘B’ (DR) (Information Technology) - Panel Year 2026")
UNDECLARED_CADRE = page("Recruitment of Officers in Grade ‘B’ (DR) - Legal Cadre - PY 2026")
BARE = page("Notice: Officers in Grade B are informed that the canteen will be closed.")
DEEP = page("Engagement of Medical Consultant on contract basis.",
            'General terms apply. ' * 90 + 'Recruitment of Officers in Grade ‘B’ (DR) - PY 2026.')
FRAGMENTS = page("Direct Recruitment - Phase-II Examination 2026 (ii) Phase-II Examination (iii) "
                 "Paper-III Online Examination Ill) examination")
NO_CYCLE = page("Revised process of recruitment of Officers in Grade-‘B’- (DR)",
                "The selection process has been revised with effect from this year.")


def canonical() -> D.CanonicalDesignation:
    t = target()
    want = D.query_designation(t.query, t.official_name, t.authority_aliases, AUTH)
    canon, notes = D.establish_canonical(want, '2026', [(DOMAIN + '/advt', ADVERT)],
                                         authority_name=AUTH)
    assert canon is not None, notes
    return canon


def canonical_target() -> ExamIdentity:
    return replace(target(), designation=canonical())


class FakeProvider:
    """Stands in for the local model: returns canned replies in order."""

    name = 'fake'

    def __init__(self, *replies, enabled=True, fail=None):
        self.replies = list(replies)
        self.enabled = enabled
        self.fail = fail
        self.calls = 0

    def is_enabled(self):
        return self.enabled

    def complete(self, messages, *, max_tokens=320):
        from .verification.client import ProviderError
        from .verification.schemas import InfraStatus
        self.calls += 1
        if self.fail:
            raise ProviderError(InfraStatus.LLM_UNAVAILABLE, self.fail)
        r = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        return r if isinstance(r, str) else json.dumps(r)


def extraction(**over) -> dict:
    """A well-formed extraction for ADVERT: every string printed in it."""
    out = {
        'designation_core': ['Officers in Grade ‘B’'],
        'qualifiers': ['Direct Recruit-DR', 'On Probation-OP', 'General/DEPR/DSIM'],
        'cycle': '2026',
        'declared_components': ['Officers in Grade ‘B’ (DR) - General Cadre',
                                'Officers in Grade ‘B’ (DR) – DEPR Cadre',
                                'Officers in Grade ‘B’ (DR) – DSIM Cadre'],
        'evidence_spans': ['Direct Recruitment for the Posts of Officers in Grade ‘B’ (Direct Recruit-DR) '
                           '(On Probation-OP) (General/DEPR/DSIM) Cadres - Panel Year - 2026'],
        'confidence': 'high', 'ambiguities': []}
    out.update(over)
    return out


def canonical_with(provider) -> tuple:
    from .verification.designation_llm import extract_designation
    t = target()
    want = D.query_designation(t.query, t.official_name, t.authority_aliases, AUTH)
    return D.establish_canonical(want, '2026', [(DOMAIN + '/advt', ADVERT)], authority_name=AUTH,
                                 extractor=lambda b: extract_designation(b, provider),
                                 llm_enabled=provider.is_enabled())


# ======================================================================== mode and parity
class TestModeSwitch(unittest.TestCase):

    EXISTING = [
        ('SSC CGL 2026', 'SSC Combined Graduate Level Examination 2026', 'Staff Selection Commission', 'https://ssc.gov.in'),
        ('TGPSC Group-I Services 2024', 'Group-I Services', 'Telangana State Public Service Commission', 'https://websitenew.tgpsc.gov.in'),
        ('UPSC Civil Services Examination 2026', 'Civil Services (Preliminary) Examination 2026', 'Union Public Service Commission', 'https://upsc.gov.in'),
        ('HPSC HCS (Executive Branch) and Other Allied Services Examination 2025', '', 'Haryana Public Service Commission', 'https://hpsc.gov.in'),
        ('IBPS PO 2026', 'Common Recruitment Process for Probationary Officers', 'Institute of Banking Personnel Selection', 'https://ibps.in'),
        ('LIC AAO 2027', 'Assistant Administrative Officers', 'Life Insurance Corporation of India', 'https://licindia.in'),
        ('APPSC Group-I Services 2026', '', 'Andhra Pradesh Public Service Commission', 'https://psc.ap.gov.in'),
        ('APPSC Group-II Services 2026', '', 'Andhra Pradesh Public Service Commission', 'https://psc.ap.gov.in'),
        ('BPSC 72nd Combined Competitive Examination', '', 'Bihar Public Service Commission', 'https://bpsc.bihar.gov.in'),
        ('RPSC RAS 2026', 'Rajasthan State and Subordinate Services Combined Competitive Examination', 'Rajasthan Public Service Commission', 'https://rpsc.rajasthan.gov.in'),
    ]

    def test_every_exam_built_so_far_stays_on_the_alias_model(self):
        for q, name, auth, dom in self.EXISTING:
            t = ExamIdentity(exam_id='x', query=q, official_name=name or q, year='2026',
                             authority_name=auth, authority_domain=dom)
            self.assertFalse(designation_mode(t), q)

    def test_alias_mode_verdicts_are_the_old_ones(self):
        # verify() dispatches only in designation mode; an alias-mode target is judged exactly
        # as before (the full suite's identity tests are the wider proof).
        t = ExamIdentity(exam_id='x', query='SSC CGL 2026',
                         official_name='SSC Combined Graduate Level Examination 2026', year='2026',
                         authority_name='Staff Selection Commission')
        own = 'Staff Selection Commission Combined Graduate Level Examination, 2026 notice.'
        sibling = 'Staff Selection Commission Combined Higher Secondary Level Examination, 2026 notice.'
        self.assertIs(verify(own, t).verdict, IdentityVerdict.MATCH)
        self.assertIs(verify(sibling, t).verdict, IdentityVerdict.MISMATCH)
        # ... and the designation reader is never consulted for it.
        self.assertIsNone(t.designation)

    def test_a_name_of_common_words_switches_to_designation_mode(self):
        self.assertTrue(designation_mode(target()))
        self.assertEqual(set(target().aliases) - target().authority_aliases, set())


# ===================================================================== canonical designation
class TestCanonical(unittest.TestCase):

    def test_the_notification_establishes_the_canonical_designation(self):
        c = canonical()
        self.assertEqual(c.core, ('officer', 'in', 'grade', 'b'))
        self.assertEqual(c.year, '2026')
        self.assertTrue({'dr', 'direct', 'recruit', 'general', 'depr', 'dsim'} <= c.qualifiers)
        self.assertEqual(c.basis, 'deterministic')
        self.assertTrue(all(D.normalise_ws(e) in D.normalise_ws(ADVERT) for e in c.evidence))

    def test_only_a_notification_can_establish_it(self):
        # The builder offers only NOTIFICATION documents: a result page, scorecard or listing
        # cannot establish the recruitment's designation, so every document stays AMBIGUOUS.
        docs = [SimpleNamespace(url=DOMAIN + '/result', kind=DocKind.RESULT),
                SimpleNamespace(url=DOMAIN + '/score', kind=DocKind.CUTOFF)]
        loaded = {DOMAIN + '/result': SimpleNamespace(all_text=lambda: RESULT_GENERAL),
                  DOMAIN + '/score': SimpleNamespace(all_text=lambda: SCORECARD)}
        rec = SimpleNamespace(note=lambda m: None)
        t = B._establish_designation(target(), SimpleNamespace(docs=docs), loaded, rec,
                                     provider=FakeProvider(enabled=False))
        self.assertIsNone(t.designation)
        self.assertIs(verify(RESULT_GENERAL, t).verdict, IdentityVerdict.AMBIGUOUS)

    def test_a_notification_off_the_authoritys_own_site_cannot_establish_it(self):
        docs = [SimpleNamespace(url='https://elsewhere.example.com/advt', kind=DocKind.NOTIFICATION)]
        loaded = {'https://elsewhere.example.com/advt': SimpleNamespace(all_text=lambda: ADVERT)}
        notes = []
        t = B._establish_designation(target(), SimpleNamespace(docs=docs), loaded,
                                     SimpleNamespace(note=notes.append),
                                     provider=FakeProvider(enabled=False))
        self.assertIsNone(t.designation)
        self.assertTrue(any('not on the authority' in n for n in notes))

    def test_the_notification_is_found_by_the_builder(self):
        docs = [SimpleNamespace(url=DOMAIN + '/advt', kind=DocKind.NOTIFICATION),
                SimpleNamespace(url=DOMAIN + '/result', kind=DocKind.RESULT)]
        loaded = {DOMAIN + '/advt': SimpleNamespace(all_text=lambda: ADVERT),
                  DOMAIN + '/result': SimpleNamespace(all_text=lambda: RESULT_GENERAL)}
        t = B._establish_designation(target(), SimpleNamespace(docs=docs), loaded,
                                     SimpleNamespace(note=lambda m: None),
                                     provider=FakeProvider(enabled=False))
        self.assertIsNotNone(t.designation)
        self.assertEqual(t.designation.source_url, DOMAIN + '/advt')

    def test_two_notifications_for_different_recruitments_give_none(self):
        t = target(query='RBI Officers in Grade B 2026', official_name='RBI Officers in Grade B 2026')
        want = D.query_designation(t.query, t.official_name, t.authority_aliases, AUTH)
        canon, notes = D.establish_canonical(want, '2026', [(DOMAIN + '/a', ADVERT), (DOMAIN + '/b', IT_STREAM)],
                                             authority_name=AUTH)
        self.assertIsNone(canon)
        self.assertTrue(any('different recruitments' in n for n in notes))

    def test_no_canonical_means_every_document_is_ambiguous(self):
        for text in (ADVERT, RESULT_GENERAL, LEGAL, OTHER_CYCLE):
            self.assertIs(verify(text, target()).verdict, IdentityVerdict.AMBIGUOUS)


# ======================================================================== the model's output
class TestModelOutput(unittest.TestCase):

    def test_a_valid_extraction_adds_the_components_the_notice_declares(self):
        canon, notes = canonical_with(FakeProvider(extraction()))
        self.assertIsNotNone(canon, notes)
        self.assertEqual(canon.basis, 'deterministic+qwen')
        self.assertTrue({'depr', 'dsim', 'cadre'} <= canon.components)
        self.assertNotIn('officer', canon.qualifiers)          # core words are never qualifiers
        self.assertTrue(all(D.normalise_ws(e) in D.normalise_ws(ADVERT) for e in canon.evidence))

    def test_evidence_is_required(self):
        canon, notes = canonical_with(FakeProvider(extraction(evidence_spans=[])))
        self.assertIsNone(canon)
        self.assertTrue(any('no evidence span' in n for n in notes))

    def test_an_evidence_span_not_in_the_notice_is_refused(self):
        canon, notes = canonical_with(FakeProvider(extraction(
            evidence_spans=['Recruitment of Officers in Grade B (DR) for 2026 across all cadres'])))
        self.assertIsNone(canon)
        self.assertTrue(any('not printed in the notification' in n for n in notes))

    def test_a_hallucinated_component_is_refused(self):
        canon, notes = canonical_with(FakeProvider(extraction(
            declared_components=['Officers in Grade ‘B’ (DR) – Information Technology Cadre'])))
        self.assertIsNone(canon)
        self.assertTrue(any('declared_components item not printed' in n for n in notes))

    def test_a_hallucinated_designation_is_refused(self):
        canon, notes = canonical_with(FakeProvider(extraction(designation_core=['Officers in Grade ‘A’'])))
        self.assertIsNone(canon)

    def test_a_printed_heading_misread_as_a_component_is_only_set_aside(self):
        canon, notes = canonical_with(FakeProvider(extraction(
            declared_components=['GEN/UR', 'Officers in Grade ‘B’ (DR) – DSIM Cadre'])))
        self.assertIsNotNone(canon, notes)
        self.assertIn('dsim', canon.components)
        self.assertNotIn('gen', canon.components | canon.qualifiers)
        self.assertTrue(any('set aside' in n for n in notes))

    def test_a_qualifier_printed_away_from_the_designation_is_refused(self):
        canon, notes = canonical_with(FakeProvider(extraction(
            qualifiers=['Direct Recruit-DR', 'Total'],
            evidence_spans=extraction()['evidence_spans'] + ['Total 1 Officers'])))
        self.assertIsNone(canon)
        self.assertTrue(any('same statement' in n for n in notes))

    def test_conflicting_designations_are_ambiguous(self):
        canon, notes = canonical_with(FakeProvider(extraction(
            designation_core=['Officers in Grade ‘B’', 'Posts of Officers'])))
        self.assertIsNone(canon)
        self.assertTrue(any('disagree' in n for n in notes))

    def test_a_declared_ambiguity_is_ambiguous(self):
        canon, notes = canonical_with(FakeProvider(extraction(
            ambiguities=['the notice names three cadres'])))
        self.assertIsNone(canon)

    def test_output_outside_the_contract_is_refused(self):
        for bad in ('not json at all', {'designation_core': ['Officers in Grade ‘B’'], 'verdict': 'MATCH',
                                        'evidence_spans': ['Officers in Grade ‘B’']}):
            canon, notes = canonical_with(FakeProvider(bad))
            self.assertIsNone(canon, bad)

    def test_an_unreachable_model_that_is_enabled_gives_no_canonical(self):
        canon, notes = canonical_with(FakeProvider(fail='connection refused'))
        self.assertIsNone(canon)
        self.assertTrue(any('model unavailable' in n for n in notes))

    def test_a_disabled_model_leaves_the_deterministic_reading(self):
        canon, _ = canonical_with(FakeProvider(enabled=False))
        self.assertEqual(canon.basis, 'deterministic')


class TestConfirmationOnlyWithholds(unittest.TestCase):

    def test_confirmed_match_stays_a_match(self):
        p = FakeProvider({'same_recruitment': True, 'reason': 'same designation and cycle',
                          'evidence_span': 'Officers in Grade ‘B’ (DR) - General Cadre - PY 2026'})
        self.assertIs(B._identify(RESULT_GENERAL, canonical_target(), provider=p).verdict,
                      IdentityVerdict.MATCH)

    def test_the_model_can_withhold_a_match(self):
        p = FakeProvider({'same_recruitment': False, 'reason': 'different cadre',
                          'evidence_span': 'Officers in Grade ‘B’ (DR) - General Cadre - PY 2026'})
        self.assertIs(B._identify(RESULT_GENERAL, canonical_target(), provider=p).verdict,
                      IdentityVerdict.AMBIGUOUS)

    def test_the_model_cannot_create_a_match(self):
        p = FakeProvider({'same_recruitment': True, 'reason': 'x', 'evidence_span': 'Legal Officer'})
        for text in (LEGAL, OTHER_CYCLE, BARE, UNDECLARED_STREAM):
            self.assertIsNot(B._identify(text, canonical_target(), provider=p).verdict,
                             IdentityVerdict.MATCH)
        self.assertEqual(p.calls, 0)                     # it is never even asked

    def test_an_unverifiable_confirmation_withholds(self):
        p = FakeProvider({'same_recruitment': True, 'reason': 'x',
                          'evidence_span': 'a sentence the document never prints'})
        self.assertIs(B._identify(RESULT_GENERAL, canonical_target(), provider=p).verdict,
                      IdentityVerdict.AMBIGUOUS)

    def test_an_unreachable_model_withholds(self):
        self.assertIs(B._identify(RESULT_GENERAL, canonical_target(),
                                  provider=FakeProvider(fail='timeout')).verdict,
                      IdentityVerdict.AMBIGUOUS)


# ============================================================================ the four callers
class TestEveryCallerUsesTheSameMatcher(unittest.TestCase):

    def test_main_verdict(self):
        t = canonical_target()
        self.assertIs(verify(RESULT_DEPR, t).verdict, IdentityVerdict.MATCH)
        self.assertIs(verify(LEGAL, t).verdict, IdentityVerdict.MISMATCH)

    def test_listing_rows(self):
        from ..exam_authoring.sources import Document
        rows = ''.join(f'<tr><td>{r}</td></tr>' for r in (
            'Direct Recruitment for the Posts of Officers in Grade ‘B’ (DR) - DSIM Cadre - PY 2026: Result',
            'Lateral Recruitment of Site Engineers on Full-Time Contract Basis - PY 2026',
            'Recruitment for the post of Legal Officer in Grade ‘B’ - Panel Year 2026'))
        doc = Document(url=DOMAIN + '/results', kind='HTML', fetched_at='2026-09-30', text='listing')
        doc.html = f'<table>{rows}</table>'
        entry = B._listing_entry(doc, canonical_target())
        self.assertIsNotNone(entry)
        self.assertIn('DSIM Cadre', entry.text)
        self.assertNotIn('Legal Officer', entry.text)
        self.assertNotIn('Site Engineers', entry.text)

    def test_span_attribution_never_rescues_an_ambiguous_document(self):
        t = canonical_target()
        # "RBI Recruitment 2026" could be any of the authority's recruitments that year.
        text = MIXED + ' RBI Recruitment 2026 schedule: Phase-I on 01.08.2026.'
        span = 'RBI Recruitment 2026 schedule: Phase-I on 01.08.2026.'
        self.assertIs(verify(text, t).verdict, IdentityVerdict.AMBIGUOUS)
        # The older word-based path would attribute this span -- its only alias is the
        # authority's own -- which is exactly the leak the designation-mode guard closes.
        from .identity import _identifies, exam_references
        self.assertTrue(any(_identifies(r, t) for r in exam_references(span)))
        self.assertFalse(field_is_attributable(text, t, span))

    def test_pattern_and_stage_readers_refuse_ambiguous(self):
        t = canonical_target()
        self.assertTrue(may_supply_pattern(RESULT_GENERAL, t)[0])
        self.assertFalse(may_supply_pattern(MIXED, t)[0])
        self.assertFalse(may_supply_pattern(UNDECLARED_STREAM, t)[0])

    def test_semantic_verifier_refuses_ambiguous(self):
        from unittest import mock
        from .identity import IdentityCheck
        from .verification import deterministic as DET
        from .verification.schemas import Claim
        claim = Claim(exam_id='exam-x', field='x', value='1', evidence_span='PY 2026',
                      source_url=DOMAIN, cycle='2026', authority=AUTH, official_name=QUERY,
                      source_text=MIXED)
        # A claim carries no canonical designation, so its identity is AMBIGUOUS already ...
        self.assertFalse(DET.run_deterministic(claim).identity_ok)
        # ... and even an AMBIGUOUS verdict that names the exam in its title block (the
        # alias-mode escape hatch) is refused in designation mode.
        named = IdentityCheck(IdentityVerdict.AMBIGUOUS, matched=['Officers in Grade ‘B’ (DR)'])
        with mock.patch.object(DET, 'identity_verify', return_value=named):
            self.assertFalse(DET.run_deterministic(claim).identity_ok)

    def test_discovery_link_gate(self):
        want = D.query_designation(QUERY, QUERY, target().authority_aliases, AUTH)
        own = 'Direct Recruitment for the Posts of Officers in Grade ‘B’ (DR) - DEPR Cadre - PY 2026: Result'
        rel, _, _ = gate(own, DOMAIN + '/x', exam_words=target().aliases, page_is_exam_specific=False,
                         designation=want)
        self.assertIs(rel, Relevance.DIRECT)
        rel, _, _ = gate('Recruitment for the post of Legal Officer in Grade ‘B’ - PY 2026', DOMAIN + '/y',
                         exam_words=target().aliases, page_is_exam_specific=True, designation=want)
        self.assertIs(rel, Relevance.REJECTED)
        # The authority's own name, which every link carries, admits nothing.
        rel, _, _ = gate('RBI Kehta Hai', DOMAIN + '/rbi', exam_words=target().aliases,
                         page_is_exam_specific=False, designation=want)
        self.assertIs(rel, Relevance.REJECTED)
        self.assertTrue(page_is_specific_to(own, DOMAIN + '/x', target().aliases, designation=want))

    def test_alias_mode_gate_is_unchanged(self):
        rel, matched, _ = gate('CGL 2026 Notice', 'https://ssc.gov.in/cgl.pdf', exam_words=['cgl'],
                               page_is_exam_specific=False)
        self.assertIs(rel, Relevance.DIRECT)


# ========================================================================= the validation case
class TestValidationMatrix(unittest.TestCase):

    CASES = [
        ('advertisement', ADVERT, 'MATCH'),
        ('Phase-II result, General Cadre', RESULT_GENERAL, 'MATCH'),
        ('Phase-II result, DEPR Cadre', RESULT_DEPR, 'MATCH'),
        ('Phase-I scorecard', SCORECARD, 'MATCH'),
        ('information handout', HANDOUT, 'MATCH'),
        ('singular "Officer"', SINGULAR, 'MATCH'),
        ('spelled-out "(Direct Recruit)"', SPELLED_OUT, 'MATCH'),
        ('same designation, PY 2025', OTHER_CYCLE, 'MISMATCH'),
        ('Legal Officer in Grade B', LEGAL, 'MISMATCH'),
        ('Grade B (Information Technology)', IT_STREAM, 'MISMATCH'),
        ('Assistant Manager in Grade A', GRADE_A, 'MISMATCH'),
        ('mixed recruitment title', MIXED, 'AMBIGUOUS'),
        ('(DR) plus an undeclared stream', UNDECLARED_STREAM, 'AMBIGUOUS'),
        ('(DR) plus an undeclared cadre', UNDECLARED_CADRE, 'AMBIGUOUS'),
        ('bare Grade B', BARE, 'AMBIGUOUS'),
        ('designation only deep in the body', DEEP, 'AMBIGUOUS'),
        ('Direct Recruitment / Roman-numeral fragments', FRAGMENTS, 'AMBIGUOUS'),
        ('no-cycle process page', NO_CYCLE, 'AMBIGUOUS'),
    ]

    def test_matrix(self):
        t = canonical_target()
        for label, text, want in self.CASES:
            with self.subTest(label):
                self.assertEqual(verify(text, t).verdict.value, want)

    def test_every_match_carries_verbatim_evidence(self):
        t = canonical_target()
        for label, text, want in self.CASES:
            chk = verify(text, t, source_url='u')
            if chk.verdict is IdentityVerdict.MATCH:
                self.assertIsNotNone(chk.evidence, label)
                self.assertIn(D.normalise_ws(chk.evidence.span), D.normalise_ws(text), label)


class TestNoExamSpecificCode(unittest.TestCase):

    def test_the_designation_code_names_no_authority_exam_or_cadre(self):
        import io
        import re
        for path in ('tools/exam_builder/designation.py',
                     'tools/exam_builder/verification/designation_llm.py'):
            with io.open(path, encoding='utf-8') as fh:
                src = fh.read()
            code = re.sub(r'"""[\s\S]*?"""', '', src)          # docstrings describe; code decides
            for word in ('rbi', 'reserve bank', 'grade', 'depr', 'dsim', 'legal officer',
                         'panel year 2026', 'officers in'):
                self.assertNotIn(word, code.lower(), f'{word} in {path}')


if __name__ == '__main__':
    unittest.main()
