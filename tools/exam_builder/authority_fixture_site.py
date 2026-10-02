"""An invented authority's website, served from memory, for the authority-discovery tests.

Its pages are laid out the way a real state commission's are -- a home page with navigation and a
notice ticker, a notifications listing, an old-question-papers page whose items sit under list
labels ("1.AE.") with one item on a retired domain and one listed without a link, a page built by
script that lists nothing, a chain of archive pages, a registration portal on a sister host -- but
it names no real authority, exam or website. Nothing here touches the network.

Not a test module (pytest collects test_*.py only).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Optional

ROOT = 'https://www.epsc.gov.in/'
AUTHORITY = 'Example Public Service Commission'
LEGACY_PDF = 'http://old.expsc.gov.in/OldQuestionPapers/AEE-GS-QP.pdf'
OTR = 'https://otr.epsc.gov.in/login?type=new'
APPLY = 'https://apply.epsc.gov.in/'
SOCIAL = 'https://x.com/epsc_official'
CHANNEL = 'https://www.youtube.com/@epsc_official'
COACHING = 'https://coaching.example.com/epsc-papers'
#: The exam vendor's practice interface, linked from the authority's home page (someone else's site).
VENDOR_MOCK = 'https://www.vendor-exams.example.com/OnlineAssessment/index.html'


@dataclass
class FakeResponse:
    """The fields authority discovery reads from `claude_cli.discovery.FetchResult`."""

    ok: bool = True
    status: int = 200
    final_url: str = ''
    content_type: str = 'text/html'
    text: str = ''
    error: str = ''
    content_hash: str = ''
    truncated: bool = False
    hops: list = field(default_factory=list)


def _html(title: str, body: str) -> str:
    return f'<html><head><title>{title}</title></head><body>{body}</body></html>'


NAV = f"""
<nav><ul>
  <li><a href="/">Home</a></li>
  <li><a href="/about.jsp">About Us</a></li>
  <li><a href="/notifications.jsp">Notifications</a></li>
  <li><a href="/oldquestionp.jsp">Old Question Papers</a></li>
  <li><a href="/syllabus.jsp">Scheme &amp; Syllabus</a></li>
  <li><a href="/results.jsp">Results</a></li>
  <li><a href="/contactUs.jsp">Contact Us</a></li>
</ul></nav>
"""

HOME = _html(f'{AUTHORITY}', NAV + f"""
<h3>Candidate Services</h3>
<ul>
  <li><a href="{OTR}">One Time Registration</a></li>
  <li><a href="{APPLY}">Apply Online</a></li>
  <li><a href="/knowYourId.jsp">Know Your EPSC ID</a></li>
  <li><a href="/officeLogin.jsp">Official Login</a></li>
  <li><a href="{VENDOR_MOCK}">Online Mock Exam</a></li>
</ul>
<h3>Latest News</h3>
<ul>
  <li><a href="/pdf/n05-2026-web-note.pdf">GROUP-I SERVICES - NOTIFICATION NO.05/2026 - EXTENSION OF RECEIPT OF ONLINE APPLICATIONS UPTO 11/09/2026 - WEB NOTE</a></li>
</ul>
<h3>Follow us</h3>
<ul>
  <li><a href="{SOCIAL}">EPSC on X</a></li>
  <li><a href="{CHANNEL}">EPSC YouTube channel</a></li>
</ul>
<script>var x = '<a href="/hidden.jsp">hidden</a>';</script>
""")

NOTIFICATIONS = _html('Notifications', NAV + """
<h3 class="mainhead">Notifications</h3>
<ul>
  <li><a href="/pdf/n05-2026.pdf">05/2026 - GROUP-I SERVICES</a></li>
  <li><a href="/pdf/n06-2026.pdf">06/2026 - GROUP-II SERVICES (GENERAL RECRUITMENT)</a></li>
  <li><a href="/pdf/n07-2026.pdf">07/2026 - ASSISTANT ENGINEERS</a></li>
  <li><a href="/pdf/n04-2022.pdf">04/2022 - Group - I Services</a></li>
  <li><a href="/archive/2025.jsp">Notifications Archive 2025</a></li>
</ul>
""")

OLD_PAPERS = _html('Old Question Papers', NAV + f"""
<h3 class="mainhead">Old Question Papers:</h3>
<ul>
  <li><a href="/preview/accounts-shift2.pdf">1.Accounts and Audit 21-Feb Shift 2 Actual.</a></li>
  <li><a>1.AE. </a> <br> <a href="/preview/ae-civil.pdf">1.AE-CIVIL.</a> <br>
      <a href="/preview/ae-gs.pdf?utm_source=newsletter#top">2.AE-GS.</a></li>
  <li>2.ASSISTANT EXECUTIVE ENGINEER-CIVIL. <br> <a href="/preview/aee-civil.pdf">1.AEE-CIVIL.</a> <br>
      <a href="{LEGACY_PDF}">2.AEE-GS.</a></li>
  <li><a>3.TOWN PLANNING BUILDING OVERSEER.</a> <a href="/preview/tpbo-gs.pdf">1.TPBO-GS &amp; GA.</a>
      <a href="#">2.TPBO-Intermediate Vocational Standard.</a></li>
  <li><a href="/files/ae-civil-copy.pdf">4.AE-CIVIL (copy).</a></li>
  <li><a href="{COACHING}">More papers (external)</a></li>
</ul>
""")

SYLLABUS = _html('Scheme & Syllabus', NAV + """
<h3>Scheme &amp; Syllabus</h3>
<ul>
  <li><a href="/pdf/g1-syllabus.pdf">Group-I Services</a></li>
  <li><a href="/pdf/g2-syllabus.pdf">Group-II Services</a></li>
  <li><a href="/pdf/ae-syllabus.pdf">Assistant Engineers</a></li>
</ul>
""")

# A page built by script: the server sends a shell with nothing of its own in it.
RESULTS = _html('Results', NAV + '<div id="app"></div><script src="/js/results.js"></script>')

ABOUT = _html('About Us', NAV + '<p>The Commission was constituted under Article 315.</p>')


def _archive(year: int) -> str:
    return _html(f'Notifications Archive {year}', NAV + f"""
<h3>Notifications Archive {year}</h3>
<ul>
  <li><a href="/pdf/old-{year}-a.pdf">{year} - Notification A</a></li>
  <li><a href="/pdf/old-{year}-b.pdf">{year} - Notification B</a></li>
  <li><a href="/pdf/old-{year}-c.pdf">{year} - Notification C</a></li>
  <li><a href="/archive/{year - 1}.jsp">Notifications Archive {year - 1}</a></li>
</ul>
""")


COACHING_PAGE = _html('EPSC papers', """
<ul>
  <li><a href="https://coaching.example.com/paper-1">Paper 1</a></li>
  <li><a href="https://coaching.example.com/paper-2">Paper 2</a></li>
  <li><a href="https://coaching.example.com/paper-3">Paper 3</a></li>
</ul>""")


def _pdf(name: str, *, same_as: Optional[str] = None) -> FakeResponse:
    body = (same_as or name).encode('utf-8')
    return FakeResponse(content_type='application/pdf', text='', content_hash=hashlib.sha256(body).hexdigest()[:24])


class FakeSite:
    """`fetch(url)` over the invented site. Records every URL asked for, in order."""

    def __init__(self, *, extra: Optional[dict] = None, failing: tuple = (LEGACY_PDF,)) -> None:
        self.calls: list = []
        self.failing = set(failing)
        pages = {
            ROOT: HOME,
            'https://www.epsc.gov.in/notifications.jsp': NOTIFICATIONS,
            'https://www.epsc.gov.in/oldquestionp.jsp': OLD_PAPERS,
            'https://www.epsc.gov.in/syllabus.jsp': SYLLABUS,
            'https://www.epsc.gov.in/results.jsp': RESULTS,
            'https://www.epsc.gov.in/about.jsp': ABOUT,
            'https://www.epsc.gov.in/contactUs.jsp': ABOUT,
            COACHING: COACHING_PAGE,
        }
        for year in range(2025, 2015, -1):
            pages[f'https://www.epsc.gov.in/archive/{year}.jsp'] = _archive(year)
        pages.update(extra or {})
        self.pages = pages

    def __call__(self, url: str) -> FakeResponse:
        self.calls.append(url)
        if url in self.failing:
            return FakeResponse(ok=False, status=0, error='connection timed out')
        if url in self.pages:
            return FakeResponse(final_url=url, text=self.pages[url], content_hash=hashlib.sha256(
                self.pages[url].encode('utf-8')).hexdigest()[:24])
        if url.endswith('ae-civil-copy.pdf'):
            return _pdf(url, same_as='ae-civil')            # the same bytes at a second address
        if url.endswith('ae-civil.pdf'):
            return _pdf(url, same_as='ae-civil')
        if url.lower().split('?')[0].endswith('.pdf'):
            return _pdf(url)
        return FakeResponse(ok=False, status=404, error='HTTP 404')
