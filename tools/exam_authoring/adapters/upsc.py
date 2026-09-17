"""Union Public Service Commission — upsc.gov.in.

UPSC publishes the same two things for every examination it runs, which is what makes one
adapter cover all of them rather than just the CSE:

1. `/examinations/active-exams` and `/examinations/forthcoming-exams` list every exam, each
   linking to `/examinations/<exam name, URL-encoded>`.
2. That per-exam page is a plain label/value table — Date of Notification, Date of
   Commencement of Examination, **Last Date for Receipt of Applications** — plus a
   "Download Notification" link to the notice PDF, and a second table of the documents
   published since (admit card, question papers, written result).

The page is the authority on dates and the notice is the authority on rules, and they can
disagree: UPSC extended CSE 2026's last date by three days after the notice was printed.
This adapter therefore reads the page for dates and the PDF for everything else, and records
the disagreement as a corrigendum instead of picking a winner silently.
"""
from __future__ import annotations

import re
from urllib.parse import quote

from .. import extract
from ..record import ExamRecord, Field
from ..sources import FetchError, html_links, html_rows, load_html, load_pdf
from .base import ExamTarget

ROOT = 'https://www.upsc.gov.in'
LIST_PAGES = (
    f'{ROOT}/examinations/active-exams',
    f'{ROOT}/examinations/forthcoming-exams',
)


def _slugify_id(title: str) -> str:
    """A stable exam id from the exam's own printed name.

    The parenthetical stays in. UPSC lists "Civil Services (Preliminary)" and "Civil
    Services (Main)" as separate pages, and dropping the qualifier collapsed them onto one
    id — so one silently overwrote the other during discovery. Two documents must never
    share an id; that is the same rule the register follows.
    """
    t = title.lower()
    year = re.search(r'(20\d{2})', t)
    t = re.sub(r'[^a-z0-9]+', '-', t).strip('-')
    t = re.sub(r'-20\d{2}', '', t)
    t = re.sub(r'-(examination|exam)$', '', t)
    t = re.sub(r'-(examination|exam)-', '-', t)
    return f"exam-upsc-{t.strip('-')}" + (f'-{year.group(1)}' if year else '')


def _code(title: str) -> str:
    year = re.search(r'(20\d{2})', title)
    letters = ''.join(w[0] for w in re.findall(r'[A-Za-z]+', re.sub(r'\(.*?\)', '', title))[:4]).upper()
    return f'UPSC_{letters}' + (f'_{year.group(1)}' if year else '')


class UPSCAdapter:
    authority_name = 'Union Public Service Commission (UPSC)'
    official_domain = ROOT

    # ------------------------------------------------------------------ discovery
    def discover(self, query: str) -> list[ExamTarget]:
        wanted = [w for w in re.split(r'\W+', query.lower()) if len(w) > 2]
        seen: dict[str, ExamTarget] = {}
        for list_url in LIST_PAGES:
            try:
                page = load_html(list_url)
            except FetchError:
                continue
            for label, href in html_links(page, r'/examinations/'):
                if not re.search(r'/examinations/[^/]+%2C|/examinations/[A-Z]', href):
                    # the listing's own nav links have no exam name in them
                    if not re.search(r'\d{4}', label):
                        continue
                title = label.strip()
                if not title or len(title) < 8:
                    continue
                hay = title.lower()
                if wanted and not all(w in hay for w in wanted):
                    # allow a partial match on the distinctive words only
                    hits = sum(1 for w in wanted if w in hay)
                    if hits < max(1, len(wanted) - 1):
                        continue
                target = ExamTarget(
                    exam_id=_slugify_id(title),
                    code=_code(title),
                    title=f'UPSC {title}',
                    authority_name=self.authority_name,
                    official_domain=self.official_domain,
                    exam_page_url=href,
                )
                seen.setdefault(target.exam_id, target)

        # Best match first, so "--pick 0" is the exam the user actually named rather than
        # whichever one the listing happened to print first.
        def score(t: ExamTarget) -> tuple:
            hay = t.title.lower()
            covered = sum(1 for w in wanted if w in hay)
            exact = 1 if all(w in hay for w in wanted) else 0
            # a shorter title covering the same words is the more specific match
            return (-exact, -covered, len(hay))

        return sorted(seen.values(), key=score)

    # -------------------------------------------------------------------- gather
    def gather(self, target: ExamTarget) -> ExamRecord:
        rec = ExamRecord(
            exam_id=target.exam_id,
            code=target.code,
            title=target.title,
            authority_name=self.authority_name,
            official_domain=self.official_domain,
        )

        # --- 1. the exam page: dates, and the links to everything else
        page = None
        if target.exam_page_url:
            try:
                page = load_html(target.exam_page_url)
                rec.sources_read.append(target.exam_page_url)
            except FetchError as exc:
                rec.note(f'Exam page unreachable: {exc}')

        rows: list[list[str]] = []
        if page is not None:
            rows = html_rows(page)
            rec.set(extract.dates_from_rows(page, rows, f'{target.title} — UPSC examination page'))

            # The notice PDF and every document published since (papers, keys, admit card).
            for label, href in html_links(page, r'\.pdf$|Notice|Notification'):
                low = (label + ' ' + href).lower()
                if 'notice' in low or 'notif' in low:
                    target.notice_url = target.notice_url or href
                if re.search(r'question\s*paper|qp[-_]', low):
                    target.extra_urls.setdefault(f'paper::{label[:60]}', href)
                if re.search(r'answer\s*key', low):
                    target.extra_urls.setdefault(f'key::{label[:60]}', href)
                if re.search(r'cut[-\s]?off', low):
                    target.extra_urls.setdefault(f'cutoff::{label[:60]}', href)
            # The page's second table lists Document Type / Document / Date of Upload.
            for row in rows:
                if len(row) >= 2 and re.search(r'question paper|answer key|written result|admit card', row[0], re.I):
                    rec.note(f'Published document on the exam page: {row[0]} — {" | ".join(row[1:])}')

        # --- 2. the notice PDF: the rules
        if not target.notice_url:
            rec.set(Field.not_published('notice', 'No notification PDF linked on the exam page'))
            rec.note('No notice PDF found; only the exam page could be read.')
            return rec

        try:
            notice = load_pdf(target.notice_url)
            rec.sources_read.append(target.notice_url)
        except FetchError as exc:
            rec.set(Field.not_published('notice', f'Notice PDF unreachable: {exc}'))
            return rec

        title = f'{target.title} — Examination Notice'
        if notice.is_scanned:
            # Saying "scanned" matters: it is not the same claim as "the authority published
            # nothing", and the difference decides whether a person needs to read it by hand.
            rec.set(Field.needs_review('notice', target.notice_url,
                                       f'The notice PDF at {target.notice_url} has no text layer '
                                       f'({notice.page_count} pages of images). Its rules must be read by a person.'))
            rec.note('Notice is a scan — no rule extraction attempted, by design.')
            return rec

        rec.set(Field.found('notice', {'url': target.notice_url, 'pages': notice.page_count},
                            extract.cite(notice, title, 1, 'Whole notice', notice.page_text(1)[:300])))

        for fn in (extract.age_limits, extract.qualification, extract.attempts, extract.fee,
                   extract.services_list, extract.vacancies, extract.application_portal,
                   extract.how_to_apply, extract.admit_card, extract.scheme_tables):
            try:
                rec.set(fn(notice, title))
            except Exception as exc:                       # noqa: BLE001
                rec.note(f'{fn.__name__} failed: {exc!r}')

        # --- 3. dates: the page wins, and a disagreement is recorded, not hidden
        if page is None:
            rec.set(extract.dates_from_notice(notice, title))
        else:
            self._reconcile_close_date(rec, notice, title)

        # --- 4. what UPSC publishes for this exam, stated either way
        papers = {k: v for k, v in target.extra_urls.items() if k.startswith('paper::')}
        keys = {k: v for k, v in target.extra_urls.items() if k.startswith('key::')}
        rec.set(Field.found('officialPapers', papers,
                            extract.cite(page, f'{target.title} — UPSC examination page', 1,
                                         'Published documents', f'{len(papers)} question paper link(s)'))
                if papers else
                Field.not_published('officialPapers', 'UPSC lists no question paper for this exam yet'))
        rec.set(Field.found('answerKeys', keys,
                            extract.cite(page, f'{target.title} — UPSC examination page', 1,
                                         'Published documents', f'{len(keys)} answer key link(s)'))
                if keys else
                Field.not_published('answerKeys',
                                    'UPSC has published no answer key for this exam — scoring it would mean inventing answers'))
        return rec

    # ------------------------------------------------------------------ reconcile
    @staticmethod
    def _reconcile_close_date(rec: ExamRecord, notice, title: str) -> None:
        """The notice's own last date, checked against the page's.

        This is the CSE 2026 lesson made automatic: the notice printed 24 February and the
        page said 27 February, because the Commission extended the window afterwards. The
        page's date stays operative; the notice's is recorded as superseded.
        """
        page_dates = rec.value('dates') or []
        close = next((d for d in page_dates if d['type'] == 'APPLICATION_CLOSE'), None)
        if not close:
            return
        m = re.search(r'(?:online )?applications? can be (?:filled|submitted)\s*up\s*to\s*(.{0,60}?)(?:\.|$)',
                      notice.all_text(), re.I)
        if not m:
            return
        notice_iso = extract.parse_date(m.group(1))
        if not notice_iso:
            return
        page_iso = close['dateTimeStr'][:10]
        if notice_iso != page_iso:
            rec.set(Field.found('lastDateSuperseded', {
                'noticeDate': f'{notice_iso} {extract.parse_time(m.group(1))}',
                'pageDate': close['dateTimeStr'],
                'noticeExcerpt': extract._clean(m.group(0)),
            }, extract.cite(notice, title, notice.find_page(re.escape(m.group(0)[:30])) or 1,
                            'Last date for submission of applications', extract._clean(m.group(0)))))
            rec.note(f'Last date differs: notice says {notice_iso}, examination page says {page_iso}. '
                     f'The page is operative; the notice date is recorded as superseded.')
