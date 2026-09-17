"""One command. Name an exam; GovOS finds who runs it and reads what they published.

    python -m tools.exam_builder "SSC CGL 2026"
    python -m tools.exam_builder "UPSC Civil Services Preliminary 2026" --json out.json

No authority is configured anywhere. The resolver discovers it, discovery finds that
authority's documents *for this exam*, the contract says what GovOS wants to know, and the
extractors read whatever was actually found.

Four outcomes per field, and the last two are deliberately never merged:

    FOUND          sourced, with document and page
    NEEDS REVIEW   read but unconfident; never badged official
    NOT PUBLISHED  nothing the authority published could answer it
    NOT EXTRACTED  the document was read and our pattern missed it — our gap, not theirs
"""
from __future__ import annotations

import argparse
import json
import sys

from ..exam_authoring.record import Status
from ..exam_authoring.verify import IsolationError, run_all
from .build import build
from .contract import GROUPS
from .resolve import SearchUnavailable


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog='exam_builder', description=__doc__)
    ap.add_argument('exam', help='the exam name, e.g. "SSC CGL 2026"')
    ap.add_argument('--year', default='', help='override the year if the name has none')
    ap.add_argument('--siblings', default='',
                    help='comma-separated names of other exams on the same site, so their '
                         'documents are actively rejected rather than merely unmatched')
    ap.add_argument('--json', dest='json_out', help='write the full record here')
    args = ap.parse_args(argv)

    try:
        siblings: list[str] = []
        for name in filter(None, (s.strip() for s in args.siblings.split(','))):
            from .discover import exam_aliases
            siblings.extend(exam_aliases(name, name))
        result = build(args.exam, year=args.year, sibling_exam_words=siblings)
    except SearchUnavailable as exc:
        print(f'Cannot resolve an authority without search.\n  {exc}')
        return 2
    except LookupError as exc:
        print(f'Could not identify the authority for "{args.exam}".\n  {exc}')
        return 3

    r, rec = result.resolved, result.record
    print(f'\nAUTHORITY   {r.authority.name}')
    print(f'            {r.authority.domain}   confidence {r.authority.confidence}')
    if r.authority.corroborated_by:
        print(f'            not a government domain; vouched for by {r.authority.corroborated_by}')
    if r.authority.rivals:
        print(f'            other candidates: {r.authority.rivals}')
    print(f'EXAM        {rec.title}')
    print(f'            {rec.exam_id}')

    print(f'\nDOCUMENTS   {len(result.sources.docs)} kept, '
          f'{len(result.sources.rejected)} rejected as another exam’s')
    for kind, count in sorted(result.sources.kinds_found().items()):
        print(f'   {kind:18} {count}')
    for d in result.sources.rejected[:5]:
        print(f'   rejected: {d.title[:50]!r} (matches {d.foreign_words})')

    try:
        rpt = run_all(rec)
    except IsolationError as exc:
        print(f'\nISOLATION CHECK FAILED — nothing emitted.\n  {exc}')
        return 4

    print('\nCONTRACT')
    by_group = result.coverage.by_group()
    for group in GROUPS:
        rows = by_group.get(group) or []
        print(f'  {group}')
        for name, _ in rows:
            f = rec.fields.get(name)
            if f is None:
                print(f'     {name:20} —')
                continue
            mark = {Status.FOUND: 'FOUND', Status.NEEDS_REVIEW: 'NEEDS REVIEW',
                    Status.NOT_PUBLISHED: 'NOT PUBLISHED', Status.NOT_EXTRACTED: 'NOT EXTRACTED'}[f.status]
            where = f' [p.{f.citation.page}]' if (f.citation and f.status is Status.FOUND) else ''
            print(f'     {name:20} {mark}{where}')

    print(f'\ncoverage: {rpt["coverage"]}')
    if rpt['lowCoverage']:
        print('  Few fields were sourced. Check whether the notice is a scan, or whether the')
        print('  extractors need work for this authority’s layout — it is not evidence that')
        print('  the authority publishes little.')
    if rec.log:
        print('\nNOTES')
        for line in rec.log[:12]:
            print(f'  · {line}')

    if args.json_out:
        payload = {
            'examId': rec.exam_id, 'title': rec.title,
            'authority': {'name': r.authority.name, 'domain': r.authority.domain,
                          'confidence': r.authority.confidence,
                          'corroboratedBy': r.authority.corroborated_by},
            'documents': [{'url': d.url, 'kind': d.kind.value, 'title': d.title,
                           'relevance': d.relevance.value} for d in result.sources.docs],
            'rejected': [{'url': d.url, 'title': d.title, 'foreign': d.foreign_words}
                         for d in result.sources.rejected],
            'coverage': result.coverage.supplied,
            'fields': {n: {'status': f.status.value, 'note': f.note, 'value': f.value,
                           'citation': (f.citation.__dict__ if f.citation else None)}
                       for n, f in rec.fields.items()},
        }
        with open(args.json_out, 'w', encoding='utf-8') as fh:
            json.dump(payload, fh, indent=1, ensure_ascii=False, default=str)
        print(f'\nfull record -> {args.json_out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
