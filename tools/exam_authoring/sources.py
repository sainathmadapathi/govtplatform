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
import time
import urllib.parse
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
#: The largest document read: an official notice is a few MB (UPSC CSE 2026's 159-page notice, SSC CGL
#: 2026's 132 pages); a scanned question booklet runs to tens of MB. A larger file is refused, never read
#: in part -- half a notice is a document that "does not mention" what is on its missing pages.
SOURCE_MAX_BYTES = 40 * 1024 * 1024
#: The whole download, beyond the per-operation _TIMEOUT: a host that trickles bytes cannot hold a build.
SOURCE_MAX_SECONDS = 180
#: Failures worth another attempt: a slow or flaky government host. A refused address, a certificate that
#: does not verify, an HTTP error or an oversized file will not change on retry.
_RETRYABLE = ('TIMEOUT', 'NETWORK')


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
    """Get a document's bytes, retrying before declaring it unreachable.

    Through GovOS's one guarded fetch (`claude_cli.discovery.fetch_checked`): every hop validated and
    resolved to a public address before connecting, TLS certificates and host names verified, each
    socket operation and the whole download time-bounded, at most SOURCE_MAX_BYTES read. It used to
    open the URL with certificate checks switched off, follow any redirect anywhere (a private address,
    ftp:) and read without limit; a URL with no scheme or a file: one is now refused, never read from disk.
    The cache holds only what this guarded fetch returned (`.checked.*`; nothing fetched the old way is reused).
    """
    from ..claude_cli.discovery import fetch_checked

    blob = _cache_path(url, '.checked.bin')
    meta = _cache_path(url, '.checked.json')
    if use_cache and os.path.exists(blob) and os.path.exists(meta):
        try:
            info = json.load(open(meta, encoding='utf-8'))
            if (time.time() - info.get('ts', 0)) < max_age_hours * 3600:
                return open(blob, 'rb').read()
        except Exception:
            pass

    # Requested with its path encoded; cached under the URL as the authority wrote it.
    try:
        requested = _encoded(url)
    except ValueError as exc:                       # "http://[x/": a malformed address is a FetchError like any other
        raise FetchError(f'{url} could not be fetched after 0 attempts: not a valid web address ({type(exc).__name__})') from exc

    last = ''
    attempts = 0
    for attempt in range(_RETRIES):
        attempts += 1
        result = fetch_checked(requested, timeout=_TIMEOUT, max_bytes=SOURCE_MAX_BYTES, keep_body=True,
                               max_seconds=SOURCE_MAX_SECONDS, headers=_UA)
        if result.ok and result.truncated:
            raise FetchError(f'{url} is larger than {SOURCE_MAX_BYTES // (1024 * 1024)} MB, so it was not read')
        if result.ok:
            data = result.body
            os.makedirs(CACHE_DIR, exist_ok=True)
            open(blob, 'wb').write(data)
            json.dump({'url': url, 'ts': time.time(), 'final_url': result.final_url}, open(meta, 'w', encoding='utf-8'))
            return data
        last = (f'the TLS certificate could not be verified ({result.error})' if result.error_kind == 'TLS'
                else result.error or f'HTTP {result.status}')
        if not (result.error_kind in _RETRYABLE or (result.error_kind == 'HTTP' and result.status >= 500)):
            break
        time.sleep(1.5 * (attempt + 1))
    raise FetchError(f'{url} could not be fetched after {attempts} attempt{"s" if attempts > 1 else ""}: {last}')


def pdf_text(text: str) -> str:
    """A page's text with the printed hyphen restored where the extractor marked one.

    pdfium returns U+FFFE (a noncharacter) for a hyphen that ended a printed line, and a
    soft hyphen as U+00AD; "De-industrialization" came through as "De\\ufffeindustrialization"
    and reached a candidate's syllabus that way. The table reader already restored these."""
    return text.replace('\ufffe', '-').replace('\u00ad', '-')


_LATIN_WORD = re.compile(r'[A-Za-z]{3,}')
_VOWEL = re.compile(r'[aeiouyAEIOUY]')


def unreadable_text(text: str) -> bool:
    """True for a page whose Latin letters form no words.

    Among mixed- and lower-case words of three letters or more (all-capital acronyms such as
    OBC or UR are left out), real English almost always has a vowel: across 1,245 pages of
    official notices the highest vowel-less share was 0.154. Legacy-font Hindi and garbage OCR
    layers ran from 0.22 to 0.43. A page is judged only when it has 40 such words, so a short
    page or a page in its own script (Devanagari, Telugu) is never touched.
    """
    words = [w for w in _LATIN_WORD.findall(text or '') if not w.isupper()]
    if len(words) < 40:
        return False
    return sum(1 for w in words if not _VOWEL.search(w)) / len(words) > 0.2


def load_pdf(url: str, **kw) -> Document:
    """A PDF as per-page text. A scanned PDF is reported as scanned, never as empty."""
    return pdf_document(url, fetch(url, **kw))


def pdf_document(url: str, data: bytes) -> Document:
    """A PDF already in hand, as per-page text. Parses the bytes it is given; nothing here fetches."""
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(data)
    pages = []
    for i in range(len(doc)):
        try:
            pages.append(pdf_text(doc[i].get_textpage().get_text_range()))
        except Exception:
            pages.append('')
    # A text layer can exist and still not be text: a notice typed in a legacy (non-Unicode)
    # Hindi font, or a bad OCR layer, extracts as Latin letters that form no words ("qrqr ftdr
    # sH"). Readers took such pages at face value and "read" FAQ questions out of them. A page
    # like that is read as having no text, the same as a scan.
    pages = ['' if unreadable_text(p) else p for p in pages]
    # A notice with almost no extractable text is a scan. Saying so is the honest outcome:
    # the alternative is an extractor reporting "field not found" for a document it simply
    # could not read, which reads as "the authority did not publish it".
    total = sum(len(p.strip()) for p in pages)
    is_scanned = total < max(200, 40 * len(pages))
    return Document(url=url, kind='PDF', fetched_at=_now(), raw=data, pages=pages, is_scanned=is_scanned)


_TAG = re.compile(r'<[^>]+>')
_SCRIPT = re.compile(r'<(script|style)[^>]*>.*?</\1>', re.S | re.I)


def load_html(url: str, **kw) -> Document:
    return html_document(url, fetch(url, **kw))


def html_document(url: str, data: bytes) -> Document:
    """An HTML page already in hand, as text (and its markup, for links and tables). Nothing here fetches."""
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
    names no examination". The bytes are fetched once and the PDF magic decides.
    """
    return document_from_bytes(url, fetch(url, **kw))


def document_from_bytes(url: str, data: bytes) -> Document:
    """A document from bytes already fetched (by the guarded fetch): a PDF by its magic, else HTML.
    `url` is only the citation it keeps; nothing here touches the network."""
    if data[:5] == b'%PDF-':
        return pdf_document(url, data)
    return html_document(url, data)
