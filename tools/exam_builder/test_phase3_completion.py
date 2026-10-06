"""Phase 3 completion: the REAL unknown exam reaches gate PASS -> materialized -> registered.

The root cause this suite closes: `build.py` recorded one status, NOT_EXTRACTED, for three
different situations (no reader exists; a reader ran over every acquired source and found no
such clause; a reader actually failed), and `gate.py` blocked on *any* NOT_EXTRACTED regardless
of whether the contract requires the field. The fix is generic and never collapses a state:

  * `faqs` and `exam_day_checklist` readers now exist and run through the same dispatch.
  * Bounded re-acquisition issues one domain-restricted query per unpopulated field and records
    which fields it actually searched for.
  * Completeness names the state from the evidence: SOURCE_NOT_FOUND_AFTER_SEARCH (readers ran
    and the domain was searched), EXTRACTION_FAILED (a reader raised on present content),
    NOT_APPLICABLE (explicit, cited), NOT_YET_PUBLISHED (the authority's listing), and
    INFRASTRUCTURE_FAILURE -- with the record's own status left exactly as read.
  * The gate consults the contract's `required` flag: a required field that could not be read
    still blocks; an optional one is allowed through *as* our gap, state preserved.

Everything here drives the real pipeline, the real gate, the real materializer, the real
registry and the real API; only network I/O is stubbed. `src/data.ts` is fingerprinted around
every test.
"""
from __future__ import annotations

import io
import os
import re
import tempfile
import unittest
from unittest.mock import patch

from . import build as B
from . import discover as D
from . import orchestrate as O
from . import publish as P
from .completeness import CompletenessState, evaluate_completeness
from .discover import DiscoveredDoc, DocKind
from .gate import BuildState, GateDecision, evaluate as gate_evaluate
from .materialize import (EngineState, ExamRegistry, RegistryRejected, RUNTIME_EXAM_REQUIRED,
                          build_exam, materialize_exam, validate_runtime_exam)
from .overlay import ExamFactOverlay, OverlayKind, apply_overlays_to_exam_dict
from .resolve import Authority, ResolvedExam
from . import test_phase2_acquisition as F
from .test_materialize import _passing_build, _passing_record, patch_build, stsb
from ..exam_authoring import extract as X
from ..exam_authoring.record import Citation, ExamRecord, Field, Status
from ..exam_authoring.sources import Document

DATA_TS = os.path.join('src', 'data.ts')


def _fingerprint_live() -> dict:
    with io.open(DATA_TS, encoding='utf-8') as fh:
        return P.fingerprint(fh.read())


# ------------------------------------------------------------------ the real NAEB fixture, whole
NAEB_NOTICE_URL = 'https://naeb.gov.in/notice.html'
NAEB_SYLLABUS_URL = 'https://naeb.gov.in/syllabus.pdf'
NAEB_ADMIT_URL = 'https://naeb.gov.in/admit.pdf'
NAEB_CORR_URL = 'https://naeb.gov.in/corr.pdf'


class _Hit:
    def __init__(self, title, url):
        self.title, self.url, self.host = title, url, 'naeb.gov.in'


def _naeb_search(query, max_results=5, official_only=False):
    """The authority's own domain, as a search would return it: the documents NAEB published."""
    q = query.lower()
    if 'syllabus' in q:
        return [_Hit('Detailed Syllabus of Agricultural Research Scientist Examination 2028', NAEB_SYLLABUS_URL)]
    if 'admit' in q:
        return [_Hit('Notice regarding City Intimation and Admit Card Agricultural Research Scientist Examination 2028', NAEB_ADMIT_URL)]
    if 'corrigendum' in q:
        return [_Hit('Corrigendum to Notice of Agricultural Research Scientist Examination 2028', NAEB_CORR_URL)]
    return []                                   # no FAQ page, no exam-day instructions, no attempts doc


def naeb_full(registry=None, search_fn=_naeb_search):
    resolved = ResolvedExam(query=F.UNKNOWN_EXAM_QUERY, official_name=F.UNKNOWN_OFFICIAL_NAME, year='2028',
                            authority=Authority(name=F.UNKNOWN_AUTHORITY_NAME, domain=F.UNKNOWN_DOMAIN,
                                                confidence=0.95, evidence=['https://naeb.gov.in official portal']),
                            seed_urls=[NAEB_NOTICE_URL])
    docs = [DiscoveredDoc(url=NAEB_NOTICE_URL, kind=DocKind.NOTIFICATION, title='NAEB Scientist 2028 Notice',
                          relevance=D.Relevance.DIRECT, matched=['scientist', '2028'])]
    sources = D.SourceSet(exam_id=F.UNKNOWN_EXAM_ID, authority_domain=F.UNKNOWN_DOMAIN, docs=docs)
    notice = Document(url=NAEB_NOTICE_URL, kind='HTML', text=F.NOTICE_PAGE_HTML, fetched_at='2028-01-10')
    notice.html = F.NOTICE_PAGE_HTML
    loaded = {
        NAEB_NOTICE_URL: notice,
        NAEB_SYLLABUS_URL: Document(url=NAEB_SYLLABUS_URL, kind='PDF', text=F.SEPARATE_SYLLABUS_PDF_TEXT,
                                    pages=[F.SEPARATE_SYLLABUS_PDF_TEXT], fetched_at='2028-01-11'),
        NAEB_ADMIT_URL: Document(url=NAEB_ADMIT_URL, kind='PDF', text=F.ADMIT_CARD_NOTICE_TEXT,
                                 pages=[F.ADMIT_CARD_NOTICE_TEXT], fetched_at='2028-05-10'),
        NAEB_CORR_URL: Document(url=NAEB_CORR_URL, kind='PDF', text=F.CORRIGENDUM_PDF_TEXT,
                                pages=[F.CORRIGENDUM_PDF_TEXT], fetched_at='2028-02-10'),
    }
    with patch.object(B, 'resolve', return_value=resolved), \
         patch.object(B, 'discover', return_value=sources), \
         patch.object(B, '_load', side_effect=lambda d: loaded[d.url]):
        return build_exam(F.UNKNOWN_EXAM_QUERY, '2028', registry=registry or ExamRegistry(':memory:'),
                          search_fn=search_fn)


# ------------------------------------------------------------------ official-evidence fixtures
FAQ_DOC_TEXT = """Zeta Recruitment Board
Frequently Asked Questions - Clerk Examination 2028
Q1. What is the last date to apply? A. The last date for receipt of online applications is 15/02/2028.
Q2. Is there any age relaxation for SC and ST candidates? A. Yes, the upper age limit is relaxable by five years for SC and ST candidates as stated in the notice.
Q3. Can the application fee be paid offline? A. No, the fee must be paid online only.
"""

EXAM_DAY_DOC_TEXT = """Zeta Recruitment Board - Instructions to Candidates
Candidates must report at the examination centre by 8:00 AM. Entry will not be allowed after 8:30 AM.
Candidates must carry the printed admit card and an original photo identity proof. Mobile phones and
calculators are strictly prohibited inside the examination hall. Frisking will be conducted at the gate.
"""


def _pdf(url, text, when='2028-01-01'):
    return Document(url=url, kind='PDF', text=text, pages=[text], fetched_at=when)


class TestPhase3Completion(unittest.TestCase):

    def setUp(self):
        self.before = _fingerprint_live()

    def tearDown(self):
        self.assertEqual(self.before, _fingerprint_live(), 'src/data.ts changed during a test')

    # 1. FAQ extraction from official evidence -----------------------------------------------
    def test_faq_extraction_from_official_evidence(self):
        f = X.faqs(_pdf('https://zeta.gov.in/faq.pdf', FAQ_DOC_TEXT), 'Zeta FAQ')
        self.assertIs(f.status, Status.FOUND)
        qs = [i['question'] for i in f.value]
        self.assertEqual(len(qs), 3)
        self.assertEqual(qs[0], 'What is the last date to apply?')
        self.assertEqual(f.value[0]['answer'], 'The last date for receipt of online applications is 15/02/2028.')
        self.assertEqual(f.value[2]['answer'], 'No, the fee must be paid online only.')
        self.assertTrue(f.citation and f.citation.excerpt)           # provenance carried
        # a notice with no FAQ clauses yields nothing -- never an invented question
        notice = Document(url=NAEB_NOTICE_URL, kind='HTML', text=F.NOTICE_PAGE_HTML, fetched_at='2028-01-10')
        notice.html = F.NOTICE_PAGE_HTML
        self.assertIs(X.faqs(notice, 'NAEB notice').status, Status.NOT_EXTRACTED)

    # 2. Exam-day extraction from official evidence ------------------------------------------
    def test_exam_day_extraction_from_official_evidence(self):
        f = X.exam_day_checklist(_pdf('https://zeta.gov.in/instr.pdf', EXAM_DAY_DOC_TEXT), 'Zeta instructions')
        self.assertIs(f.status, Status.FOUND)
        cats = {i['category'] for i in f.value}
        self.assertEqual(cats, {'TIMING', 'DOCUMENTS', 'ITEMS_PROHIBITED', 'CENTRE_INSTRUCTIONS'})
        for item in f.value:                                          # every item is a sentence from the doc
            self.assertIn(item['description'], ' '.join(EXAM_DAY_DOC_TEXT.split()))
        self.assertTrue(any(i['isMandatory'] for i in f.value))
        # NAEB's admit-card notice states where to view the city, not conduct rules: nothing invented
        self.assertIs(X.exam_day_checklist(_pdf(NAEB_ADMIT_URL, F.ADMIT_CARD_NOTICE_TEXT), 'NAEB admit').status,
                      Status.NOT_EXTRACTED)

    # 3. NOT_APPLICABLE behaviour -------------------------------------------------------------
    def test_not_applicable_behavior(self):
        rec = _passing_record()
        rec.set(Field.not_extracted('cutoffs', 'https://zeta.gov.in', 'cutoffs'))
        sources = D.SourceSet(exam_id=rec.exam_id, authority_domain=rec.official_domain)
        # An explicit, cited applicability decision is a distinct state -- not "not yet
        # published", not "not found after search".
        report = evaluate_completeness(rec, sources, not_applicable={'cutoffs': 'Single-stage recruitment with no cut-off declared in the notice, clause 9'})
        self.assertEqual(report.get_section('cutoffs').state, CompletenessState.NOT_APPLICABLE)
        self.assertEqual(report.not_applicable_count, 1)
        # without the cited decision the same record is NOT_EXTRACTED-and-unsearched -> EXTRACTION_FAILED
        self.assertEqual(evaluate_completeness(rec, sources).get_section('cutoffs').state,
                         CompletenessState.EXTRACTION_FAILED)
        gate = gate_evaluate(rec, completeness=report)
        self.assertIs(gate.decision, GateDecision.PASS)
        self.assertIn('cutoffs', gate.allowed)
        self.assertIs(rec.fields['cutoffs'].status, Status.NOT_EXTRACTED)   # never rewritten
        exam = materialize_exam(rec, cycle='2028', completeness=report, gate=gate)
        self.assertEqual(exam['sectionStates']['cutoffs']['state'], 'NOT_APPLICABLE')
        self.assertEqual(exam['cutoffsHistory'], [])

    # 4. EXTRACTION_FAILED behaviour ----------------------------------------------------------
    def test_extraction_failed_behavior(self):
        rec = _passing_record()
        rec.set(Field.not_extracted('attempts', 'https://zeta.gov.in', 'attempts'))
        rec.note('attempts failed on https://zeta.gov.in/notice: ValueError("bad clause")')   # the reader raised
        sources = D.SourceSet(exam_id=rec.exam_id, authority_domain=rec.official_domain)
        report = evaluate_completeness(rec, sources, searched_not_found=frozenset({'attempts'}))
        # a reader that threw on present content is EXTRACTION_FAILED even though a search ran
        self.assertEqual(report.get_section('eligibility').fields['attempts'], 'EXTRACTION_FAILED')
        self.assertIs(rec.fields['attempts'].status, Status.NOT_EXTRACTED)

    # 5. SOURCE_NOT_FOUND_AFTER_SEARCH behaviour (the real NAEB) ------------------------------
    def test_source_not_found_after_search_behavior(self):
        res = naeb_full()
        rec = res.orchestration.build.record
        secs = {s['sectionId']: s for s in res.completeness['sections']}
        for field, section in (('attempts', 'eligibility'), ('faqs', 'faqs'), ('examDayChecklist', 'exam-day')):
            self.assertIs(rec.fields[field].status, Status.NOT_EXTRACTED)        # status untouched
            self.assertEqual(secs[section]['fields'][field], 'SOURCE_NOT_FOUND_AFTER_SEARCH')
        self.assertEqual(secs['faqs']['state'], 'SOURCE_NOT_FOUND_AFTER_SEARCH')
        self.assertNotEqual(secs['faqs']['state'], 'NOT_YET_PUBLISHED')            # no claim about the authority
        self.assertGreaterEqual(res.completeness['reacquisitionAttempts'], 4)   # every unpopulated field was searched
        self.assertGreaterEqual(res.completeness['sourceNotFoundCount'], 2)

    # 6. Infrastructure-failure behaviour ----------------------------------------------------
    def test_infrastructure_failure_behavior(self):
        rec = _passing_record()
        rec.set(Field.not_extracted('faqs', 'https://zeta.gov.in', 'faqs'))
        sources = D.SourceSet(exam_id=rec.exam_id, authority_domain=rec.official_domain)
        sources.infrastructure_failed = True
        sources.infrastructure_note = 'DNS timeout'
        report = evaluate_completeness(rec, sources, searched_not_found=frozenset({'faqs'}))
        self.assertEqual(report.get_section('faqs').state, CompletenessState.INFRASTRUCTURE_FAILURE)
        gate = gate_evaluate(rec, build_state=BuildState.PAUSED_INFRASTRUCTURE, completeness=report)
        self.assertIs(gate.decision, GateDecision.BLOCK)                          # an outage never publishes
        self.assertTrue(any(b.field == '(build)' for b in gate.blockers))

    # 7. Real NAEB: gate PASS -----------------------------------------------------------------
    def test_real_naeb_gate_pass(self):
        res = naeb_full()
        self.assertEqual(res.gate['decision'], 'PASS', res.gate['blockers'])
        self.assertEqual(res.gate['blockers'], [])
        rec = res.orchestration.build.record
        for name in ('officialName', 'authority', 'applicationPortal', 'dates',          # the required four
                     'examPattern', 'syllabus', 'admitCard', 'corrigenda', 'posts', 'vacancies',
                     'ageLimits', 'qualification', 'fee'):
            self.assertIs(rec.fields[name].status, Status.FOUND, name)
        self.assertIn(NAEB_SYLLABUS_URL, rec.sources_read)                       # re-acquired
        self.assertIn(NAEB_ADMIT_URL, rec.sources_read)

    # 8. Real NAEB: materialization -----------------------------------------------------------
    def test_real_naeb_materialization(self):
        res = naeb_full()
        exam = res.exam
        self.assertIsNotNone(exam)
        self.assertEqual(validate_runtime_exam(exam), [])
        # canonical syllabus and pattern reach the typed trees the UI renders, node by node
        self.assertTrue(exam['syllabusTree'])
        self.assertTrue(all(n.get('provenance', {}).get('officialUrl') for n in exam['syllabusTree']))
        self.assertTrue(exam['patternTree'])
        for node in exam['patternTree']:
            self.assertIn(node['level'], {'STAGE', 'PAPER', 'SUBJECT', 'SECTION', 'PART', 'OTHER'})
            self.assertTrue(node['name'])
        self.assertEqual(exam['patternTree'][0]['marks'], 200)
        self.assertEqual(exam['patternTree'][0]['children'][0]['durationMinutes'], 120)
        # the corrigendum the authority issued is a CorrigendumNotice, in its own words
        self.assertTrue(exam['corrigendums'])
        self.assertIn('15/02/2028', exam['corrigendums'][0]['summary'])
        self.assertEqual(exam['corrigendums'][0]['status'], 'ACTIVE')
        # what was not sourced stays an honest empty; nothing invented
        self.assertEqual(exam['faqs'], [])
        self.assertNotIn('examDayChecklist', exam)
        # The flat syllabus is projected from the tree so the tree map, the topic checklist
        # and the weightage view (which all read exam.syllabus) render; the tree stays the
        # source of record. Same content, the shape those views need — nothing invented, and
        # nothing weighted (the authority printed no weightage).
        self.assertTrue(exam['syllabus'])
        self.assertTrue(all(t['topicName'] and t['subject'] and t['officialProvenance'] for t in exam['syllabus']))
        self.assertTrue(all(t['weightagePercentage'] == 0 and not t['isHighYield'] for t in exam['syllabus']))
        # The notice names the posts but prints no Group: they are published by name with an
        # empty classification (never inferred), and listed as such. Dropping them lost two
        # verified post names; the projection contract no longer allows that.
        self.assertEqual([p['postName'] for p in exam['posts']], ['Scientist (Agronomy)', 'Scientist (Genetics)'])
        self.assertTrue(all(p['classification'] == '' for p in exam['posts']))
        self.assertEqual(exam['materialization']['postsWithoutPrintedGroup'],
                         ['Scientist (Agronomy)', 'Scientist (Genetics)'])

    # 9. Real NAEB: registry insertion --------------------------------------------------------
    def test_real_naeb_registry_insertion(self):
        reg = ExamRegistry(':memory:')
        res = naeb_full(reg)
        self.assertEqual(res.state, EngineState.REGISTERED, res.reason)
        self.assertEqual(res.registry['status'], 'REGISTERED')
        self.assertEqual(res.registry['cycle'], '2028')
        got = reg.get(res.registry['examId'])
        self.assertIsNotNone(got)
        self.assertTrue(got.published)
        self.assertEqual(got.exam['authorityName'], F.UNKNOWN_AUTHORITY_NAME)
        self.assertIn('faqs', got.completeness['sections'][13]['fields'])          # completeness persisted

    # 10. Real NAEB: GET /api/exams and GET /api/exams/<id> ----------------------------------
    def test_real_naeb_get_api_exams(self):
        import app as flask_app
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, 'api.db')
            res = naeb_full(ExamRegistry(db))
            self.assertEqual(res.state, EngineState.REGISTERED, res.reason)
            with patch.object(flask_app, 'DB_FILE', db):
                client = flask_app.app.test_client()
                listing = client.get('/api/exams').get_json()
                self.assertEqual(listing['count'], 1)
                self.assertTrue(listing['exams'][0]['id'].startswith('exam-naeb-'))
                one = client.get(f"/api/exams/{res.registry['examId']}").get_json()
                self.assertEqual(one['exam']['title'], F.UNKNOWN_OFFICIAL_NAME)
                self.assertEqual(one['origin'], 'MACHINE_ACQUIRED')
                self.assertEqual(validate_runtime_exam(one['exam']), [])
                self.assertEqual(client.get(f"/api/exams/{res.registry['examId']}?cycle=2027").status_code, 404)

    # 11. Real NAEB: 17-section projection ---------------------------------------------------
    def test_real_naeb_17_section_projection(self):
        res = naeb_full()
        exam = res.exam
        states = exam['sectionStates']
        self.assertEqual(len(states), 17)
        want = {
            'overview': 'VERIFIED_AVAILABLE', 'dates': 'VERIFIED_AVAILABLE', 'eligibility': 'VERIFIED_AVAILABLE',
            'application': 'VERIFIED_AVAILABLE', 'pattern': 'VERIFIED_AVAILABLE', 'syllabus': 'VERIFIED_AVAILABLE',
            'admit-card': 'VERIFIED_AVAILABLE', 'corrigenda': 'VERIFIED_AVAILABLE', 'resources': 'VERIFIED_AVAILABLE',
            'official-links': 'VERIFIED_AVAILABLE',
            # Changed expectation: the roadmap is now a deterministic study order over the
            # verified syllabus (GOVOS_GUIDANCE, `studyGuidance`), so it is supported and
            # projected. Mock tests still have no verified question source.
            'roadmap': 'SUPPORTED_AND_PROJECTED', 'mock-tests': 'NOT_YET_GENERATED',
            'exam-day': 'SOURCE_NOT_FOUND_AFTER_SEARCH', 'faqs': 'SOURCE_NOT_FOUND_AFTER_SEARCH',
            # Changed expectation: no paper or cut-off document was found, which is a search that came
            # up empty, not the authority's own listing showing none -- never "not published yet".
            # Results stay "not published yet": the builder read that no result is declared.
            'pyqs': 'SOURCE_NOT_FOUND_AFTER_SEARCH', 'results': 'NOT_YET_PUBLISHED',
            'cutoffs': 'SOURCE_NOT_FOUND_AFTER_SEARCH',
        }
        for sid, st in want.items():
            self.assertEqual(states[sid]['state'], st, sid)
        # and every overlay domain still projects onto the materialized exam
        prov = {'documentTitle': 'N', 'officialUrl': 'https://naeb.gov.in/n',
                'verificationLevel': 'OFFICIALLY_VERIFIED', 'excerptText': 'x'}
        o = ExamFactOverlay(id='ov-naeb', exam_id=exam['id'], cycle='2028', domain='faqs', kind=OverlayKind.ADD,
                            value={'question': 'Q?', 'answer': 'A.', 'officialClause': 'Para 1'}, provenance=prov)
        self.assertEqual(len(apply_overlays_to_exam_dict(exam, [o])['faqs']), 1)

    # 12. Zeta structural-variation regression -----------------------------------------------
    def test_zeta_structural_variation_regression(self):
        rec = _passing_record()
        real_build = O.build
        patch_build(self, lambda *a, **k: _passing_build(rec))
        reg = ExamRegistry(':memory:')
        res = build_exam('Zeta Clerk', 2028, registry=reg, search_fn=lambda q, **kw: [])
        self.assertEqual(res.state, EngineState.REGISTERED, res.reason)
        # the prose-notice STSB exam registers on the same generic path, with its own honest gaps
        # (the real build is restored first: stsb() drives the real pipeline, not the Zeta stub)
        O.build = real_build
        s = stsb(reg)
        self.assertEqual(s.state, EngineState.REGISTERED, s.reason)
        self.assertEqual(s.exam['applicationGuide']['officialPortal'], 'https://stsb.gov.in/recruitment/apply')
        self.assertEqual(len(reg.list_published()), 2)

    # 13. Authored exam isolation --------------------------------------------------------------
    def test_authored_exam_isolation(self):
        reg = ExamRegistry(':memory:')
        naeb_full(reg)
        self.assertEqual(self.before, _fingerprint_live())
        authored = _passing_record(exam_id='exam-upsc-cse-2026', title='Civil Services (Preliminary) Examination',
                                   authority='Union Public Service Commission', domain='https://upsc.gov.in', year='2026')
        with self.assertRaises(RegistryRejected):
            reg.register(authored, gate=gate_evaluate(authored), exam=materialize_exam(authored, cycle='2026'), cycle='2026')
        self.assertIsNone(reg.get('exam-upsc-cse-2026'))
        self.assertEqual([r.exam_id for r in reg.list_published()], [naeb_full(reg).registry['examId']])

    # 14. No exam-specific branches ----------------------------------------------------------
    def test_no_exam_specific_branches(self):
        here = os.path.dirname(__file__)
        files = [os.path.join(here, n) for n in ('materialize.py', 'gate.py', 'completeness.py', 'build.py')]
        files.append(os.path.join(here, '..', 'exam_authoring', 'extract.py'))
        for path in files:
            with io.open(path, encoding='utf-8') as fh:
                code = '\n'.join(l for l in fh.read().splitlines() if not l.strip().startswith('#'))
            for pat in (r"if\s+exam\s*==", r"if\s+authority\s*==", r"==\s*['\"]exam-",
                        r"\bNAEB\b", r"\bSTSB\b", r"if\s+[^\n]*['\"](?:SSC|UPSC|IBPS|APPSC|LIC)['\"]"):
                self.assertIsNone(re.search(pat, code), f'forbidden branch {pat!r} in {os.path.basename(path)}')


if __name__ == '__main__':
    unittest.main(verbosity=2)
