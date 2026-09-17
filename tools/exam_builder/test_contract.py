"""Offline checks for the Universal Information Contract.

The case that matters is the one live discovery on ssc.gov.in produced: SSC publishes no
standalone syllabus for CGL — it is an annexure inside the notice — while other authorities
publish a separate syllabus PDF. A contract that tied `syllabus` to a SYLLABUS document
would report "not published" for SSC, which is false about SSC.

Run: python -m tools.exam_builder.test_contract
"""
from __future__ import annotations

from .contract import CONTRACT, GROUPS, coverage_from, fields_for, suppliers
from .discover import DocKind

_FAILURES: list[str] = []


def check(label: str, got, want) -> None:
    if got != want:
        _FAILURES.append(f'{label}\n     got  {got!r}\n     want {want!r}')


def test_syllabus_falls_back_to_the_notice() -> None:
    """The SSC case, which is why fields name several sources in preference order."""
    only_notice = coverage_from({DocKind.NOTIFICATION})
    check('syllabus answerable from the notice alone',
          only_notice.supplied['syllabus'], 'CAN_ANSWER_FROM:NOTIFICATION')

    # And where a real syllabus document exists, it is preferred over the notice.
    both = coverage_from({DocKind.NOTIFICATION, DocKind.SYLLABUS})
    check('a dedicated syllabus wins', both.supplied['syllabus'], 'CAN_ANSWER_FROM:SYLLABUS')


def test_absent_means_absent() -> None:
    """A kind nobody published is NO_SOURCE — a fact about the authority, not about us."""
    cov = coverage_from({DocKind.NOTIFICATION})
    check('answer keys have no source', cov.supplied['answerKeys'], 'NO_SOURCE')
    check('the missing kind is named',
          cov.missing_sources['answerKeys'], ['ANSWER_KEY'])
    check('results have no source', cov.supplied['results'], 'NO_SOURCE')


def test_every_field_is_reachable() -> None:
    """No field may be unanswerable by every document kind — that would be a dead entry."""
    for f in CONTRACT:
        if not f.sources:
            continue                      # intrinsic, filled by the builder itself
        cov = coverage_from(set(f.sources))
        check(f'{f.name} answerable from its own sources',
              cov.supplied[f.name].startswith('CAN_ANSWER_FROM:'), True)


def test_shape() -> None:
    names = [f.name for f in CONTRACT]
    check('no duplicate field names', len(names), len(set(names)))
    check('groups cover the specified tree',
          set(GROUPS) >= {'Identity', 'Application', 'Posts', 'Eligibility', 'Dates',
                          'Exam Pattern', 'Syllabus', 'PYQs', 'Answer Keys',
                          'Admit Card', 'Results', 'Official Sources'}, True)
    # The notification is the workhorse: most fields must be able to fall back to it,
    # because many authorities publish nothing else.
    from_notice = fields_for(DocKind.NOTIFICATION)
    check('the notice alone can answer most of the contract', len(from_notice) >= 10, True)
    check('suppliers() agrees with the table',
          suppliers('answerKeys'), (DocKind.ANSWER_KEY,))


def main() -> int:
    test_syllabus_falls_back_to_the_notice()
    test_absent_means_absent()
    test_every_field_is_reachable()
    test_shape()
    if _FAILURES:
        print(f'{len(_FAILURES)} FAILURE(S):')
        for f in _FAILURES:
            print('  -', f)
        return 1
    print(f'contract: all checks pass ({len(CONTRACT)} fields, {len(GROUPS)} groups)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
