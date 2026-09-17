"""Turning a gathered record into a TypeScript `Exam` entry.

Only sourced values are written. A field the run could not source is emitted as an empty
array or omitted entirely, which is deliberate: the app already renders honest empty states
for every section ("No milestones authored for this exam", "A practice form for this exam
has not been authored yet"), so an absent field shows as absent rather than as a plausible
invention. Filling a gap here to make a page look complete is the one thing this emitter
must never do.

Every value carries a `DataProvenance` naming the document, the page and the words it came
from, and anything that was NEEDS_REVIEW is emitted as `UNDER_VERIFICATION` so the UI badges
it as unconfirmed rather than official.
"""
from __future__ import annotations

import json
import re

from .record import ExamRecord, Field, Status


def ts(value) -> str:
    """A Python value as TypeScript source."""
    if value is None:
        return 'undefined'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return "'" + value.replace('\\', '\\\\').replace("'", "\\'").replace('\n', ' ') + "'"
    if isinstance(value, (list, tuple)):
        return '[' + ', '.join(ts(v) for v in value) + ']'
    if isinstance(value, dict):
        return '{ ' + ', '.join(f'{k}: {ts(v)}' for k, v in value.items()) + ' }'
    return ts(str(value))


def _prov(rec: ExamRecord, f: Field, suffix: str) -> str:
    """The provenance literal for one sourced field."""
    if not f.citation:
        return ''
    p = f.citation.to_provenance(
        prov_id=f'prov-{rec.exam_id}-{suffix}',
        level=f.verification_level,
    )
    return ts(p)


def _dates(rec: ExamRecord) -> str:
    f = rec.get('dates')
    if not f or not f.usable:
        return '[]'
    out = []
    # A row whose label matched no known milestone ("Date of Upload") is not emitted. The
    # union has no OTHER, and forcing it into the nearest member would invent a milestone.
    for i, d in enumerate(x for x in f.value if x['type'] != 'OTHER'):
        prov = _prov(rec, f, f'date-{i}')
        out.append('    ' + ts({
            'id': f"date-{rec.exam_id}-{i}",
            'type': d['type'],
            'label': d['label'],
            'dateTimeStr': d['dateTimeStr'],
            'timezone': 'Asia/Kolkata (IST)',
            'isTentative': False,
            'status': 'AVAILABLE',
        })[:-2] + f', provenance: {prov} }}')

    # A date the notice printed and the authority later changed is kept, struck through,
    # because the record is the chain and not only the latest value.
    sup = rec.get('lastDateSuperseded')
    if sup and sup.usable:
        prov = _prov(rec, sup, 'lastdate-superseded')
        out.append('    ' + ts({
            'id': f'date-{rec.exam_id}-close-superseded',
            'type': 'APPLICATION_CLOSE',
            'label': 'Last date printed in the notice (superseded)',
            'dateTimeStr': sup.value['noticeDate'],
            'timezone': 'Asia/Kolkata (IST)',
            'isTentative': False,
            'status': 'SUPERSEDED',
        })[:-2] + f', provenance: {prov} }}')
    return '[\n' + ',\n'.join(out) + '\n  ]'


def _corrigendums(rec: ExamRecord) -> str:
    sup = rec.get('lastDateSuperseded')
    if not (sup and sup.usable):
        return '[]'
    v = sup.value
    entry = {
        'id': f'corr-{rec.exam_id}-lastdate',
        'title': f"Last date changed from {v['noticeDate'][:10]} to {v['pageDate'][:10]}",
        'noticeNumber': f"{rec.authority_name} — examination page for this exam",
        'publishedDate': v['pageDate'][:10],
        'effectiveDate': v['noticeDate'][:10],
        'summary': (f"The notice prints \"{v['noticeExcerpt']}\" The authority's own examination "
                    f"page records {v['pageDate'][:10]} as the last date. The page is the later "
                    f"statement, so it is operative and the notice's date is kept struck through."),
        'pdfUrl': sup.citation.url if sup.citation else '',
        'status': 'ACTIVE',
        'diffSummary': f"Last date: {v['noticeDate'][:10]} (notice) → {v['pageDate'][:10]} (examination page).",
    }
    return '[\n    ' + ts(entry) + '\n  ]'


def _eligibility_highlights(rec: ExamRecord) -> str:
    cards = []
    for name, title in (('ageLimits', 'Age limits'),
                        ('qualification', 'Educational qualification'),
                        ('attempts', 'Number of attempts'),
                        ('fee', 'Fee')):
        f = rec.get(name)
        if not (f and f.usable and f.citation):
            continue
        if name == 'ageLimits':
            v = f.value
            body = (f"{v['minAge']} to {v['maxAge']} years"
                    + (f" as on {v['asOn']}" if v.get('asOn') else '')
                    + (f"; born on or after {v['bornNotEarlierThan']} and on or before "
                       f"{v['bornNotLaterThan']}." if v.get('bornNotEarlierThan') else '.'))
        elif name == 'fee':
            v = f.value
            body = v['text'][:400]
        elif name == 'attempts':
            body = f.value['text'][:400]
        else:
            body = str(f.value)[:400]
        cards.append('    ' + ts({'title': title, 'body': body})[:-2]
                     + f', provenance: {_prov(rec, f, name.lower())} }}')
    return ('[\n' + ',\n'.join(cards) + '\n  ]') if cards else '[]'


def _resources(rec: ExamRecord) -> str:
    """Links only — the content policy forbids storing anything (CLAUDE.md)."""
    items = []
    notice = rec.get('notice')
    if notice and notice.usable and notice.citation:
        url = notice.value['url'] if isinstance(notice.value, dict) else notice.value
        items.append('    ' + ts({
            'id': f'res-{rec.exam_id}-notice',
            'title': f'{rec.title} — Examination Notice (official PDF)',
            'subject': 'Official Gazette',
            'author': rec.authority_name,
            'type': 'OFFICIAL_PDF',
            'resourceFormat': 'DIRECT_PDF',
            'url': url,
            'directPdfUrl': url,
            'officialTag': f'{rec.code} — OFFICIAL NOTICE',
            'recommendedFor': 'The rules themselves, from the authority that wrote them.',
            'description': 'The examination notice this record was read from.',
            'linkVerifiedDate': notice.citation.verified_date,
        })[:-2] + f', provenance: {_prov(rec, notice, "notice")} }}')

    papers = rec.get('officialPapers')
    if papers and papers.usable:
        for i, (label, url) in enumerate(sorted(papers.value.items())[:12]):
            items.append('    ' + ts({
                'id': f'res-{rec.exam_id}-paper-{i}',
                'title': label.split('::', 1)[-1],
                'subject': 'Previous Year Papers',
                'author': rec.authority_name,
                'type': 'OFFICIAL_PDF',
                'resourceFormat': 'DIRECT_PDF',
                'url': url,
                'directPdfUrl': url,
                'officialTag': f'{rec.code} — OFFICIAL QUESTION PAPER',
                'recommendedFor': 'The real paper, as the authority published it.',
                'description': 'Published by the authority on this exam’s own page.',
                'linkVerifiedDate': papers.citation.verified_date if papers.citation else '',
            })[:-2] + f', provenance: {_prov(rec, papers, f"paper-{i}")} }}')
    return ('[\n' + ',\n'.join(items) + '\n  ]') if items else '[]'


def _application_guide(rec: ExamRecord) -> str:
    portal = rec.value('applicationPortal') or rec.official_domain
    how = rec.get('howToApply')
    steps = '[]'
    if how and how.usable:
        # The section is kept whole, as one cited step. Splitting an authority's prose into
        # invented sub-steps would be GovOS writing the process rather than quoting it.
        steps = '[\n    ' + ts({
            'stepNumber': 1,
            'title': 'How to Apply — as the notice states it',
            'portalUrl': portal,
            'instructions': [how.value[:1200]],
            'mandatoryFields': [],
            'commonMistakesToAvoid': [],
        }) + '\n    ]'
    guide = {
        'officialPortal': portal,
        'photoRules': {'documentType': 'As stated on the portal’s upload screen', 'dimensions': '',
                       'fileFormat': '', 'fileSize': '', 'rules': [], 'sampleDescription': ''},
        'signatureRules': {'documentType': 'As stated on the portal’s upload screen', 'dimensions': '',
                           'fileFormat': '', 'fileSize': '', 'rules': [], 'sampleDescription': ''},
        'certificateRules': [],
        'rejectionPitfalls': [],
    }
    body = ts(guide)[:-2]
    return body + f', otrSteps: {steps} }}'


def render_exam(rec: ExamRecord) -> str:
    """The whole `Exam` literal for this record."""
    admit = rec.get('admitCard')
    admit_ts = 'undefined'
    if admit and admit.usable:
        admit_ts = ts({
            'status': 'NOT_YET_ANNOUNCED',
            'releaseDateStr': '',
            'officialPortalUrl': admit.value.get('portalUrl') or rec.value('applicationPortal') or rec.official_domain,
            'loginCredentialsRequired': [],
            'instructions': [admit.value['text'][:500]],
            'cityIntimationAvailable': False,
        })

    posts_ts, unclassified = _posts(rec)

    lines = [
        f'export const {rec.code}_EXAM: Exam = {{',
        f'  id: {ts(rec.exam_id)},',
        f'  code: {ts(rec.code)},',
        f'  title: {ts(rec.title)},',
        f'  authorityName: {ts(rec.authority_name)},',
        f'  officialDomain: {ts(rec.official_domain)},',
        f"  crucialEligibilityDate: {ts((rec.value('ageLimits') or {}).get('asOn') or '')},",
        '  isGoldenJourney: false,',
        '  isDemoData: false,',
        f'  overviewDescription: {ts(_overview(rec))},',
        f"  vacanciesTotal: {ts(rec.value('vacancies') or '')},",
        f'  posts: {posts_ts},',
        f'  dates: {_dates(rec)},',
        f"  globalRuleGroup: {{ id: 'rules-{rec.exam_id}', operator: 'AND', rules: [] }},",
        '  stages: [],',
        '  syllabus: [],',
        '  practiceQuestions: [],',
        f'  corrigendums: {_corrigendums(rec)},',
        '  cutoffsHistory: [],',
        f'  resources: {_resources(rec)},',
        '  faqs: [],',
        f'  applicationGuide: {_application_guide(rec)},',
        '  roadmapTracks: [],',
        f'  admitCardDetails: {admit_ts},',
        f'  eligibilityHighlights: {_eligibility_highlights(rec)},',
        f'  officialLinks: {ts([{"title": f"{rec.authority_name} — official website", "url": rec.official_domain, "note": "The authority’s own site."}])},',
        '};',
    ]
    return '\n'.join(lines)


#: The quotation marks these notices use around a Group letter: straight, and the curly
#: pair that actually appears in the PDFs. Built from escapes so this file stays ASCII.
_Q = "['‘’“”\"]?"
_GROUP_RX = re.compile(r"Group\s*" + _Q + r"\s*([AB])\s*" + _Q)
_GROUP_TAIL_RX = re.compile(r",?\s*Group\s*" + _Q + r"[AB]" + _Q + r"\s*$")


def classification_of(post_name: str) -> str:
    """The Group the authority printed on this service's own line, or '' if it printed none.

    UPSC writes "Indian Audit and Accounts Service, Group 'A'". It does not write a Group
    for the IAS, IFS or IPS, and those three being Group A is knowledge from elsewhere —
    so this returns '' for them rather than supplying the answer from memory.
    """
    # The notices wrap the Group letter in curly quotation marks, and the class therefore
    # has to hold both those and a straight apostrophe. It is written with a double-quoted
    # regex because a straight quote inside a single-quoted literal closes the string.
    m = re.search(_GROUP_RX, post_name)
    if not m:
        return ''
    group = m.group(1).upper()
    if group == 'A':
        return 'Group A (Gazetted)'
    # The notices that distinguish them say so; without that word the safe read of "Group B"
    # in a gazetted-services notice is the gazetted one, and it is flagged in the header.
    return 'Group B (Non-Gazetted)' if re.search(r'non-?gazetted', post_name, re.I) else 'Group B (Gazetted)'


def _posts(rec: ExamRecord) -> tuple[str, list[str]]:
    """Posts whose Group the authority printed. The rest are returned to be named, not faked."""
    posts = rec.get('posts')
    if not (posts and posts.usable):
        return '[]', []
    rows, skipped = [], []
    for i, name in enumerate(posts.value[:60]):
        cls = classification_of(name)
        if not cls:
            skipped.append(name)
            continue
        age = rec.value('ageLimits') or {}
        rows.append('    ' + ts({
            'id': f'post-{rec.exam_id}-{i}',
            'postName': re.sub(_GROUP_TAIL_RX, '', name).strip(),
            'department': rec.authority_name,
            'payLevel': '',
            'payScale': '',
            'classification': cls,
            'minAge': age.get('minAge', 0),
            'maxAge': age.get('maxAge', 0),
        })[:-2] + f', provenance: {_prov(rec, posts, f"post-{i}")} }}')
    if not rows:
        return '[]', skipped
    return '[\n' + ',\n'.join(rows) + '\n  ]', skipped


def _overview(rec: ExamRecord) -> str:
    bits = [f'{rec.title}, conducted by {rec.authority_name}.']
    if rec.value('vacancies'):
        bits.append(f"The notice states approximately {rec.value('vacancies')} vacancies.")
    dates = rec.value('dates') or []
    close = next((d for d in dates if d['type'] == 'APPLICATION_CLOSE'), None)
    if close:
        bits.append(f"Applications close {close['dateTimeStr']}.")
    bits.append('Read from the authority’s own notice and examination page by the GovOS '
                'exam-authoring pipeline; sections with no sourced data are shown as unauthored '
                'rather than filled in.')
    return ' '.join(bits)


def header(rec: ExamRecord, report: dict) -> str:
    """A comment block recording exactly what this record can and cannot claim."""
    lines = [
        '/**',
        f' * {rec.title}',
        ' *',
        f' * Generated by tools/exam_authoring from {rec.authority_name}’s own documents.',
        ' * Sources read:',
    ]
    lines += [f' *   - {u}' for u in rec.sources_read]
    lines.append(' *')
    lines.append(f" * Sourced: {', '.join(report['found']) or 'nothing'}")
    if report.get('needsReview'):
        lines.append(f" * Needs review: {', '.join(report['needsReview'])}")
    if report.get('notPublished'):
        lines.append(f" * The authority publishes no: {', '.join(report['notPublished'])}")
    if report.get('notExtracted'):
        lines.append(f" * Not extracted by this tool (read by hand): {', '.join(report['notExtracted'])}")
    _, skipped = _posts(rec)
    if skipped:
        lines.append(' *')
        lines.append(' * Posts the authority listed without printing a Group classification, which')
        lines.append(' * `PostRequirement` requires and this pipeline will not supply from memory:')
        lines += [f' *   - {p}' for p in skipped]
        lines.append(' * Add them by hand with their classification cited, or widen the type.')
    lines.append(' *')
    lines.append(' * Empty arrays below are unauthored, not zero. Nothing here is invented to')
    lines.append(' * fill a section; see CLAUDE.md on the provenance chain.')
    lines.append(' */')
    return '\n'.join(lines)
