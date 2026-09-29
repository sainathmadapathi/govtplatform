"""Fetching and reading an authority's own documents.

Nothing in this module interprets an exam. It only gets bytes from a government host and
turns them into text that still knows where it came from: every page of every PDF and every
table of every HTML page keeps its URL, so an extractor downstream can cite a document and a
page number rather than asserting a fact from nowhere.

Study material is never stored in the repo (see CLAUDE.md). The cache below holds only what
is needed to run an extraction twice without hammering a government host, lives in a
gitignored directory, and can be deleted at any time.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from html import unescape
from typing import Optional

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.exam_cache')

_UA = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/pdf,*/*',
    'Accept-Language': 'en-IN,en;q=0.9',
}

# Government hosts are intermittent from Indian networks (CLAUDE.md). A single timeout is
# not proof a document is missing, so every fetch retries before it gives up, and the
# failure is recorded rather than silently treated as "no such document".
_RETRIES = 3
_TIMEOUT = 45


class FetchError(RuntimeError):
    """Raised when a document could not be obtained. Never swallowed into a blank value."""


#: Public suffixes under which an Indian authority registers one name and then runs several
#: hosts on it: a commission's site, its apply portal and its results host are
#: `websitenew.<body>.gov.in`, `otr.<body>.gov.in`, `results.<body>.gov.in` -- one estate.
_TWO_LABEL_SUFFIXES = ('gov.in', 'nic.in', 'ac.in', 'co.in', 'org.in', 'net.in', 'res.in', 'edu.in')


def estate_of(host: str) -> str:
    """The registered domain a host belongs to: `otr.tgpsc.gov.in` -> `tgpsc.gov.in`,
    `www.ibps.in` -> `ibps.in`. Two hosts with one estate are one authority's own sites."""
    h = (host or '').lower().replace('www.', '').strip('.')
    labels = h.split('.')
    if len(labels) >= 3 and '.'.join(labels[-2:]) in _TWO_LABEL_SUFFIXES:
        return '.'.join(labels[-3:])
    return '.'.join(labels[-2:]) if len(labels) >= 2 else h


def same_estate(host: str, own_host: str) -> bool:
    """Is `host` the authority's own site, or a sibling host on its registered domain?"""
    h = (host or '').lower().replace('www.', '')
    own = (own_host or '').lower().replace('www.', '')
    if not h or not own:
        return False
    return h == own or h.endswith('.' + own) or estate_of(h) == estate_of(own)


@dataclass
class Document:
    """One document from an authority, with enough identity to cite it."""

    url: str
    kind: str                      # 'PDF' | 'HTML'
    fetched_at: str
    raw: bytes = field(repr=False, default=b'')
    #: PDF only - text per page, 1-indexed via page_text()
    pages: list[str] = field(default_factory=list, repr=False)
    #: HTML only - tag-stripped text
    text: str = field(default='', repr=False)
    #: True when a PDF carried no extractable text layer (scanned images).
    is_scanned: bool = False

    def page_text(self, page_number: int) -> str:
        """1-indexed, matching how a notice cites itself."""
        if 1 <= page_number <= len(self.pages):
            return self.pages[page_number - 1]
        return ''

    @property
    def page_count(self) -> int:
        return len(self.pages)

    def find_page(self, pattern: str, flags: int = re.I) -> Optional[int]:
        """The 1-indexed page a pattern first appears on, so a fact can cite its page."""
        rx = re.compile(pattern, flags)
        for i, page in enumerate(self.pages, start=1):
            if rx.search(page):
                return i
        return None

    def all_text(self) -> str:
        return self.text if self.kind == 'HTML' else '\n'.join(self.pages)


def _cache_path(url: str, suffix: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    key = hashlib.sha1(url.encode('utf-8')).hexdigest()[:20]
    return os.path.join(CACHE_DIR, f'{key}{suffix}')


def _now() -> str:
    return time.strftime('%Y-%m-%d')


def _encoded(url: str) -> str:
    """The same URL, safe to request.

    Authorities link to their own files with spaces and other characters `urllib` rejects,
    and a rejected request is a client-side failure -- never evidence that the document
    does not exist. Only the path is touched, and only characters that are already illegal
    in one; an already-encoded path passes through unchanged because `%` is left alone.
    """
    parts = urllib.parse.urlsplit(url)
    if not parts.scheme:
        return url
    return urllib.parse.urlunsplit((
        parts.scheme, parts.netloc,
        urllib.parse.quote(parts.path, safe="/%:@&=+$,~!*'()"),
        parts.query, parts.fragment))


def fetch(url: str, *, use_cache: bool = True, max_age_hours: int = 24) -> bytes:
    """Get a document's bytes, retrying before declaring it unreachable."""
    blob = _cache_path(url, '.bin')
    meta = _cache_path(url, '.json')
    if use_cache and os.path.exists(blob) and os.path.exists(meta):
        try:
            info = json.load(open(meta, encoding='utf-8'))
            if (time.time() - info.get('ts', 0)) < max_age_hours * 3600:
                return open(blob, 'rb').read()
        except Exception:
            pass

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    # Requested with its path encoded; cached under the URL as the authority wrote it.
    requested = _encoded(url)

    last = None
    for attempt in range(_RETRIES):
        try:
            req = urllib.request.Request(requested, headers=_UA)
            with urllib.request.urlopen(req, timeout=_TIMEOUT, context=ctx) as resp:
                data = resp.read()
            os.makedirs(CACHE_DIR, exist_ok=True)
            open(blob, 'wb').write(data)
            json.dump({'url': url, 'ts': time.time()}, open(meta, 'w', encoding='utf-8'))
            return data
        except Exception as exc:                      # noqa: BLE001 - reported, not hidden
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise FetchError(f'{url} could not be fetched after {_RETRIES} attempts: {last!r}')


def pdf_text(text: str) -> str:
    """A page's text with the printed hyphen restored where the extractor marked one.

    pdfium returns U+FFFE (a noncharacter) for a hyphen that ended a printed line, and a
    soft hyphen as U+00AD; "De-industrialization" came through as "De\\ufffeindustrialization"
    and reached a candidate's syllabus that way. The table reader already restored these."""
    return text.replace('\ufffe', '-').replace('\u00ad', '-')


def load_pdf(url: str, **kw) -> Document:
    """A PDF as per-page text. A scanned PDF is reported as scanned, never as empty."""
    import pypdfium2 as pdfium

    data = fetch(url, **kw)
    path = _cache_path(url, '.pdf')
    open(path, 'wb').write(data)
    doc = pdfium.PdfDocument(path)
    pages = []
    for i in range(len(doc)):
        try:
            pages.append(pdf_text(doc[i].get_textpage().get_text_range()))
        except Exception:
            pages.append('')
    # A notice with almost no extractable text is a scan. Saying so is the honest outcome:
    # the alternative is an extractor reporting "field not found" for a document it simply
    # could not read, which reads as "the authority did not publish it".
    total = sum(len(p.strip()) for p in pages)
    is_scanned = total < max(200, 40 * len(pages))
    return Document(url=url, kind='PDF', fetched_at=_now(), raw=data, pages=pages, is_scanned=is_scanned)


_TAG = re.compile(r'<[^>]+>')
_SCRIPT = re.compile(r'<(script|style)[^>]*>.*?</\1>', re.S | re.I)


def load_html(url: str, **kw) -> Document:
    data = fetch(url, **kw)
    html = data.decode('utf-8', 'replace')
    body = _SCRIPT.sub(' ', html)
    text = ' '.join(unescape(_TAG.sub(' ', body)).split())
    d = Document(url=url, kind='HTML', fetched_at=_now(), raw=data, text=text)
    d.html = html          # type: ignore[attr-defined]
    return d


_ROW = re.compile(r'<tr[^>]*>(.*?)</tr>', re.S | re.I)
_CELL = re.compile(r'<t[dh][^>]*>(.*?)</t[dh]>', re.S | re.I)


def html_rows(document: Document) -> list[list[str]]:
    """Every table row on an HTML page, as clean cell text.

    UPSC's per-examination pages are plain tables whose first cell is a label and whose
    second is the value ("Last Date for Receipt of Applications | 27/02/2026 - 6:00pm"),
    which is the most reliable structured data any of these authorities publish.
    """
    html = getattr(document, 'html', '')
    rows = []
    for rm in _ROW.finditer(html):
        cells = [' '.join(unescape(_TAG.sub(' ', c)).split()) for c in _CELL.findall(rm.group(1))]
        cells = [c for c in cells if c != '']
        if cells:
            rows.append(cells)
    return rows


#: An anchor as authorities actually write it: `href="…"`, `href='…'`, `href ="…"` (a space
#: before the equals sign), attributes in any order. The strict `href="` form missed a
#: commission's whole notification list, whose anchors were written `href ="preview/…"`.
_ANCHOR = re.compile(r'<a\b([^>]*)>(.*?)</a>', re.S | re.I)
_HREF = re.compile(r'''\bhref\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))''', re.I)


def html_links(document: Document, pattern: str = r'.*') -> list[tuple[str, str]]:
    """(text, absolute url) for links whose text or href matches, in page order.

    A relative href is resolved against the page it was found on, the way a browser does:
    "preview/abc" on /notifications is /preview/abc. Skipping those dropped every document
    a site linked without a leading slash.
    """
    html = getattr(document, 'html', '')
    rx = re.compile(pattern, re.I)
    out = []
    for m in _ANCHOR.finditer(html):
        hm = _HREF.search(m.group(1))
        if not hm:
            continue
        href = unescape(next(g for g in hm.groups() if g is not None)).strip()
        label = ' '.join(unescape(_TAG.sub(' ', m.group(2))).split())
        if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
            continue
        if not href.startswith('http'):
            href = urllib.parse.urljoin(document.url, href)
        if not href.startswith('http'):
            continue
        if rx.search(label) or rx.search(href):
            out.append((label, href.replace(' ', '%20')))
    return out


def load_document(url: str, **kw) -> Document:
    """A document as whatever it *is*, not whatever its address says.

    Authorities serve PDFs behind viewer routes with no extension ("/preview/<token>"), and
    reading one of those as HTML yields no text at all -- which then reads as "the document
    names no examination". The bytes are fetched once and the PDF magic decides; `load_pdf`
    re-reads them from the cache.
    """
    data = fetch(url, **kw)
    if data[:5] == b'%PDF-':
        return load_pdf(url, **kw)
    return load_html(url, **kw)
