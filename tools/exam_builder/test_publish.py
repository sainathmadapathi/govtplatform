"""Offline checks for the isolation proof.

The claim under test is the one that lets an automated builder touch the register at all:
building one exam leaves every other exam byte-for-byte unchanged, and a build that fails
that test does not publish.

These run against a fabricated register, never src/data.ts.

Run: python -m tools.exam_builder.test_publish
"""
from __future__ import annotations

import io
import os
import tempfile

from .publish import (IsolationViolation, PublishReport, assert_only_this_exam_changed,
                      fingerprint, slice_exams, stage)

_FAILURES: list[str] = []


def check(label: str, got, want) -> None:
    if got != want:
        _FAILURES.append(f'{label}\n     got  {got!r}\n     want {want!r}')


def expect_raises(label: str, fn) -> None:
    try:
        fn()
    except IsolationViolation:
        return
    _FAILURES.append(f'{label}\n     expected IsolationViolation, none raised')


REGISTER = """import { Exam } from './types';

export const SSC_CGL_EXAM: Exam = {
  id: 'exam-ssc-cgl-2026',
  title: 'SSC CGL',
  note: 'a string containing a brace } to trip a naive parser',
};

export const UPSC_CSE_EXAM: Exam = {
  id: 'exam-upsc-cse-2026',
  title: 'UPSC CSE',
};

export const ALL_EXAMS = [SSC_CGL_EXAM, UPSC_CSE_EXAM];
"""

NEW_EXAM = """export const IBPS_PO_EXAM: Exam = {
  id: 'exam-ibps-po-2027',
  title: 'IBPS PO 2027',
};"""


def test_slicing() -> None:
    slices = slice_exams(REGISTER)
    check('two exams found', len(slices), 2)
    check('ids read from the records',
          [s.exam_id for s in slices], ['exam-ssc-cgl-2026', 'exam-upsc-cse-2026'])
    # The brace inside a string must not end the record early.
    check('a brace inside a string does not split a record',
          'ALL_EXAMS' not in slices[0].text, True)


def test_hashes_are_per_exam() -> None:
    fp = fingerprint(REGISTER)
    check('one digest per exam', sorted(fp), ['exam-ssc-cgl-2026', 'exam-upsc-cse-2026'])
    edited = REGISTER.replace("title: 'UPSC CSE'", "title: 'UPSC CSE 2026'")
    fp2 = fingerprint(edited)
    check('editing UPSC changes only UPSC',
          fp['exam-ssc-cgl-2026'] == fp2['exam-ssc-cgl-2026'], True)
    check('and UPSC does change',
          fp['exam-upsc-cse-2026'] != fp2['exam-upsc-cse-2026'], True)


def test_proof_accepts_a_clean_build() -> None:
    before = {'a': '1', 'b': '2'}
    after = {'a': '1', 'b': '2', 'c': '3'}
    added, replaced, untouched = assert_only_this_exam_changed(before, after, 'c')
    check('new exam added', added, ['c'])
    check('nothing replaced', replaced, [])
    check('both neighbours untouched', sorted(untouched), ['a', 'b'])


def test_proof_rejects_collateral_damage() -> None:
    # The case the whole module exists for: building c quietly rewrote a.
    expect_raises('a changed neighbour must abort the build',
                  lambda: assert_only_this_exam_changed(
                      {'a': '1', 'b': '2'}, {'a': 'CHANGED', 'b': '2', 'c': '3'}, 'c'))
    expect_raises('a removed exam must abort the build',
                  lambda: assert_only_this_exam_changed(
                      {'a': '1', 'b': '2'}, {'b': '2', 'c': '3'}, 'c'))
    expect_raises('an unrequested extra exam must abort the build',
                  lambda: assert_only_this_exam_changed(
                      {'a': '1'}, {'a': '1', 'c': '3', 'sneaky': '9'}, 'c'))


def test_stage_is_non_destructive() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        data_ts = os.path.join(tmp, 'data.ts')
        io.open(data_ts, 'w', encoding='utf-8', newline='').write(REGISTER)
        staging = os.path.join(tmp, 'staging')

        report = stage('exam-ibps-po-2027', NEW_EXAM, data_ts=data_ts, staging_dir=staging)

        check('the live register is untouched by staging',
              io.open(data_ts, encoding='utf-8').read(), REGISTER)
        check('a staged file was written', os.path.exists(report.staged_path), True)
        check('the new exam is in the staged copy', report.added, ['exam-ibps-po-2027'])
        check('both existing exams untouched', len(report.untouched), 2)
        check('not published merely by staging', report.published, False)

        staged = io.open(report.staged_path, encoding='utf-8').read()
        check('staged copy keeps every original exam',
              all(e in staged for e in ('exam-ssc-cgl-2026', 'exam-upsc-cse-2026')), True)


def test_rebuilding_an_existing_exam_replaces_only_it() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        data_ts = os.path.join(tmp, 'data.ts')
        io.open(data_ts, 'w', encoding='utf-8', newline='').write(REGISTER)
        staging = os.path.join(tmp, 'staging')

        rebuilt = """export const UPSC_CSE_EXAM: Exam = {
  id: 'exam-upsc-cse-2026',
  title: 'UPSC CSE 2026 (rebuilt)',
};"""
        report = stage('exam-upsc-cse-2026', rebuilt, data_ts=data_ts, staging_dir=staging)
        check('the rebuilt exam is marked replaced, not added',
              (report.added, report.replaced), ([], ['exam-upsc-cse-2026']))
        check('SSC untouched by a UPSC rebuild', report.untouched, ['exam-ssc-cgl-2026'])


def main() -> int:
    test_slicing()
    test_hashes_are_per_exam()
    test_proof_accepts_a_clean_build()
    test_proof_rejects_collateral_damage()
    test_stage_is_non_destructive()
    test_rebuilding_an_existing_exam_replaces_only_it()
    if _FAILURES:
        print(f'{len(_FAILURES)} FAILURE(S):')
        for f in _FAILURES:
            print('  -', f)
        return 1
    print('isolation proof: all checks pass')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
