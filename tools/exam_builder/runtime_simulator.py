"""A practice application form for an exam GovOS read by machine, from that exam's own record.

The mock form (`ApplicationSimulatorSpec`) used to exist only where a person had authored one
from a notice. Every check such a form runs is a fact the record already holds, cited: when
applications were accepted, how old a candidate may be on the crucial date, which categories
the notice exempts from a fee. This builds the form from those facts and nothing else:

  * a check is emitted only where its fact is in the record -- an exam with no window on
    record gets no window check, never a default one;
  * every check quotes the statement it enforces and names its document and page;
  * the window runs from the earliest opening the authority ever printed to the close that
    governs now, because a later re-opening adds days and takes none away: an application
    made in the original window was not late;
  * age is checked against every post's printed band at once and before relaxation, so it
    says only what is true of every post: too young for all of them is a fault, older than
    all of them is a warning that a relaxation the notice prints may still apply;
  * the portal's own screens are not reproduced, and the form says so.

It names no exam and no authority; it reads the runtime shape alone.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional

from .runtime_evidence import is_provenance


def _day(value: str) -> Optional[date]:
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', value or '')
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def _years_before(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year - years)
    except ValueError:                        # 29 February
        return d.replace(year=d.year - years, day=28)


def _where(p: dict) -> str:
    page = f", page {p['pageNumber']}" if p.get('pageNumber') else ''
    clause = f" — {p['clauseNumber']}" if p.get('clauseNumber') else ''
    return f"{p.get('documentTitle', 'the notice')}{page}{clause}"


def _words(p: dict) -> str:
    return str(p.get('excerptText') or '').strip()[:300]


def _category_label(raw: str) -> str:
    return re.sub(r'^\s*category\s*:\s*', '', raw or '', flags=re.I).strip()


def _distinct_categories(exemptions: list[dict]) -> list[dict]:
    """Each exempt category once. "SC" beside "Scheduled Castes" is the same category, so a
    short all-letter name that is the initials of another listed name is dropped."""
    named = [(x, _category_label(x.get('category') or '')) for x in exemptions if x.get('category')]
    initials = {''.join(w[0] for w in re.findall(r'[A-Za-z]+', n)).lower() for _x, n in named
                if len(re.findall(r'[A-Za-z]+', n)) > 1}
    out, seen = [], set()
    for x, name in named:
        key = name.lower()
        if not name or key in seen:
            continue
        if re.fullmatch(r'[A-Za-z]{2,5}', name) and key in initials:
            continue
        seen.add(key)
        out.append({'name': name[:1].upper() + name[1:], 'exemption': x})
    return out


def build_simulator(exam: dict) -> Optional[dict]:
    """The practice form for this exam, or None where the record holds no check to run."""
    modules: list[dict] = []
    traps: list[dict] = []
    anchor: Optional[dict] = None             # the provenance the whole form cites

    # ------------------------------------------------------------ particulars and age
    posts = [p for p in exam.get('posts') or [] if p.get('postName')]
    asof = _day(str(exam.get('crucialEligibilityDate') or ''))
    bands = [(int(p['minAge']), int(p['maxAge'])) for p in posts
             if isinstance(p.get('minAge'), int) and isinstance(p.get('maxAge'), int) and p['maxAge'] > 0]
    age_prov = (exam.get('factEvidence') or {}).get('crucialEligibilityDate')
    particulars: list[dict] = []
    if posts:
        particulars.append({
            'id': 'post', 'label': 'Post applied for', 'kind': 'SELECT',
            'defaultValue': posts[0]['id'],
            'options': [{'value': p['id'], 'label': p['postName'][:90]} for p in posts[:80]],
            'noteFromNotice': 'The posts this notice recruits to. Age limits and qualifications differ by post '
                              '— see Eligibility & Posts for the one you choose.'})
    if asof and bands and is_provenance(age_prov):
        youngest, oldest = min(lo for lo, _hi in bands), max(hi for _lo, hi in bands)
        latest_birth = _years_before(asof, youngest)                          # born on or before
        earliest_birth = _years_before(asof, oldest + 1) + timedelta(days=1)  # born on or after
        default_birth = _years_before(asof, min(oldest, youngest + 7))
        particulars.append({
            'id': 'dob', 'label': 'Date of birth', 'kind': 'DATE',
            'defaultValue': default_birth.isoformat(),
            'noteFromNotice': f'Age is reckoned on {asof.isoformat()}, as the notice states.'})
        traps.append({
            'id': 'trap-too-young', 'severity': 'CRITICAL',
            'rule': {'kind': 'DATE_OUTSIDE', 'fieldId': 'dob', 'earliest': '1900-01-01',
                     'latest': latest_birth.isoformat()},
            'title': 'Under the minimum age for every post',
            'problem': f'On {asof.isoformat()} this candidate would be under {youngest}, the lowest minimum age '
                       f'this notice prints for any post.',
            'whyItMatters': 'No relaxation lowers a minimum age; the application would be ineligible for every post.',
            'rememberRule': f'Age is counted on {asof.isoformat()}, not on the day you apply.',
            'officialClause': _words(age_prov), 'noticeReference': _where(age_prov)})
        relaxations = [r for r in exam.get('ageRelaxations') or [] if r.get('status') == 'VERIFIED']
        traps.append({
            'id': 'trap-over-age', 'severity': 'WARNING',
            'rule': {'kind': 'DATE_OUTSIDE', 'fieldId': 'dob', 'earliest': earliest_birth.isoformat(),
                     'latest': '2100-12-31'},
            'title': 'Over the upper age limit for every post',
            'problem': f'On {asof.isoformat()} this candidate would be over {oldest}, the highest upper age '
                       f'limit this notice prints for any post.',
            'whyItMatters': ('Only an age relaxation the notice prints can keep this application eligible: '
                             + ', '.join(f"{r['category']} (+{int(r['years'])} years)" for r in relaxations
                                         if r.get('years') is not None)
                             + '.') if relaxations else 'The notice prints no relaxation that GovOS could verify.',
            'rememberRule': 'A relaxation applies only to the category the notice names, with its own certificate.',
            'officialClause': _words(age_prov), 'noticeReference': _where(age_prov)})
        anchor = anchor or age_prov
    if particulars:
        modules.append({'moduleNumber': len(modules) + 1, 'cardName': 'Particulars',
                        'title': 'Post and date of birth',
                        'introduction': 'The particulars the notice judges eligibility on.',
                        'noticeReference': _where(age_prov) if is_provenance(age_prov) else '',
                        'fields': particulars})

    # ------------------------------------------------------------ fee exemption
    fee = (exam.get('applicationGuide') or {}).get('fee') or {}
    exempt = _distinct_categories(fee.get('exemptions') or [])
    fee_prov = next((c['exemption'].get('provenance') for c in exempt
                     if is_provenance(c['exemption'].get('provenance'))), fee.get('provenance'))
    if exempt and is_provenance(fee_prov):
        none = '__none__'
        modules.append({
            'moduleNumber': len(modules) + 1, 'cardName': 'Fee', 'title': 'Fee and exemption',
            'introduction': 'Fee as printed: ' + ' + '.join(f'Rs. {a}' for a in fee.get('amounts') or []) + '.'
                            if fee.get('amounts') else 'The fee the notice prints.',
            'noticeReference': _where(fee_prov),
            'fields': [
                {'id': 'category', 'label': 'Which of these applies to you?', 'kind': 'SELECT',
                 'defaultValue': none,
                 'options': [{'value': none, 'label': 'None of the categories the notice exempts'}]
                            + [{'value': f'cat-{i}', 'label': c['name'][:80] + (
                                f" (from the {c['exemption']['exemptedFeeType'].replace('_', ' ').lower()} fee)"
                                if c['exemption'].get('exemptedFeeType') else '')}
                               for i, c in enumerate(exempt)]},
                {'id': 'claimExemption', 'label': 'Claiming a fee exemption?', 'kind': 'RADIO',
                 'defaultValue': 'no', 'options': [{'value': 'no', 'label': 'No'}, {'value': 'yes', 'label': 'Yes'}]},
            ]})
        traps.append({
            'id': 'trap-exemption', 'severity': 'CRITICAL',
            'rule': {'kind': 'VALUE_IN_ALL', 'conditions': [
                {'fieldId': 'claimExemption', 'values': ['yes']}, {'fieldId': 'category', 'values': [none]}]},
            'title': 'Exemption claimed without an exempt category',
            'problem': 'A fee exemption is claimed, but none of the categories the notice exempts applies.',
            'whyItMatters': 'An unpaid fee the notice does not waive is a defective application.',
            'rememberRule': 'Only the categories the notice names are exempt, and only from the fee it names.',
            'officialClause': _words(fee_prov), 'noticeReference': _where(fee_prov)})
        anchor = anchor or fee_prov

    # ------------------------------------------------------------ the window
    dates = exam.get('dates') or []
    opens = [(_day(d.get('dateTimeStr', '')), d) for d in dates if d.get('type') == 'APPLICATION_OPEN']
    closes = [(_day(d.get('dateTimeStr', '')), d) for d in dates
              if d.get('type') == 'APPLICATION_CLOSE' and d.get('status') != 'SUPERSEDED']
    opens = [(day, d) for day, d in opens if day]
    closes = [(day, d) for day, d in closes if day]
    if opens and len({day for day, _d in closes}) == 1:
        first_open, open_row = min(opens, key=lambda x: x[0])
        close_day, close_row = closes[0]
        close_prov = close_row.get('provenance') or {}
        if is_provenance(close_prov) and first_open <= close_day:
            revised = bool(close_prov.get('supersedes'))
            modules.append({
                'moduleNumber': len(modules) + 1, 'cardName': 'Submission', 'title': 'Submitting the form',
                'introduction': f'Applications are accepted from {first_open.isoformat()} to {close_day.isoformat()}'
                                + (' — the close was revised by a later official statement.' if revised else '.'),
                'noticeReference': _where(close_prov),
                'fields': [{'id': 'submittedOn', 'label': 'Date you submit the form', 'kind': 'DATE',
                            'defaultValue': first_open.isoformat(),
                            'noteFromNotice': f'Last date: {close_day.isoformat()}.'}]})
            old = [p.get('excerptText') for p in close_prov.get('supersedes') or [] if p.get('excerptText')]
            traps.append({
                'id': 'trap-window', 'severity': 'CRITICAL',
                'rule': {'kind': 'DATE_OUTSIDE', 'fieldId': 'submittedOn', 'earliest': first_open.isoformat(),
                         'latest': close_day.isoformat()},
                'title': 'Outside the application window',
                'problem': f'The form is dated outside {first_open.isoformat()} to {close_day.isoformat()}.',
                'whyItMatters': 'An application outside the window is not accepted.',
                'rememberRule': ('The date that governs is the later official one: the notice first printed '
                                 f'“{old[0]}”.') if old else 'Submit before the last date; do not wait for its last hours.',
                'officialClause': _words(close_prov), 'noticeReference': _where(close_prov)})
            anchor = anchor or close_prov

    if not traps or anchor is None:
        return None
    portal = (exam.get('applicationGuide') or {}).get('officialPortal') or exam.get('officialDomain') or ''
    return {
        'examId': exam['id'],
        'portalName': f"{exam.get('authorityName', 'The authority')}'s application portal",
        'portalUrl': portal,
        'sourceDocumentTitle': anchor.get('documentTitle', ''),
        'sourceDocumentUrl': anchor.get('officialUrl', ''),
        'modelledOnNote': ('Built by GovOS from the rules this exam’s own notice prints — each check below quotes '
                           'the statement it enforces. The portal’s own screens are not reproduced; practise the '
                           'rules here, then apply on the official portal.'),
        'modules': modules,
        'traps': traps,
        'cleanSubmissionNote': 'Nothing in this form breaks a rule the notice prints. On the real portal, check '
                               'every entry against your own certificates before you submit.',
        'provenance': dict(anchor),
    }
