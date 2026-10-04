"""The orchestration layer: the twenty-two required cases, all offline.

Every case drives the REAL orchestrator (`orchestrate.orchestrate`) — the real gate, the real
publisher, the real record-level isolation check, the real verifier — and only the outermost
`build` (network) and the Claude provider are stubbed, exactly as `test_contamination` stubs the
build's own I/O. The live register is never touched: publish tests write to a temp file.

The point is to prove the wiring is safe and universal: each distinct failure keeps its own
state, Claude can only withhold, publishing goes through the gate, and no orchestrator branch
names an exam or an authority.
"""
from __future__ import annotations

import io
import json
import os
import re
import tempfile
import unittest
from types import SimpleNamespace

from . import orchestrate as O
from . import publish as P
from .gate import BuildState
from .identity import IdentityCheck, IdentityVerdict
from .resolve import AmbiguousAuthority, Authority, ResolvedExam, SearchUnavailable
from tools.claude_cli.testing import FakeClaude, ForbiddenClaude, verdict_reply
from .verification.schemas import InfraStatus
from ..exam_authoring.record import Citation, ExamRecord, Field, Status


# --------------------------------------------------------------------------- fixtures
def _rec(exam_id='exam-ssc-cgl-2026', title='SSC Combined Graduate Level Examination',
         authority='Staff Selection Commission', domain='https://ssc.gov.in',
         statuses=None):
    """A record. By default every required field is FOUND, so the gate passes."""
    rec = ExamRecord(exam_id=exam_id,
                     code=exam_id.replace('exam-', '').upper().replace('-', '_'),
                     title=title, authority_name=authority, official_domain=domain)
    cit = Citation(document_title=f'{title}, 2026 — Notice', url=domain + '/notice', page=2,
                   excerpt=f'{title}, 2026. Applications are invited.', verified_date='2026-01-01')
    base = {'officialName': title, 'authority': authority,
            'applicationPortal': domain, 'dates': {'notification': '2026-01-01'}}
    for name, val in base.items():
        rec.set(Field.found(name, val, cit))
    rec.sources_read.append(domain + '/notice')
    for name, status in (statuses or {}).items():
        if status is Status.NOT_EXTRACTED:
            rec.set(Field.not_extracted(name, domain, name))
        elif status is Status.NEEDS_REVIEW:
            rec.set(Field.needs_review(name, 'x', 'unconfident', cit))
        elif status is Status.NOT_PUBLISHED:
            rec.set(Field.not_published(name, 'authority publishes none'))
    return rec


def _build(rec, *, build_state=BuildState.COMPLETE, identity=None, year='2026'):
    resolved = ResolvedExam(query=rec.title, official_name=rec.title, year=year,
                            authority=Authority(name=rec.authority_name,
                                                domain=rec.official_domain, confidence=0.9),
                            seed_urls=[])
    return O.BuildResult(resolved=resolved,
                         sources=SimpleNamespace(docs=[], rejected=[], log=[]),
                         coverage=SimpleNamespace(supplied={}), record=rec,
                         build_state=build_state, identity=identity or {})


def patch_build(test, fn):
    """Replace orchestrate.build with fn for the duration of one test."""
    real = O.build
    O.build = fn
    test.addCleanup(lambda: setattr(O, 'build', real))


def _Stub(payload=None, raises=None):
    """A scripted Claude gateway: the real gateway over a fake CLI process. `payload` is a verdict
    reply (or a raw string for a malformed one); `raises` is the failure to simulate."""
    if raises is not None:
        return FakeClaude(fail=raises)
    return FakeClaude(payload)


def _json(decision, ident=True, ev=True, claim=True):
    return verdict_reply(decision, identity=ident, evidence=ev, claim=claim)


def _temp_register(tmpdir, exams):
    """A minimal data.ts holding the given (const, exam_id) exams plus ALL_EXAMS."""
    parts = []
    for const, exam_id in exams:
        parts.append(f"export const {const}: Exam = {{\n  id: '{exam_id}',\n  title: '{exam_id}',\n}};\n")
    parts.append('export const ALL_EXAMS: Exam[] = [\n' +
                 ',\n'.join('  ' + c for c, _ in exams) + '\n];\n')
    path = os.path.join(tmpdir, 'data.ts')
    io.open(path, 'w', encoding='utf-8', newline='').write('\n'.join(parts))
    return path


def _render(exam_id):
    const = exam_id.replace('exam-', '').upper().replace('-', '_') + '_EXAM'
    return lambda rec: f"export const {const}: Exam = {{\n  id: '{exam_id}',\n  title: '{rec.title}',\n}};"


class TestOrchestration(unittest.TestCase):

    # --- 1-4: resolution of the four real exams (dry run -> STAGED on a passing record) ------
    def test_1_ssc_resolution(self):
        patch_build(self, lambda *a, **k: _build(_rec('exam-ssc-cgl-2026', 'SSC Combined Graduate Level Examination', 'Staff Selection Commission', 'https://ssc.gov.in')))
        r = O.orchestrate('SSC CGL 2026')
        self.assertEqual(r.state, O.OrchestrationState.STAGED)
        self.assertEqual(r.gate.decision.value, 'PASS')

    def test_2_upsc_resolution(self):
        patch_build(self, lambda *a, **k: _build(_rec('exam-upsc-cse-2026', 'Civil Services (Preliminary) Examination', 'Union Public Service Commission', 'https://upsc.gov.in')))
        r = O.orchestrate('UPSC CSE 2026')
        self.assertEqual(r.state, O.OrchestrationState.STAGED)

    def test_3_ibps_resolution(self):
        patch_build(self, lambda *a, **k: _build(_rec('exam-ibps-po-2026', 'Probationary Officers', 'Institute of Banking Personnel Selection', 'https://ibps.in')))
        r = O.orchestrate('IBPS PO 2026')
        self.assertEqual(r.state, O.OrchestrationState.STAGED)

    def test_4_lic_resolution(self):
        patch_build(self, lambda *a, **k: _build(_rec('exam-lic-aao-2027', 'Recruitment of Assistant Administrative Officers', 'Life Insurance Corporation of India', 'https://licindia.in'), year='2027'))
        r = O.orchestrate('LIC AAO 2027', year='2027')
        self.assertEqual(r.state, O.OrchestrationState.STAGED)

    # --- 5: APPSC ambiguous authority -> AMBIGUOUS_AUTHORITY, nothing built ------------------
    def test_5_appsc_ambiguous(self):
        verdict = SimpleNamespace(reason='Andhra vs Arunachal PSC; the name chooses neither',
                                  summary=lambda: 'Andhra vs Arunachal PSC; the name chooses neither')
        def boom(*a, **k):
            raise AmbiguousAuthority(verdict)
        patch_build(self, boom)
        r = O.orchestrate('APPSC Group I 2026')
        self.assertEqual(r.state, O.OrchestrationState.AMBIGUOUS_AUTHORITY)
        self.assertEqual(r.reached, O.Stage.RESOLUTION)
        self.assertIsNone(r.build)

    # --- 6: unknown authority -> RESOLUTION_FAILURE (LookupError) ----------------------------
    def test_6_unknown_authority(self):
        def boom(*a, **k):
            raise LookupError('no authority points clearly enough at "Zeta Board Clerk 2031"')
        patch_build(self, boom)
        r = O.orchestrate('Zeta Board Clerk 2031')
        self.assertEqual(r.state, O.OrchestrationState.RESOLUTION_FAILURE)

    # --- 7: source identity mismatch -> gate blocks -----------------------------------------
    def test_7_source_identity_mismatch(self):
        # The record's fields cite <domain>/notice; a MISMATCH verdict on that very source is
        # contamination and blocks. A MISMATCH on a source nothing cites (it was excluded from
        # extraction) is retained for audit and does not block.
        rec = _rec()
        cited = rec.fields['dates'].citation.url
        ident = {cited: IdentityCheck(IdentityVerdict.MISMATCH)}
        patch_build(self, lambda *a, **k: _build(_rec(), identity=ident))
        r = O.orchestrate('SSC CGL 2026')
        self.assertEqual(r.state, O.OrchestrationState.BLOCKED_BY_GATE)
        self.assertTrue(any('another exam' in str(b) for b in r.gate.blockers))
        quiet = {'https://ssc.gov.in/other': IdentityCheck(IdentityVerdict.MISMATCH)}
        patch_build(self, lambda *a, **k: _build(_rec(), identity=quiet))
        r2 = O.orchestrate('SSC CGL 2026')
        self.assertEqual(r2.state, O.OrchestrationState.STAGED)
        self.assertTrue(any('retained for audit' in n for n in r2.gate.notes))

    # --- 8: cycle mismatch surfaces as a resolution mismatch (build raises LookupError) ------
    def test_8_cycle_mismatch(self):
        def boom(*a, **k):
            raise LookupError('the only sources found are for 2025, not 2026')
        patch_build(self, boom)
        r = O.orchestrate('SSC CGL 2026', year='2026')
        self.assertEqual(r.state, O.OrchestrationState.RESOLUTION_FAILURE)

    # --- 9: source unavailable -> INFRASTRUCTURE_FAILURE / SOURCE_FETCH_FAILURE --------------
    def test_9a_search_unavailable(self):
        def boom(*a, **k):
            raise SearchUnavailable('discovery is unavailable')
        patch_build(self, boom)
        r = O.orchestrate('SSC CGL 2026')
        self.assertEqual(r.state, O.OrchestrationState.INFRASTRUCTURE_FAILURE)
        self.assertEqual(r.reached, O.Stage.DISCOVERY)

    def test_9b_source_fetch_failure_is_not_not_published(self):
        # A build paused because a document could not be fetched: the orchestrator reports
        # SOURCE_FETCH_FAILURE, never "the authority published nothing".
        patch_build(self, lambda *a, **k: _build(_rec(), build_state=BuildState.PAUSED_INFRASTRUCTURE))
        r = O.orchestrate('SSC CGL 2026')
        self.assertEqual(r.state, O.OrchestrationState.SOURCE_FETCH_FAILURE)

    # --- 10: extraction failure on a required field -> gate blocks ---------------------------
    def test_10_extraction_failure_blocks(self):
        patch_build(self, lambda *a, **k: _build(_rec(statuses={'dates': Status.NOT_EXTRACTED})))
        r = O.orchestrate('SSC CGL 2026')
        self.assertEqual(r.state, O.OrchestrationState.BLOCKED_BY_GATE)

    # --- 11: deterministic validation failure -> verdict never publishable, field not upgraded
    def test_11_deterministic_failure(self):
        # A FOUND field whose citation names another exam entirely: the verifier's deterministic
        # layer rejects it before the model, and the verdict is not publishable.
        rec = _rec()
        bad = rec.fields['dates']
        bad.citation = Citation(document_title='Some other exam 2099', url='https://ssc.gov.in/x',
                                page=1, excerpt='A clause that names no exam at all.', verified_date='2026')
        patch_build(self, lambda *a, **k: _build(rec))
        r = O.orchestrate('SSC CGL 2026', use_claude=True, gateway=_Stub(_json('SUPPORTED')),
                          year='2026')
        v = r.verifications.get('dates')
        self.assertIsNotNone(v)
        self.assertFalse(v.publishable)          # deterministic gate withheld it

    # --- 12: Claude SUPPORTED -> field stays FOUND --------------------------------------------
    def test_12_claude_supported(self):
        patch_build(self, lambda *a, **k: _build(_rec()))
        r = O.orchestrate('SSC CGL 2026', use_claude=True, gateway=_Stub(_json('SUPPORTED')))
        self.assertEqual(r.build.record.fields['officialName'].status, Status.FOUND)

    # --- 13: Claude CONTRADICTED -> field downgraded to NEEDS_REVIEW, gate blocks --------------
    def test_13_claude_contradicted_downgrades(self):
        patch_build(self, lambda *a, **k: _build(_rec()))
        r = O.orchestrate('SSC CGL 2026', use_claude=True,
                          gateway=_Stub(_json('CONTRADICTED', ev=False, claim=False)))
        self.assertEqual(r.build.record.fields['officialName'].status, Status.NEEDS_REVIEW)
        self.assertEqual(r.state, O.OrchestrationState.BLOCKED_BY_GATE)

    # --- 14: Claude INSUFFICIENT -> field NOT downgraded (build evidence stands) ---------------
    def test_14_claude_insufficient_does_not_downgrade(self):
        patch_build(self, lambda *a, **k: _build(_rec()))
        r = O.orchestrate('SSC CGL 2026', use_claude=True,
                          gateway=_Stub(_json('INSUFFICIENT', ev=False, claim=False)))
        self.assertEqual(r.build.record.fields['officialName'].status, Status.FOUND)

    # --- 15: Claude unavailable -> field unchanged, never VERIFIED, never fabricated -----------
    def test_15_claude_unavailable(self):
        patch_build(self, lambda *a, **k: _build(_rec()))
        r = O.orchestrate('SSC CGL 2026', use_claude=True,
                          gateway=_Stub(raises=InfraStatus.CLAUDE_CLI_FAILED))
        self.assertEqual(r.build.record.fields['officialName'].status, Status.FOUND)
        self.assertIs(r.verifications['officialName'].infra, InfraStatus.CLAUDE_CLI_FAILED)
        self.assertFalse(r.verifications['officialName'].publishable)

    # --- 16: publication rejection (non-dry-run, gate BLOCK) leaves live data unchanged ------
    def test_16_publication_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            reg = _temp_register(d, [('SSC_EXAM', 'exam-ssc-cgl-2026'), ('UPSC_EXAM', 'exam-upsc-cse-2026')])
            before = io.open(reg, encoding='utf-8').read()
            patch_build(self, lambda *a, **k: _build(_rec(statuses={'dates': Status.NOT_EXTRACTED})))
            r = O.orchestrate('SSC CGL 2026', dry_run=False, data_ts=reg, typecheck=False,
                              render=_render('exam-ssc-cgl-2026'))
            self.assertEqual(r.state, O.OrchestrationState.BLOCKED_BY_GATE)
            self.assertFalse(r.published)
            self.assertEqual(io.open(reg, encoding='utf-8').read(), before)   # untouched

    # --- 17: dry run does not mutate live data ----------------------------------------------
    def test_17_dry_run_no_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            reg = _temp_register(d, [('SSC_EXAM', 'exam-ssc-cgl-2026')])
            before = io.open(reg, encoding='utf-8').read()
            patch_build(self, lambda *a, **k: _build(_rec()))
            r = O.orchestrate('SSC CGL 2026', dry_run=True, data_ts=reg)
            self.assertEqual(r.state, O.OrchestrationState.STAGED)
            self.assertFalse(r.published)
            self.assertEqual(io.open(reg, encoding='utf-8').read(), before)
            self.assertTrue(r.isolation_ok)

    # --- 18: staging writes an auditable artifact and mutates nothing live -------------------
    def test_18_staging_no_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            reg = _temp_register(d, [('SSC_EXAM', 'exam-ssc-cgl-2026')])
            before = io.open(reg, encoding='utf-8').read()
            patch_build(self, lambda *a, **k: _build(_rec()))
            r = O.orchestrate('SSC CGL 2026', dry_run=True, data_ts=reg)
            self.assertTrue(os.path.exists(r.staging_path))
            payload = json.load(io.open(r.staging_path, encoding='utf-8'))
            for key in ('examId', 'identity', 'fields', 'gate', 'sourcesRead'):
                self.assertIn(key, payload)                     # auditable
            self.assertEqual(io.open(reg, encoding='utf-8').read(), before)
            os.remove(r.staging_path)

    # --- 19: successful publication updates the target and only the target -------------------
    def test_19_successful_publication(self):
        with tempfile.TemporaryDirectory() as d:
            reg = _temp_register(d, [('SSC_EXAM', 'exam-ssc-cgl-2026'), ('UPSC_EXAM', 'exam-upsc-cse-2026')])
            before = P.fingerprint(io.open(reg, encoding='utf-8').read())
            patch_build(self, lambda *a, **k: _build(_rec('exam-ssc-cgl-2026')))
            r = O.orchestrate('SSC CGL 2026', dry_run=False, data_ts=reg, typecheck=False,
                              allow_overwrite=True, render=_render('exam-ssc-cgl-2026'))
            self.assertEqual(r.state, O.OrchestrationState.PUBLISHED)
            self.assertTrue(r.published)
            after = P.fingerprint(io.open(reg, encoding='utf-8').read())
            self.assertEqual(before['exam-upsc-cse-2026'], after['exam-upsc-cse-2026'])   # neighbour untouched
            self.assertNotEqual(before['exam-ssc-cgl-2026'], after['exam-ssc-cgl-2026'])  # target updated

    # --- 20: cross-exam isolation across the four required pairs -----------------------------
    def test_20_cross_exam_isolation(self):
        with tempfile.TemporaryDirectory() as d:
            reg = _temp_register(d, [('SSC_EXAM', 'exam-ssc-cgl-2026'), ('UPSC_EXAM', 'exam-upsc-cse-2026'),
                                     ('IBPS_EXAM', 'exam-ibps-po-2026'), ('LIC_EXAM', 'exam-lic-aao-2027'),
                                     ('APPSC_EXAM', 'exam-appsc-group1-2026')])
            before = P.fingerprint(io.open(reg, encoding='utf-8').read())
            patch_build(self, lambda *a, **k: _build(_rec('exam-ssc-cgl-2026')))
            r = O.orchestrate('SSC CGL 2026', dry_run=False, data_ts=reg, typecheck=False,
                              allow_overwrite=True, render=_render('exam-ssc-cgl-2026'))
            self.assertEqual(r.state, O.OrchestrationState.PUBLISHED)
            after = P.fingerprint(io.open(reg, encoding='utf-8').read())
            for other in ('exam-upsc-cse-2026', 'exam-ibps-po-2026', 'exam-lic-aao-2027', 'exam-appsc-group1-2026'):
                self.assertEqual(before[other], after[other], f'{other} changed')

    # --- 21: reverse-order builds each leave the other untouched ----------------------------
    def test_21_reverse_order_isolation(self):
        with tempfile.TemporaryDirectory() as d:
            reg = _temp_register(d, [('SSC_EXAM', 'exam-ssc-cgl-2026'), ('UPSC_EXAM', 'exam-upsc-cse-2026')])
            # publish UPSC, assert SSC unchanged
            f0 = P.fingerprint(io.open(reg, encoding='utf-8').read())
            patch_build(self, lambda *a, **k: _build(_rec('exam-upsc-cse-2026', 'Civil Services', 'Union Public Service Commission', 'https://upsc.gov.in')))
            O.orchestrate('UPSC', dry_run=False, data_ts=reg, typecheck=False, allow_overwrite=True, render=_render('exam-upsc-cse-2026'))
            f1 = P.fingerprint(io.open(reg, encoding='utf-8').read())
            self.assertEqual(f0['exam-ssc-cgl-2026'], f1['exam-ssc-cgl-2026'])
            # now publish SSC, assert UPSC unchanged
            O.build = lambda *a, **k: _build(_rec('exam-ssc-cgl-2026'))
            O.orchestrate('SSC', dry_run=False, data_ts=reg, typecheck=False, allow_overwrite=True, render=_render('exam-ssc-cgl-2026'))
            f2 = P.fingerprint(io.open(reg, encoding='utf-8').read())
            self.assertEqual(f1['exam-upsc-cse-2026'], f2['exam-upsc-cse-2026'])

    # --- 22: the orchestrator contains no exam-specific or authority-specific branch ---------
    def test_22_no_exam_specific_branch(self):
        with io.open(os.path.join(os.path.dirname(__file__), 'orchestrate.py'), encoding='utf-8') as _fh:
            src = _fh.read()
        # strip comments/docstrings-ish: check only code lines for forbidden branches
        code = '\n'.join(l for l in src.splitlines() if not l.strip().startswith('#'))
        for pattern in (r"if\s+exam\s*==", r"if\s+authority\s*==", r"==\s*['\"]exam-",
                        r"\.startswith\(\s*['\"]exam-ssc", r"if\s+.*['\"]SSC['\"]",
                        r"if\s+.*['\"]UPSC['\"]", r"if\s+.*['\"]IBPS['\"]", r"if\s+.*['\"]APPSC['\"]"):
            self.assertIsNone(re.search(pattern, code), f'forbidden branch {pattern!r} in orchestrator')

    # --- 23: a build without Claude never reaches it, even where Claude is enabled -----------
    def test_23_build_gets_the_jobs_gateway(self):
        seen = []

        def capture(*a, **k):
            seen.append(k.get('gateway'))
            return _build(_rec())
        patch_build(self, capture)
        O.orchestrate('SSC CGL 2026', use_claude=False, gateway=ForbiddenClaude())
        self.assertFalse(seen[-1].is_enabled())
        O.orchestrate('SSC CGL 2026', use_claude=True, gateway=_Stub(_json('SUPPORTED')))
        self.assertIsNone(seen[-1])        # unchanged: the build's steps use the process-wide gateway

    def test_24_every_build_step_uses_the_runs_gateway(self):
        # Identity, completeness and date checks resolve their gateway through the run's one; a
        # process-wide gateway that is enabled is never reached while the run's is NoClaude.
        from . import build as B
        from tools.claude_cli.testing import use_gateway
        forbidden = ForbiddenClaude()
        with use_gateway(forbidden):
            token = B._RUN_GATEWAY.set(B.NoClaude())
            try:
                self.assertFalse(B._run_gateway().is_enabled())
                held = Field.found('dates', [{'type': 'APPLICATION_CLOSE', 'label': 'Last date',
                                              'dateTimeStr': '2026-05-20 00:00:00',
                                              'provenance': {'excerptText': 'Last date 20.05.2026'}}],
                                   Citation(document_title='Notice', url='https://ssc.gov.in/notice',
                                            page=1, excerpt='Last date 20.05.2026'))
                B._vet_dates(held, {}, _rec(), cycle='2026')
            finally:
                B._RUN_GATEWAY.reset(token)
            self.assertIs(B._run_gateway(), forbidden)
        self.assertEqual(forbidden.attempts, 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
