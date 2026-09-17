"""Name an exam; the pipeline reads that authority's own documents and reports what it found.

    python -m tools.exam_authoring "UPSC Civil Services"
    python -m tools.exam_authoring "Engineering Services" --json out.json

It prints three lists and they are the whole point:

    FOUND          sourced, with document and page
    NEEDS REVIEW   read but not confidently, or read from a scan — never badged official
    NOT PUBLISHED  the authority does not publish it; a fact about them
    NOT EXTRACTED  the document was read but no pattern matched; a gap in this tool, and
                   deliberately not reported as the authority being silent

Nothing is invented to fill any of them.
"""
from __future__ import annotations

import argparse
import json
import sys

from .record import Status
from .registry import resolve, supported
from .verify import IsolationError, run_all


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog='exam_authoring', description=__doc__)
    ap.add_argument('exam', help='the exam name, as the authority prints it')
    ap.add_argument('--json', dest='json_out', help='write the full record to this file')
    ap.add_argument('--pick', type=int, default=None, help='choose one of several matches by index')
    ap.add_argument('--list', action='store_true', help='list matches and stop')
    ap.add_argument('--emit', help='write the TypeScript Exam record to this file')
    args = ap.parse_args(argv)

    adapter = resolve(args.exam)
    if adapter is None:
        print(f'No adapter matches "{args.exam}".')
        print('Authorities wired so far:', ', '.join(supported()))
        print('An authority without an adapter is not guessed at — add one in adapters/.')
        return 2

    print(f'Authority: {adapter.authority_name}')
    targets = adapter.discover(args.exam)
    if not targets:
        print(f'{adapter.authority_name} lists no exam matching "{args.exam}".')
        return 3

    if args.list or (len(targets) > 1 and args.pick is None):
        print(f'\n{len(targets)} match(es):')
        for i, t in enumerate(targets):
            print(f'  [{i}] {t.title}')
            print(f'      {t.exam_page_url}')
        if args.list:
            return 0
        print('\nRe-run with --pick <index> to gather one of these.')
        return 0

    target = targets[args.pick or 0]
    print(f'Gathering: {target.title}\n  {target.exam_page_url}')
    rec = adapter.gather(target)

    try:
        rpt = run_all(rec)
    except IsolationError as exc:
        print(f'\nISOLATION CHECK FAILED — nothing emitted.\n  {exc}')
        return 4

    print(f'\n--- {rec.title} ({rec.exam_id}) ---')
    print(f'sources read ({len(rec.sources_read)}):')
    for u in rec.sources_read:
        print(f'  · {u}')

    for heading, names in (('FOUND', rpt['found']),
                           ('NEEDS REVIEW', rpt['needsReview']),
                           ('NOT PUBLISHED BY THE AUTHORITY', rpt['notPublished']),
                           ('NOT EXTRACTED (our gap, not theirs)', rpt['notExtracted'])):
        print(f'\n{heading} ({len(names)}):')
        for n in names:
            f = rec.fields[n]
            if f.status is Status.FOUND:
                where = f' [p.{f.citation.page}]' if f.citation else ''
                print(f'  · {n}{where}')
            else:
                print(f'  · {n} — {f.note}')

    if rpt['foreignMentions']:
        print('\nMENTIONS ANOTHER AUTHORITY (for a person to judge):')
        for m in rpt['foreignMentions']:
            print(f'  · {m}')

    if rec.log:
        print('\nNOTES:')
        for line in rec.log:
            print(f'  · {line}')

    if args.emit:
        from .emit import header, render_exam
        with open(args.emit, 'w', encoding='utf-8') as fh:
            fh.write(header(rec, rpt) + '\n\n' + render_exam(rec) + '\n')
        print(f'\nTypeScript record -> {args.emit}')
        if rpt['lowCoverage']:
            print('  WARNING: few fields were sourced. That usually means this adapter '
                  'needs work for the notice\'s layout, not that the authority publishes little.')

    if args.json_out:
        payload = {
            'examId': rec.exam_id, 'code': rec.code, 'title': rec.title,
            'authorityName': rec.authority_name, 'officialDomain': rec.official_domain,
            'sourcesRead': rec.sources_read, 'log': rec.log,
            'fields': {
                n: {
                    'status': f.status.value, 'note': f.note, 'value': f.value,
                    'citation': (f.citation.__dict__ if f.citation else None),
                } for n, f in rec.fields.items()
            },
        }
        with open(args.json_out, 'w', encoding='utf-8') as fh:
            json.dump(payload, fh, indent=1, ensure_ascii=False, default=str)
        print(f'\nfull record -> {args.json_out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
