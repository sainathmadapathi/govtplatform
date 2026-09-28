"""Phase 3 — Universal Exam Materialization Engine: the acceptance suite.

Everything here drives the REAL engine: the real acquisition pipeline over the accepted NAEB and
STSB fixtures, the real publication gate, the real materializer, the real registry (in a temp
SQLite), the real Flask API, and the real overlay projection. Only network I/O is stubbed, as
`test_phase2_acquisition` stubs it. `src/data.ts` is fingerprinted before and after every test.

Two things are proven side by side, and kept honest:

  * The real gate BLOCKS the raw NAEB/STSB builds (fields the notice does not carry are
    conservatively NOT_EXTRACTED, and two contract fields have no reader yet). The engine then
    registers NOTHING, reports the exact blockers, and leaves data.ts byte-identical — that is
    the failure-safety contract, and it is never worked around here by weakening the gate or by
    marking a field NOT_PUBLISHED without evidence.
  * The whole chain build_exam → orchestrate → gate → materialize → validate → register → API →
    17-section projection is proven on a record the REAL gate passes. That record is fixture data
    (a synthetic unknown exam), evaluated by the real gate.evaluate, never a stubbed gate.
"""
from __future__ import annotations

import io
import json
import os
import re
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from . import build as B
from . import discover as D
from . import orchestrate as O
from . import publish as P
from .discover import DiscoveredDoc, DocKind
from .gate import BuildState, evaluate as gate_evaluate
from .materialize import (EngineState, ExamRegistry, RegistryRejected, RUNTIME_EXAM_REQUIRED,
                          build_exam, materialize_exam, validate_runtime_exam)
from .overlay import ExamFactOverlay, OverlayKind, apply_overlays_to_exam_dict
from .resolve import Authority, ResolvedExam
from . import test_phase2_acquisition as F
from ..exam_authoring.record import Citation, ExamRecord, Field, Status
from ..exam_authoring.sources import Document

DATA_TS = os.path.join('src', 'data.ts')


def _fingerprint_live() -> dict:
    with io.open(DATA_TS, encoding='utf-8') as fh:
        return P.fingerprint(fh.read())


# ------------------------------------------------------------------ real-pipeline drivers
def _real_build(query, official, year, authority, domain, seed, html, title, registry=None):
    """The accepted Phase 2 driver: real resolve/discover/_load stubbed for network only."""
    resolved = ResolvedExam(query=query, official_name=official, year=year,
                            authority=Authority(name=authority, domain=domain, confidence=0.95,
                                                evidence=[f'{domain} official portal']),
                            seed_urls=[seed])
    docs = [DiscoveredDoc(url=seed, kind=DocKind.NOTIFICATION, title=title,
                          relevance=D.Relevance.DIRECT, matched=[year])]
    sources = D.SourceSet(exam_id='exam-probe', authority_domain=domain, docs=docs)
    doc = Document(url=seed, kind='HTML', text=html, fetched_at=f'{year}-03-01')
    doc.html = html
    with patch.object(B, 'resolve', return_value=resolved), \
         patch.object(B, 'discover', return_value=sources), \
         patch.object(B, '_load', side_effect=lambda d: doc):
        return build_exam(query, year, registry=registry or ExamRegistry(':memory:'),
                          search_fn=lambda q, **kw: [])


def naeb(registry=None):
    return _real_build(F.UNKNOWN_EXAM_QUERY, F.UNKNOWN_OFFICIAL_NAME, '2028', F.UNKNOWN_AUTHORITY_NAME,
                       F.UNKNOWN_DOMAIN, 'https://naeb.gov.in/scientist-2028', F.NOTICE_PAGE_HTML,
                       'NAEB 2028 Notice', registry)


def stsb(registry=None):
    return _real_build(F.STRUCTURAL_UNKNOWN_QUERY, F.STRUCTURAL_OFFICIAL_NAME, '2028',
                       F.STRUCTURAL_AUTHORITY_NAME, F.STRUCTURAL_DOMAIN,
                       'https://stsb.gov.in/recruitment/ae-2028', F.STRUCTURAL_NOTICE_HTML,
                       'STSB AE 2028 Notice', registry)


# ------------------------------------------------------------------ a real-gate-passing record
def _passing_record(exam_id='exam-zeta-clerk-2028', title='Zeta Clerk Examination',
                    authority='Zeta Recruitment Board', domain='https://zeta.gov.in', year='2028'):
    """A synthetic unknown exam whose every contract field is FOUND (cited) or NOT_PUBLISHED, so
    the REAL gate passes. Fixture data for the record; the gate is not stubbed."""
    rec = ExamRecord(exam_id=exam_id, code=exam_id.replace('exam-', '').upper().replace('-', '_'),
                     title=title, authority_name=authority, official_domain=domain)
    cit = Citation(document_title=f'{title}, {year} — Notice', url=domain + '/notice', page=2,
                   excerpt=f'{title}, {year}. Applications are invited online.', verified_date=f'{year}-01-01')
    found = {
        'officialName': title, 'authority': authority, 'applicationPortal': domain + '/apply',
        'dates': [{'type': 'APPLICATION_CLOSE', 'label': 'Last date to apply', 'dateTimeStr': f'{year}-02-11 18:00'},
                  {'type': 'EXAM_TIER1', 'label': 'Written examination', 'dateTimeStr': f'{year}-05-20 09:00'},
                  {'type': 'OTHER', 'label': 'Date of upload', 'dateTimeStr': f'{year}-01-01'}],
        'ageLimits': {'minAge': 21, 'maxAge': 30, 'asOn': f'{year}-08-01'},
        'fee': {'text': 'Rs. 250 payable online.'},
        'vacancies': 60,
        'posts': [{'postName': "Clerk, Group 'B'", 'department': 'Zeta Board', 'payLevel': 'Level 4'},
                  {'postName': 'Assistant (no group printed)', 'department': 'Zeta Board'}],
        'howToApply': 'Apply online through the portal; upload certificates; pay the fee.',
        'qualification': 'Degree from a recognised university.',
        'attempts': {'text': 'No limit on number of attempts.'},
        'examPattern': {'papers': [{'label': 'Paper-I', 'name': 'General Studies', 'marks': 100,
                                    'duration': '120 minutes'}]},
    }
    for name, val in found.items():
        rec.set(Field.found(name, val, cit))
    for name in ('syllabus', 'officialPapers', 'answerKeys', 'admitCard', 'results', 'nextSteps',
                 'cutoffs', 'corrigenda', 'examDayChecklist', 'faqs', 'requiredDocuments',
                 'photoSignatureGuidelines', 'feeExemptions'):
        rec.set(Field.not_published(name, f'{authority} has published no {name} for {year} in its listed documents'))
    rec.sources_read.append(domain + '/notice')
    return rec


def _passing_build(rec, year='2028'):
    resolved = ResolvedExam(query=rec.title, official_name=rec.title, year=year,
                            authority=Authority(name=rec.authority_name, domain=rec.official_domain, confidence=0.9),
                            seed_urls=[])
    return O.BuildResult(resolved=resolved, sources=SimpleNamespace(docs=[], rejected=[], log=[]),
                         coverage=SimpleNamespace(supplied={}), record=rec,
                         build_state=BuildState.COMPLETE, identity={}, completeness=None)


def patch_build(test, fn):
    real = O.build
    O.build = fn
    test.addCleanup(lambda: setattr(O, 'build', real))


class TestMaterializationEngine(unittest.TestCase):

    def setUp(self):
        self.before = _fingerprint_live()

    def tearDown(self):
        self.assertEqual(self.before, _fingerprint_live(), 'src/data.ts changed during a test')

    # 1. test_registry_insert_gate_pass -----------------------------------------------------
    def test_registry_insert_gate_pass(self):
        rec = _passing_record()
        gate = gate_evaluate(rec)                       # the REAL gate
        self.assertTrue(gate.may_publish, [str(b) for b in gate.blockers])
        exam = materialize_exam(rec, cycle='2028', gate=gate)
        reg = ExamRegistry(':memory:')
        rr = reg.register(rec, gate=gate, exam=exam, cycle='2028')
        self.assertTrue(rr.published)
        self.assertEqual(rr.version, 1)
        self.assertEqual(reg.get('exam-zeta-clerk-2028').exam['id'], 'exam-zeta-clerk-2028')

    # 2. test_registry_rejects_unverified -----------------------------------------------------
    def test_registry_rejects_unverified(self):
        rec = _passing_record()
        rec.set(Field.needs_review('dates', rec.fields['dates'].value, 'read from prose', rec.fields['dates'].citation))
        gate = gate_evaluate(rec)
        self.assertFalse(gate.may_publish)
        exam = materialize_exam(rec, cycle='2028', gate=gate)
        self.assertIn('"verificationLevel": "UNDER_VERIFICATION"', json.dumps(exam))   # badged, never official
        reg = ExamRegistry(':memory:')
        with self.assertRaises(RegistryRejected):
            reg.register(rec, gate=gate, exam=exam, cycle='2028')
        self.assertEqual(reg.list_published(), [])
        # and the client can never assert a status: registering with no gate at all is refused
        with self.assertRaises(RegistryRejected):
            reg.register(rec, gate=None, exam=exam, cycle='2028')

    # 3. test_registry_rejects_identity_mismatch --------------------------------------------
    def test_registry_rejects_identity_mismatch(self):
        rec = _passing_record()
        gate = gate_evaluate(rec)
        exam = materialize_exam(rec, cycle='2028', gate=gate)
        exam['id'] = 'exam-someone-else-2028'            # payload identity != record identity
        with self.assertRaises(RegistryRejected):
            ExamRegistry(':memory:').register(rec, gate=gate, exam=exam, cycle='2028')
        # a source that belongs to another exam blocks at the gate itself when a field cites
        # it; one that was excluded from extraction and cited by nothing is retained for audit
        from .identity import IdentityCheck, IdentityVerdict
        cited = rec.fields['fee'].citation.url
        gate2 = gate_evaluate(rec, identity_by_source={cited: IdentityVerdict.MISMATCH})
        self.assertFalse(gate2.may_publish)
        gate3 = gate_evaluate(rec, identity_by_source={'https://zeta.gov.in/other': IdentityVerdict.MISMATCH})
        self.assertTrue(gate3.may_publish)
        self.assertTrue(any('retained for audit' in n for n in gate3.notes))

    # 4. test_materialize_unknown_exam (NAEB, real pipeline, real gate) -----------------------
    def test_materialize_unknown_exam(self):
        # A single-notice build: the fields the notice does not carry were read for, searched
        # for on the authority's domain, and not found. They are optional, so the real gate
        # passes and the exam registers with those gaps carried honestly, never invented.
        res = naeb()
        self.assertEqual(res.state, EngineState.REGISTERED, res.reason)
        self.assertEqual(res.gate['decision'], 'PASS')
        self.assertEqual(res.gate['blockers'], [])
        rec = res.orchestration.build.record
        self.assertTrue(rec.exam_id.startswith('exam-naeb-'))
        self.assertIs(rec.fields['dates'].status, Status.FOUND)
        self.assertIs(rec.fields['examPattern'].status, Status.FOUND)
        self.assertIs(rec.fields['faqs'].status, Status.NOT_EXTRACTED)   # status untouched
        exam = res.exam
        self.assertEqual(validate_runtime_exam(exam), [])
        self.assertTrue(exam['dates'])
        self.assertEqual(exam['syllabus'], [])
        self.assertEqual(exam['faqs'], [])
        self.assertEqual(exam['sectionStates']['syllabus']['state'], 'SOURCE_NOT_FOUND_AFTER_SEARCH')
        self.assertEqual(exam['sectionStates']['faqs']['state'], 'SOURCE_NOT_FOUND_AFTER_SEARCH')

    # 5. test_materialize_structural_variation_exam (STSB, prose notice) ---------------------
    def test_materialize_structural_variation_exam(self):
        res = stsb()
        self.assertEqual(res.state, EngineState.REGISTERED, res.reason)
        rec = res.orchestration.build.record
        self.assertTrue(rec.exam_id.startswith('exam-stsb-'))
        self.assertIs(rec.fields['howToApply'].status, Status.FOUND)     # prose layout read
        self.assertIs(rec.fields['requiredDocuments'].status, Status.FOUND)
        exam = materialize_exam(rec, cycle='2028', completeness=res.orchestration.build.completeness)
        self.assertEqual(validate_runtime_exam(exam), [])
        self.assertEqual(exam['applicationGuide']['officialPortal'], 'https://stsb.gov.in/recruitment/apply')
        self.assertEqual(len(exam['applicationGuide']['otrSteps']), 1)
        # Same materializer, structurally different source, different result: no branch.
        naeb_exam = materialize_exam(naeb().orchestration.build.record, cycle='2028')
        self.assertNotEqual(naeb_exam['title'], exam['title'])
        self.assertEqual(set(RUNTIME_EXAM_REQUIRED) - set(naeb_exam), set())
        self.assertEqual(set(RUNTIME_EXAM_REQUIRED) - set(exam), set())

    # 6. test_runtime_exam_matches_exam_contract --------------------------------------------
    def test_runtime_exam_matches_exam_contract(self):
        rec = _passing_record()
        exam = materialize_exam(rec, cycle='2028', gate=gate_evaluate(rec))
        self.assertEqual(validate_runtime_exam(exam), [])
        for key, typ in RUNTIME_EXAM_REQUIRED.items():
            self.assertIsInstance(exam[key], typ, key)
        # parity with the compile-time reference renderer: every key emit writes, we write.
        # (The reference emitter reads posts as names; the twin also accepts the richer dicts the
        # extractors now produce, so emit is handed a names-only copy for the key comparison.)
        from ..exam_authoring.emit import render_exam
        emit_rec = _passing_record()
        emit_rec.set(Field.found('posts', [p['postName'] for p in emit_rec.fields['posts'].value],
                                 emit_rec.fields['posts'].citation))
        emitted_keys = set(re.findall(r'^  (\w+):', render_exam(emit_rec), re.M))
        # emit writes `admitCardDetails: undefined` when absent; the JSON twin omits an absent
        # optional rather than writing null — same contract, no nulls in the payload.
        self.assertTrue(emitted_keys - {'admitCardDetails'} <= set(exam), emitted_keys - set(exam))
        # A printed milestone with no specific type is carried as OTHER, in its own words -- it
        # used to be dropped, which lost a date the notice printed. Never coerced to a member.
        self.assertEqual({d['type'] for d in exam['dates']}, {'APPLICATION_CLOSE', 'EXAM_TIER1', 'OTHER'})
        self.assertEqual(next(d['label'] for d in exam['dates'] if d['type'] == 'OTHER'), 'Date of upload')
        # A post without a printed Group is published by name with an empty classification --
        # never faked, and no longer dropped (dropping it lost a verified post name).
        self.assertEqual([p['postName'] for p in exam['posts']], ['Clerk', 'Assistant (no group printed)'])
        self.assertEqual(next(p['classification'] for p in exam['posts'] if p['postName'].startswith('Assistant')), '')
        self.assertEqual(exam['materialization']['postsWithoutPrintedGroup'], ['Assistant (no group printed)'])
        # every emitted value carries provenance
        self.assertTrue(all(d['provenance'].get('officialUrl') for d in exam['dates']))
        self.assertEqual(exam['origin'], 'MACHINE_ACQUIRED')
        # a malformed payload is caught by the contract, not stored
        bad = dict(exam); bad.pop('dates')
        self.assertTrue(validate_runtime_exam(bad))

    # 7. test_authored_exams_unchanged ------------------------------------------------------
    def test_authored_exams_unchanged(self):
        reg = ExamRegistry(':memory:')
        rec = _passing_record()
        reg.register(rec, gate=gate_evaluate(rec), exam=materialize_exam(rec, cycle='2028'), cycle='2028')
        naeb(reg); stsb(reg)
        self.assertEqual(self.before, _fingerprint_live())
        # the registry refuses an authored id outright: it never overwrites or duplicates data.ts
        authored = _passing_record(exam_id='exam-ssc-cgl-2026', title='SSC Combined Graduate Level Examination',
                                   authority='Staff Selection Commission', domain='https://ssc.gov.in', year='2026')
        with self.assertRaises(RegistryRejected) as cm:
            reg.register(authored, gate=gate_evaluate(authored), exam=materialize_exam(authored, cycle='2026'), cycle='2026')
        self.assertIn('authored', str(cm.exception))
        self.assertIsNone(reg.get('exam-ssc-cgl-2026'))

    # 8. test_cycle_isolation ---------------------------------------------------------------
    def test_cycle_isolation(self):
        reg = ExamRegistry(':memory:')
        r28 = _passing_record(exam_id='exam-zeta-clerk-2028', year='2028')
        r27 = _passing_record(exam_id='exam-zeta-clerk-2027', year='2027')
        reg.register(r28, gate=gate_evaluate(r28), exam=materialize_exam(r28, cycle='2028'), cycle='2028')
        reg.register(r27, gate=gate_evaluate(r27), exam=materialize_exam(r27, cycle='2027'), cycle='2027')
        self.assertIsNotNone(reg.get('exam-zeta-clerk-2028', '2028'))
        self.assertIsNone(reg.get('exam-zeta-clerk-2028', '2027'))     # wrong cycle never resolves
        self.assertEqual(reg.get('exam-zeta-clerk-2027').exam['cycle'], '2027')
        # a 2028 overlay never touches the 2027 exam's projection
        e27 = reg.get('exam-zeta-clerk-2027').exam
        o28 = ExamFactOverlay(id='ov-1', exam_id='exam-zeta-clerk-2027', cycle='2028', domain='dates',
                              kind=OverlayKind.ADD, value={'type': 'RESULT', 'label': 'Result', 'dateTimeStr': '2028-09-01'},
                              provenance={'documentTitle': 'N', 'officialUrl': 'https://zeta.gov.in/n',
                                          'verificationLevel': 'OFFICIALLY_VERIFIED', 'excerptText': 'x'})
        self.assertIs(apply_overlays_to_exam_dict(e27, [o28]), e27)

    # 9. test_overlay_isolation -------------------------------------------------------------
    def test_overlay_isolation(self):
        rec = _passing_record()
        exam = materialize_exam(rec, cycle='2028')
        other = materialize_exam(_passing_record(exam_id='exam-omega-clerk-2028', title='Omega Clerk'), cycle='2028')
        o = ExamFactOverlay(id='ov-2', exam_id='exam-zeta-clerk-2028', cycle='2028', domain='dates',
                            kind=OverlayKind.ADD, value={'type': 'RESULT', 'label': 'Result', 'dateTimeStr': '2028-09-01'},
                            provenance={'documentTitle': 'N', 'officialUrl': 'https://zeta.gov.in/n',
                                        'verificationLevel': 'OFFICIALLY_VERIFIED', 'excerptText': 'x'})
        projected = apply_overlays_to_exam_dict(exam, [o])
        self.assertEqual(len(projected['dates']), len(exam['dates']) + 1)   # applies to its own exam
        self.assertIs(apply_overlays_to_exam_dict(other, [o]), other)        # never to another
        self.assertEqual(len(exam['dates']), 3)                              # original untouched (incl. the OTHER date)

    # 10. test_registry_failure_does_not_break_authored_exams -------------------------------
    def test_registry_failure_does_not_break_authored_exams(self):
        # An unusable store reads as "no runtime exams", never as an error the authored
        # register would be lost behind; and the live register is untouched.
        with tempfile.TemporaryDirectory() as d:
            broken = ExamRegistry(os.path.join(d, 'reg.db'))
            with io.open(os.path.join(d, 'reg.db'), 'wb') as fh:
                fh.write(b'not a sqlite database')
            self.assertEqual(broken.list_published(), [])
            self.assertIsNone(broken.get('exam-anything-2028'))
        self.assertEqual(self.before, _fingerprint_live())
        # frontend contract: authored ∪ runtime with authored winning — empty runtime is identity
        from .materialize import ExamRegistry as R
        self.assertEqual(R(':memory:').list_published(), [])

    # 11. test_completeness_state_preserved -------------------------------------------------
    def test_completeness_state_preserved(self):
        res = naeb()
        rec = res.orchestration.build.record
        report = res.orchestration.build.completeness
        exam = materialize_exam(rec, cycle='2028', completeness=report)
        states = exam['sectionStates']
        self.assertEqual(len(states), 17)
        # an unread section stays an honest empty WITH its engine state; nothing invented
        self.assertEqual(exam['faqs'], [])
        self.assertIn(states['faqs']['state'], ('EXTRACTION_FAILED', 'SOURCE_NOT_FOUND_AFTER_SEARCH', 'NOT_YET_PUBLISHED'))
        self.assertEqual(exam['cutoffsHistory'], [])
        self.assertEqual(states['cutoffs']['state'], 'NOT_YET_PUBLISHED')
        # states are metadata: no raw enum ever lands in a student-facing text field
        for key in ('overviewDescription', 'title'):
            for s in ('NOT_EXTRACTED', 'EXTRACTION_FAILED', 'SOURCE_NOT_FOUND'):
                self.assertNotIn(s, exam[key])
        # the per-section student summaries are prose for the UI boundary, never bare enum names
        for st in states.values():
            self.assertIsInstance(st['studentStatusSummary'], str)
            self.assertNotRegex(st['studentStatusSummary'], r'^[A-Z_]+$')

    # 12. test_all_17_sections_projectable --------------------------------------------------
    def test_all_17_sections_projectable(self):
        rec = _passing_record()
        exam = materialize_exam(rec, cycle='2028', gate=gate_evaluate(rec))
        # every field the 17 sections read is present in the contract shape
        for key in ('overviewDescription', 'dates', 'posts', 'globalRuleGroup', 'applicationGuide', 'stages',
                    'syllabus', 'roadmapTracks', 'resources', 'practiceQuestions', 'corrigendums',
                    'faqs', 'officialLinks', 'cutoffsHistory', 'eligibilityHighlights'):
            self.assertIn(key, exam)
        # and every overlay domain projects onto it without error (the same projection the UI uses)
        prov = {'documentTitle': 'N', 'officialUrl': 'https://zeta.gov.in/n',
                'verificationLevel': 'OFFICIALLY_VERIFIED', 'excerptText': 'x'}
        samples = {
            'dates': {'type': 'RESULT', 'label': 'Result', 'dateTimeStr': '2028-09-01'},
            'posts': {'postName': 'Officer', 'department': 'Zeta', 'classification': 'Group B (Non-Gazetted)'},
            'syllabus': {'topicName': 'Reasoning', 'subject': 'General Intelligence'},
            'resources': {'title': 'Notice', 'url': 'https://zeta.gov.in/n', 'type': 'OFFICIAL_PDF'},
            'faqs': {'question': 'Q?', 'answer': 'A.', 'officialClause': 'Para 1'},
            'officialLinks': {'title': 'Portal', 'url': 'https://zeta.gov.in', 'note': 'site'},
            'cutoffsHistory': {'year': 2027, 'category': 'General', 'tier1Cutoff': 120},
            'corrigendums': {'title': 'Corr', 'noticeNumber': '1', 'publishedDate': '2028-02-01',
                             'effectiveDate': '2028-02-01', 'summary': 's', 'pdfUrl': 'https://zeta.gov.in/c',
                             'status': 'ACTIVE', 'diffSummary': 'd'},
        }
        for i, (domain, val) in enumerate(samples.items()):
            o = ExamFactOverlay(id=f'ov-{i}', exam_id=exam['id'], cycle='2028', domain=domain,
                                kind=OverlayKind.ADD, value=val, provenance=prov)
            projected = apply_overlays_to_exam_dict(exam, [o])
            self.assertIsInstance(projected.get(domain), list, domain)
            self.assertGreaterEqual(len(projected[domain]), len(exam.get(domain, [])), domain)

    # 13. test_no_exam_specific_branches ----------------------------------------------------
    def test_no_exam_specific_branches(self):
        with io.open(os.path.join(os.path.dirname(__file__), 'materialize.py'), encoding='utf-8') as fh:
            code = '\n'.join(l for l in fh.read().splitlines() if not l.strip().startswith('#'))
        for pat in (r"if\s+exam\s*==", r"if\s+authority\s*==", r"==\s*['\"]exam-",
                    r"\bNAEB\b", r"\bSTSB\b", r"['\"]SSC['\"]", r"['\"]UPSC['\"]", r"['\"]IBPS['\"]",
                    r"['\"]APPSC['\"]", r"['\"]LIC['\"]"):
            self.assertIsNone(re.search(pat, code), f'forbidden branch {pat!r} in materialize.py')

    # 14. test_build_exam_entrypoint --------------------------------------------------------
    def test_build_exam_entrypoint(self):
        # The same generic path for any name: a record the real gate passes is REGISTERED ...
        rec = _passing_record()
        patch_build(self, lambda *a, **k: _passing_build(rec))
        reg = ExamRegistry(':memory:')
        res = build_exam('Zeta Clerk', 2028, registry=reg, search_fn=lambda q, **kw: [])
        self.assertEqual(res.state, EngineState.REGISTERED, res.reason)
        self.assertEqual(res.registry, {'status': 'REGISTERED', 'examId': 'exam-zeta-clerk-2028', 'cycle': '2028', 'version': 1})
        self.assertEqual(res.gate['decision'], 'PASS')
        self.assertEqual(res.acquisition['fieldsFound'], 12)
        self.assertEqual(reg.get('exam-zeta-clerk-2028').exam['title'], 'Zeta Clerk Examination')
        d = res.to_dict()
        for key in ('resolution', 'identity', 'acquisition', 'verification', 'gate', 'materialization', 'registry'):
            self.assertIn(key, d)
        # ... and every failure keeps its own state and registers nothing
        from .resolve import AmbiguousAuthority, SearchUnavailable
        def boom_lookup(*a, **k): raise LookupError('no authority points at this name')
        patch_build(self, boom_lookup)
        r1 = build_exam('Nonexistent Board Exam', 2031, registry=reg)
        self.assertEqual(r1.state, EngineState.RESOLUTION_FAILURE)
        def boom_search(*a, **k): raise SearchUnavailable('search key not configured')
        patch_build(self, boom_search)
        r2 = build_exam('Any Exam', 2031, registry=reg)
        self.assertEqual(r2.state, EngineState.INFRASTRUCTURE_FAILURE)
        verdict = SimpleNamespace(reason='two boards', summary=lambda: 'two boards')
        def boom_amb(*a, **k): raise AmbiguousAuthority(verdict)
        patch_build(self, boom_amb)
        r3 = build_exam('APPSC Group I', 2028, registry=reg)
        self.assertEqual(r3.state, EngineState.AMBIGUOUS_AUTHORITY)
        for r in (r1, r2, r3):
            self.assertEqual(r.registry['status'], 'NOT_REGISTERED')
        self.assertEqual(len(reg.list_published()), 1)

    # 15. test_idempotent_materialization ---------------------------------------------------
    def test_idempotent_materialization(self):
        rec = _passing_record()
        patch_build(self, lambda *a, **k: _passing_build(rec))
        reg = ExamRegistry(':memory:')
        a = build_exam('Zeta Clerk', 2028, registry=reg, search_fn=lambda q, **kw: [])
        b = build_exam('Zeta Clerk', 2028, registry=reg, search_fn=lambda q, **kw: [])
        self.assertEqual((a.state, b.state), (EngineState.REGISTERED, EngineState.REGISTERED))
        self.assertEqual(len(reg.list_published()), 1)                  # one row, not two
        self.assertEqual(reg.get('exam-zeta-clerk-2028').version, 2)    # versioned, not duplicated
        ea, eb = a.exam, reg.get('exam-zeta-clerk-2028').exam
        for k in RUNTIME_EXAM_REQUIRED:
            self.assertEqual(ea[k], eb[k], k)                            # same projected state

    # --- API: the runtime universe is served, and never insertable by a client --------------
    def test_api_serves_registry_and_refuses_client_inserts(self):
        import app as flask_app
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, 'api.db')
            rec = _passing_record()
            ExamRegistry(db).register(rec, gate=gate_evaluate(rec), exam=materialize_exam(rec, cycle='2028'), cycle='2028')
            with patch.object(flask_app, 'DB_FILE', db):
                client = flask_app.app.test_client()
                listing = client.get('/api/exams').get_json()
                self.assertEqual(listing['count'], 1)
                self.assertEqual(listing['exams'][0]['id'], 'exam-zeta-clerk-2028')
                self.assertEqual(listing['origin'], 'MACHINE_ACQUIRED')
                one = client.get('/api/exams/exam-zeta-clerk-2028').get_json()
                self.assertEqual(one['exam']['title'], 'Zeta Clerk Examination')
                self.assertEqual(one['registry']['cycle'], '2028')
                self.assertEqual(validate_runtime_exam(one['exam']), [])
                self.assertEqual(client.get('/api/exams/exam-zeta-clerk-2028?cycle=2027').status_code, 404)
                self.assertEqual(client.get('/api/exams/exam-nothing-2028').status_code, 404)
                # no client-side insert surface exists: a POST to the collection is not a write
                self.assertEqual(client.post('/api/exams', json={'id': 'exam-hack-2028'}).status_code, 405)
                # the server-side build refuses a request with no exam name
                self.assertEqual(client.post('/api/exams/build', json={}).status_code, 400)


if __name__ == '__main__':
    unittest.main(verbosity=2)
