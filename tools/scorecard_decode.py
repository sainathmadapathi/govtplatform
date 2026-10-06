"""Reading an uploaded scorecard (a PDF or a photo) into text, with every attacker-controlled size bounded.

`/api/results/parse` takes an unauthenticated upload. The upload's own size is capped (8 MB), but what it
*expands into* was not: a 695 KB PDF whose content stream inflates to 200 MB of text operators took
PyMuPDF's text extraction past 3 GB, pdfium's renderer past 2.7 GB, and this server's own fallback ran
`zlib.decompress` with no output cap at all; a 10 x 20000 PNG was upscaled to 1600 x 3,200,000 before OCR.
One request could take the server down.

Two layers, so that no single check has to be perfect:

1. **Pre-flight in the server process** (`preflight_pdf`, `check_image_size`) -- our own code, cheap,
   and what gives the candidate a clean 4xx: every zlib stream in a PDF is measured with a streaming,
   output-capped inflater (nothing is kept), per stream and in total, and an image's declared dimensions
   are checked from its header before a pixel is decoded.
2. **Every third-party decoder runs in a child process** (`decode_isolated`) under an operating-system
   memory cap and a wall-clock timeout: PyMuPDF, pdfium, Pillow and the OCR engine are C libraries whose
   own allocations no pre-inspection can fully bound (encrypted streams, chained or indirect filters,
   inline images, JPEG dimensions). Whatever they do, the worst case is a killed child and a 4xx; the
   Flask process never holds the decoded data.

Inside the child the same limits apply again before each expensive step (page render, upscale), so a
rejection there is a clean, named one rather than an out-of-memory kill.

Run as a module (`python -m tools.scorecard_decode`) it is that child: one JSON request on stdin, one JSON
answer on stdout. It imports nothing from app.py (which would open the database).
"""
from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import sys
import threading
import zlib

MB = 1024 * 1024

# --------------------------------------------------------------------------- limits, and why
#: Decoded size of any one zlib stream in a PDF. A scorecard's text content stream is well under 1 MB;
#: the largest legitimate Flate stream is a page image stored losslessly -- a 1920 x 1080 screenshot is
#: 6 MB, a 2480 x 3508 (A4 at 300 dpi) greyscale scan 8.7 MB, a 16-megapixel RGB image 48 MB.
INFLATE_STREAM_LIMIT = 48 * MB
#: Decoded size of all zlib streams of one PDF together: two such page images, plus fonts and text.
INFLATE_TOTAL_LIMIT = 96 * MB
#: What the text-layer fallback keeps in memory from one stream; anything larger is not a page of text.
TEXT_STREAM_LIMIT = 4 * MB
#: Places a PDF reader could start a stream that the pre-flight will examine. A scorecard has a few dozen;
#: without a cap, an 8 MB upload of repeated `stream` keywords made the pre-flight examine about a million.
MAX_PDF_STREAMS = 2000
#: Text handed to the scorecard parser. A scorecard is a page or two; this bounds the parser's regexes.
MAX_TEXT_CHARS = 1_000_000
#: Pages read for a text layer, and (unchanged) for OCR. A scorecard is on its first page or two.
MAX_TEXT_PAGES = 20
MAX_OCR_PAGES = 3
#: Pixels of a source image, from its header, before decoding: a 48-megapixel phone photo (8000 x 6000)
#: fits; decoded as RGB it is ~150 MB.
MAX_SOURCE_PIXELS = 50_000_000
#: Longest side over shortest side. A tall phone screenshot is ~2.2:1, a long scrolling one ~15:1; the
#: 10 x 20000 strip from the audit is 2000:1 and would be upscaled to 1600 x 3,200,000.
MAX_ASPECT = 20
#: Pixels of the image actually handed to OCR, after the pipeline's upscale of narrow images to 1600 px
#: wide: 1600 x 20000. Checked before the resize, so the oversized image is never allocated.
MAX_OCR_PIXELS = 32_000_000
#: OCR renders PDF pages at 200 dpi (A4: 1654 x 2339, 3.9 megapixels). A larger page is rendered at a
#: lower dpi so the bitmap stays within this; a declared page image larger than MAX_SOURCE_PIXELS is refused.
RENDER_DPI = 200
MAX_RENDER_PIXELS = 32_000_000
#: The child process. Its cap is on committed memory, which the OCR runtime's arena keeps well above the
#: working set: measured on Windows, a 1200 x 700 photo commits 1.0 GB, an A4 scan 1.3 GB, a 12 MP photo
#: 1.3 GB and a 48 MP photo (the largest MAX_SOURCE_PIXELS allows) 1.7 GB -- so 2.5 GB, about 45% above
#: the largest legitimate case. A wall-clock limit well beyond the ~5 s a legitimate OCR takes; at most two
#: children at a time, so concurrent uploads cannot multiply the cap.
CHILD_MEMORY_LIMIT = 2560 * MB
CHILD_TIMEOUT_SECONDS = 90
MAX_CONCURRENT_DECODES = 2

#: The image formats a scorecard photo or screenshot comes in. Pillow opens many more (TIFF, BMP, PSD,
#: ...); none is needed here, and each is another parser exposed to an anonymous upload.
IMAGE_FORMATS = ('PNG', 'JPEG', 'WEBP')


class UploadRejected(Exception):
    """A reason the upload will not be read. `status` is the HTTP status; `reason` the stable code the
    frontend shows; `message` the candidate-facing words."""

    def __init__(self, status: int, reason: str, message: str):
        super().__init__(reason)
        self.status, self.reason, self.message = status, reason, message


def _too_large(what: str) -> UploadRejected:
    return UploadRejected(413, 'DECOMPRESSED_TOO_LARGE',
                          f'This file expands to far more data than a scorecard holds ({what}). Upload the scorecard '
                          'PDF itself, or type your marks in.')


# --------------------------------------------------------------------------- bounded inflate
class InflateLimitExceeded(Exception):
    pass


class InflateDataError(zlib.error):
    """Invalid zlib data, raised part-way through a stream. `decoded` is what was produced before the error: work
    the pre-flight must still count, or a stream that inflates almost to the limit and then fails its checksum
    costs CPU without ever counting toward the total."""

    def __init__(self, message: str, decoded: int):
        super().__init__(message)
        self.decoded = decoded


_OUT_CHUNK = 1 * MB
_IN_CHUNK = 64 * 1024


def inflate_bounded(data, limit: int, *, keep: bool = True, start: int = 0):
    """Inflate the zlib stream that begins at `data[start:]`, producing at most `limit` bytes.

    Streams: never more than one output chunk (1 MB) beyond what it keeps is allocated, and with
    `keep=False` nothing is kept at all -- the size is only counted. Stops at the end of the zlib stream
    (whatever follows is ignored, as a PDF reader's inflater ignores it) or when the input runs out.
    Raises `InflateLimitExceeded` the moment the output would pass `limit`, and `zlib.error` when the
    data is not valid zlib. Returns (bytes or None, decoded size, reached_end_of_stream).
    """
    view = memoryview(data)[start:]
    inflater = zlib.decompressobj()
    kept: list = []
    size = 0
    pos = 0
    while not inflater.eof:
        if inflater.unconsumed_tail:
            chunk = inflater.unconsumed_tail
        elif pos < len(view):
            chunk = view[pos:pos + _IN_CHUNK]
            pos += len(chunk)
        else:
            break
        try:
            piece = inflater.decompress(chunk, min(_OUT_CHUNK, limit - size + 1))
        except zlib.error as e:
            raise InflateDataError(str(e), size) from None
        size += len(piece)
        if size > limit:
            raise InflateLimitExceeded(size)
        if keep and piece:
            kept.append(piece)
    return (b''.join(kept) if keep else None), size, inflater.eof


# --------------------------------------------------------------------------- PDF pre-flight
# Every place a PDF reader may start reading a stream: the `stream` keyword (not the end of `endstream`),
# then the end-of-line the format puts before the data.
_STREAM_START = re.compile(rb'(?<![A-Za-z])stream[ \t\f\0]*(?:\r\n|\n|\r)?')
_HEX_ESCAPE = re.compile(rb'#([0-9A-Fa-f]{2})')


def _is_zlib_header(b0: int, b1: int) -> bool:
    return (b0 & 0x0F) == 8 and (b0 >> 4) <= 7 and ((b0 << 8) | b1) % 31 == 0


def _declares_flate_first(dict_bytes: bytes) -> bool:
    """True when the stream's own dictionary names FlateDecode as its first filter (names may be #-escaped)."""
    text = _HEX_ESCAPE.sub(lambda m: bytes([int(m.group(1), 16)]), dict_bytes)
    m = re.search(rb'/Filter\s*(\[\s*)?/(FlateDecode|Fl)\b', text)
    return bool(m)


def preflight_pdf(blob: bytes) -> dict:
    """Measure every zlib stream of a PDF before any reader decodes it.

    Each stream's decoded size is counted with `inflate_bounded(keep=False)` from where a reader would
    start -- right after the `stream` keyword -- to the end of its zlib data, so a stream cannot hide its
    real length behind an early `endstream` or a wrong /Length. Raises UploadRejected:
      413 DECOMPRESSED_TOO_LARGE  one stream over INFLATE_STREAM_LIMIT, or all together over INFLATE_TOTAL_LIMIT;
      422 MALFORMED_COMPRESSED_DATA  a stream its own dictionary declares FlateDecode is not valid zlib.
    Streams that are not zlib (a JPEG image, encrypted data, other filters) are not measured here: the
    decoders that read them run in the memory-capped child.
    """
    total = 0
    streams = 0
    for examined, m in enumerate(_STREAM_START.finditer(blob)):
        if examined >= MAX_PDF_STREAMS:
            raise UploadRejected(413, 'TOO_MANY_PARTS',
                                 f'This file has far more parts than a scorecard has (over {MAX_PDF_STREAMS}). '
                                 'Upload the scorecard PDF itself, or type your marks in.')
        if total >= INFLATE_TOTAL_LIMIT:
            raise _too_large(f'its compressed parts together decode to more than {INFLATE_TOTAL_LIMIT // MB} MB')
        at = m.end()
        dict_bytes = blob[max(0, m.start() - 4096):m.start()]
        dict_bytes = dict_bytes[dict_bytes.rfind(b'obj') + 3:] if b'obj' in dict_bytes else dict_bytes
        declared = _declares_flate_first(dict_bytes)
        if at + 2 > len(blob) or not _is_zlib_header(blob[at], blob[at + 1]):
            if declared:
                raise UploadRejected(422, 'MALFORMED_COMPRESSED_DATA',
                                     'Part of this PDF that should be compressed is damaged, so it cannot be read safely. '
                                     'Download the scorecard again, or type your marks in.')
            continue
        try:
            _, size, _ = inflate_bounded(blob, min(INFLATE_STREAM_LIMIT, INFLATE_TOTAL_LIMIT - total), keep=False, start=at)
        except InflateLimitExceeded:
            if INFLATE_TOTAL_LIMIT - total < INFLATE_STREAM_LIMIT:
                raise _too_large(f'its compressed parts together decode to more than {INFLATE_TOTAL_LIMIT // MB} MB')
            raise _too_large(f'one compressed part decodes to more than {INFLATE_STREAM_LIMIT // MB} MB')
        except zlib.error as e:
            if declared:
                raise UploadRejected(422, 'MALFORMED_COMPRESSED_DATA',
                                     'Part of this PDF that should be compressed is damaged, so it cannot be read safely. '
                                     'Download the scorecard again, or type your marks in.')
            # Looked like zlib by chance (raw image bytes); not declared, so not ours to judge. What it decoded
            # before failing is still work done, so it counts toward the total.
            total += getattr(e, 'decoded', 0)
            continue
        total += size
        streams += 1
    return {'streams': streams, 'decodedBytes': total}


# --------------------------------------------------------------------------- image sizes
def check_image_size(width: int, height: int, *, upscale_to: int | None = 1600) -> None:
    """Refuse an image whose decode or OCR working copy would be unreasonable, before either happens.

    Checks the source pixel count, the aspect ratio, and the size the OCR step would upscale it to
    (narrow images are widened to `upscale_to` pixels; the target is computed here, never allocated).
    """
    if width <= 0 or height <= 0:
        raise UploadRejected(422, 'IMAGE_UNREADABLE', 'That image has no readable size. Try another photo, or type your marks in.')
    if width * height > MAX_SOURCE_PIXELS:
        raise UploadRejected(413, 'IMAGE_TOO_LARGE',
                             f'That image is {width} x {height} pixels -- larger than a scorecard photo needs to be. '
                             'Upload a smaller photo or the scorecard PDF, or type your marks in.')
    if max(width, height) > MAX_ASPECT * min(width, height):
        raise UploadRejected(413, 'IMAGE_TOO_LARGE',
                             f'That image is {width} x {height} pixels -- far longer in one direction than a scorecard. '
                             'Crop it to the scorecard, or type your marks in.')
    if upscale_to and width < upscale_to:
        target_h = int(height * (upscale_to / width))
        if upscale_to * target_h > MAX_OCR_PIXELS:
            raise UploadRejected(413, 'IMAGE_TOO_LARGE',
                                 f'That image is {width} x {height} pixels; to read it GovOS would have to enlarge it to '
                                 f'{upscale_to} x {target_h}, which is too large. Upload a wider or cropped photo, or type your marks in.')


def image_header_size(raw: bytes) -> tuple[int, int, str]:
    """Width, height and format of an image, from its header only (Pillow opens lazily; no pixels decoded)."""
    import io
    from PIL import Image
    try:
        with Image.open(io.BytesIO(raw), formats=IMAGE_FORMATS) as img:
            return img.width, img.height, img.format or ''
    except Image.DecompressionBombError as exc:
        # Pillow's own guard (above ~179 megapixels) fires while reading the header: a size refusal.
        raise UploadRejected(413, 'IMAGE_TOO_LARGE',
                             'That image declares far more pixels than a scorecard photo has. Upload a normal photo or '
                             'the scorecard PDF, or type your marks in.') from exc
    except Exception as exc:                                               # noqa: BLE001 - any header failure
        raise UploadRejected(422, 'IMAGE_UNREADABLE',
                             'That file is not a readable PNG, JPEG or WEBP image. Try another photo or the scorecard PDF, '
                             'or type your marks in.') from exc


# --------------------------------------------------------------------------- decoding (runs in the child)
_OCR_ENGINE = None


def _ocr_engine():
    global _OCR_ENGINE
    if _OCR_ENGINE is None:
        from rapidocr_onnxruntime import RapidOCR
        _OCR_ENGINE = RapidOCR()
    return _OCR_ENGINE


def _ocr_image(pil_image) -> list:
    """Text lines from one image, top to bottom, as RapidOCR read them. Sizes are checked first."""
    import numpy as np
    from PIL import ImageEnhance
    check_image_size(pil_image.width, pil_image.height)
    img = pil_image.convert('RGB')
    if img.width < 1600:
        ratio = 1600 / img.width
        img = img.resize((1600, int(img.height * ratio)))
    engine = _ocr_engine()
    try:
        result, _ = engine(np.array(ImageEnhance.Contrast(img).enhance(1.2)))
    except Exception:
        result = None
    if not result:
        result, _ = engine(np.array(img))
    if not result:
        return []
    result.sort(key=lambda item: (round(item[0][0][1] / 15), item[0][0][0]))
    return [item[1] for item in result if item[1] and item[1].strip()]


def _render_dpi(width_pt: float, height_pt: float) -> float:
    """The dpi to render a page at: RENDER_DPI, lowered so the bitmap fits MAX_RENDER_PIXELS."""
    if width_pt <= 0 or height_pt <= 0:
        raise UploadRejected(422, 'PDF_UNREADABLE', 'A page of this PDF has no size. Type your marks in instead.')
    if max(width_pt, height_pt) > MAX_ASPECT * min(width_pt, height_pt):
        raise UploadRejected(413, 'PAGE_TOO_LARGE', 'A page of this PDF is far longer in one direction than a scorecard. Type your marks in instead.')
    pixels = (width_pt / 72 * RENDER_DPI) * (height_pt / 72 * RENDER_DPI)
    return RENDER_DPI if pixels <= MAX_RENDER_PIXELS else RENDER_DPI * (MAX_RENDER_PIXELS / pixels) ** 0.5


def _pdf_text_fallback(blob: bytes) -> str:
    """The text-show strings of a PDF's streams, without a PDF library. Each stream is inflated with a cap;
    one over TEXT_STREAM_LIMIT is not a page of text and is skipped, never allocated."""
    out: list = []
    chars = 0
    for match in re.finditer(rb'stream\r?\n(.*?)\r?\nendstream', blob, re.S):
        chunk = match.group(1)
        try:
            chunk = inflate_bounded(chunk, TEXT_STREAM_LIMIT)[0]
        except InflateLimitExceeded:
            continue
        except zlib.error:
            pass
        if b'Tj' not in chunk and b'TJ' not in chunk:
            continue
        text = chunk.decode('latin-1', 'ignore')
        for segment in re.findall(r'\((?:\\.|[^()\\])*\)', text):
            out.append(re.sub(r'\\([()\\])', r'\1', segment[1:-1]))
            chars += len(segment)
        out.append('\n')
        if chars > MAX_TEXT_CHARS:
            break
    return ' '.join(out)[:MAX_TEXT_CHARS]


def pdf_text(blob: bytes) -> str:
    """Visible text of a text-based PDF: PyMuPDF over the first MAX_TEXT_PAGES pages, else the fallback."""
    try:
        import fitz
        doc = fitz.open(stream=blob, filetype='pdf')
        try:
            parts, chars = [], 0
            for index in range(min(len(doc), MAX_TEXT_PAGES)):
                text = doc[index].get_text('text')
                parts.append(text)
                chars += len(text)
                if chars > MAX_TEXT_CHARS:
                    break
        finally:
            doc.close()
        full = '\n'.join(parts).strip()[:MAX_TEXT_CHARS]
        if full:
            return full
    except UploadRejected:
        raise
    except Exception as exc:                                              # noqa: BLE001
        print(f'[PDF] PyMuPDF extraction note: {type(exc).__name__}', file=sys.stderr)
    return _pdf_text_fallback(blob)


def pdf_ocr_lines(blob: bytes, max_pages: int = MAX_OCR_PAGES) -> list:
    """Render the first pages of a scanned PDF and read them. Page size and every page image's declared
    dimensions are checked before rendering."""
    try:
        import fitz
        from PIL import Image
    except ImportError:
        fitz = None
    if fitz is not None:
        try:
            doc = fitz.open(stream=blob, filetype='pdf')
        except Exception:                                                  # noqa: BLE001
            doc = None
        if doc is not None:
            try:
                lines: list = []
                for index in range(min(len(doc), max_pages)):
                    page = doc[index]
                    for info in page.get_images(full=True):
                        w, h = int(info[2] or 0), int(info[3] or 0)
                        if w * h > MAX_SOURCE_PIXELS:
                            raise UploadRejected(413, 'IMAGE_TOO_LARGE',
                                                 f'An image in this PDF is {w} x {h} pixels -- larger than a scanned scorecard. Type your marks in instead.')
                    dpi = _render_dpi(page.rect.width, page.rect.height)
                    pix = page.get_pixmap(dpi=dpi)
                    img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
                    lines.extend(_ocr_image(img))
                    lines.append('')
                return lines
            finally:
                doc.close()
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(blob)
    lines = []
    try:
        for index in range(min(len(pdf), max_pages)):
            page = pdf[index]
            w_pt, h_pt = page.get_size()
            bitmap = page.render(scale=_render_dpi(w_pt, h_pt) / 72)
            lines.extend(_ocr_image(bitmap.to_pil()))
            lines.append('')
    finally:
        pdf.close()
    return lines


def ocr_available() -> bool:
    """Whether the OCR engine and its image libraries can be imported (checked without loading models)."""
    import importlib.util
    return all(importlib.util.find_spec(m) is not None for m in ('rapidocr_onnxruntime', 'PIL', 'numpy'))


def decode(kind: str, raw: bytes, *, ocr: bool) -> dict:
    """The child's work: PDF text layer (and OCR for a scan, when `ocr`), or OCR of an image."""
    try:
        if kind == 'pdf':
            preflight_pdf(raw)
            text = pdf_text(raw)
            if len(text.strip()) >= 30 or not ocr:
                return {'ok': True, 'method': 'TEXT_LAYER', 'text': text}
            return {'ok': True, 'method': 'OCR', 'text': '\n'.join(pdf_ocr_lines(raw))[:MAX_TEXT_CHARS]}
        import io
        from PIL import Image
        width, height, _ = image_header_size(raw)
        check_image_size(width, height)
        with Image.open(io.BytesIO(raw), formats=IMAGE_FORMATS) as img:
            return {'ok': True, 'method': 'OCR', 'text': '\n'.join(_ocr_image(img))[:MAX_TEXT_CHARS]}
    except UploadRejected as rej:
        return {'ok': False, 'status': rej.status, 'reason': rej.reason, 'message': rej.message}
    except MemoryError:
        return {'ok': False, 'status': 413, 'reason': 'TOO_COMPLEX', 'message': _TOO_COMPLEX}
    except Exception as exc:                                               # noqa: BLE001
        return {'ok': False, 'status': 200, 'reason': 'OCR_FAILED' if kind != 'pdf' else 'PDF_UNREADABLE',
                'message': f'The file could not be read ({type(exc).__name__}). Try a clearer copy, or type your marks in.'}


_TOO_COMPLEX = ('Reading this file needs far more memory or time than a scorecard ever does, so GovOS stopped. '
                'Upload the scorecard PDF itself or a plain photo of it, or type your marks in.')


# --------------------------------------------------------------------------- the isolated child
def _limit_this_process(memory: int) -> None:            # pragma: no cover - POSIX only, runs in the child
    import resource
    limit = getattr(resource, 'RLIMIT_DATA', resource.RLIMIT_AS)
    resource.setrlimit(limit, (memory, memory))
    resource.setrlimit(resource.RLIMIT_CPU, (CHILD_TIMEOUT_SECONDS, CHILD_TIMEOUT_SECONDS + 5))


class _WindowsJob:
    """A Windows job object that caps the memory of the process assigned to it and kills it when closed."""

    def __init__(self, memory: int):
        import ctypes
        from ctypes import wintypes
        self._k = k = ctypes.WinDLL('kernel32', use_last_error=True)
        k.CreateJobObjectW.restype = wintypes.HANDLE
        k.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        k.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        k.SetInformationJobObject.restype = wintypes.BOOL
        k.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        k.AssignProcessToJobObject.restype = wintypes.BOOL
        k.CloseHandle.argtypes = [wintypes.HANDLE]

        class IoCounters(ctypes.Structure):
            _fields_ = [(n, ctypes.c_ulonglong) for n in ('r', 'w', 'o', 'rb', 'wb', 'ob')]

        class Basic(ctypes.Structure):
            _fields_ = [('PerProcessUserTimeLimit', ctypes.c_int64), ('PerJobUserTimeLimit', ctypes.c_int64),
                        ('LimitFlags', wintypes.DWORD), ('MinimumWorkingSetSize', ctypes.c_size_t),
                        ('MaximumWorkingSetSize', ctypes.c_size_t), ('ActiveProcessLimit', wintypes.DWORD),
                        ('Affinity', ctypes.c_size_t), ('PriorityClass', wintypes.DWORD), ('SchedulingClass', wintypes.DWORD)]

        class Extended(ctypes.Structure):
            _fields_ = [('BasicLimitInformation', Basic), ('IoInfo', IoCounters), ('ProcessMemoryLimit', ctypes.c_size_t),
                        ('JobMemoryLimit', ctypes.c_size_t), ('PeakProcessMemoryUsed', ctypes.c_size_t),
                        ('PeakJobMemoryUsed', ctypes.c_size_t)]

        self.handle = k.CreateJobObjectW(None, None)
        if not self.handle:
            raise OSError(ctypes.get_last_error(), 'CreateJobObjectW failed')
        info = Extended()
        # PROCESS_MEMORY | KILL_ON_JOB_CLOSE | DIE_ON_UNHANDLED_EXCEPTION | ACTIVE_PROCESS (no grandchildren)
        info.BasicLimitInformation.LimitFlags = 0x100 | 0x2000 | 0x400 | 0x8
        info.BasicLimitInformation.ActiveProcessLimit = 1
        info.ProcessMemoryLimit = memory
        if not k.SetInformationJobObject(self.handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
            err = ctypes.get_last_error()
            k.CloseHandle(self.handle)
            raise OSError(err, 'SetInformationJobObject failed')

    def assign(self, proc: subprocess.Popen) -> None:
        import ctypes
        if not self._k.AssignProcessToJobObject(self.handle, int(proc._handle)):
            raise OSError(ctypes.get_last_error(), 'AssignProcessToJobObject failed')

    def close(self) -> None:
        if self.handle:
            self._k.CloseHandle(self.handle)
            self.handle = None


_SLOTS = threading.BoundedSemaphore(MAX_CONCURRENT_DECODES)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def decode_isolated(kind: str, raw: bytes, *, ocr: bool, memory: int = CHILD_MEMORY_LIMIT,
                    timeout: float = CHILD_TIMEOUT_SECONDS) -> dict:
    """Run `decode` in a child process under a memory cap and a timeout; never raises for the input's sake.

    The child is created, put under its limits, and only then sent the upload (it reads stdin before it
    imports a decoder). Out of memory, killed, timed out or any crash: a 413 TOO_COMPLEX answer. All
    slots busy for 15 s: a 503 BUSY answer.
    """
    if not _SLOTS.acquire(timeout=15):
        return {'ok': False, 'status': 503, 'reason': 'BUSY',
                'message': 'GovOS is reading other scorecards right now. Try again in a minute, or type your marks in.'}
    job = None
    proc = None
    try:
        kwargs: dict = {'stdin': subprocess.PIPE, 'stdout': subprocess.PIPE, 'stderr': subprocess.DEVNULL, 'cwd': _ROOT}
        if os.name == 'nt':
            job = _WindowsJob(memory)
            kwargs['creationflags'] = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        else:
            kwargs['preexec_fn'] = lambda: _limit_this_process(memory)
        env = {k: v for k, v in os.environ.items() if k.upper() in ('PATH', 'SYSTEMROOT', 'TEMP', 'TMP', 'HOME', 'USERPROFILE', 'LANG', 'LC_ALL')}
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        proc = subprocess.Popen([sys.executable, '-m', 'tools.scorecard_decode'], env=env, **kwargs)
        if job is not None:
            job.assign(proc)
        request = json.dumps({'kind': kind, 'ocr': bool(ocr), 'raw': base64.b64encode(raw).decode('ascii')}).encode()
        try:
            out, _ = proc.communicate(request, timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            return {'ok': False, 'status': 413, 'reason': 'TOO_COMPLEX', 'message': _TOO_COMPLEX}
        if proc.returncode != 0 or not out:
            return {'ok': False, 'status': 413, 'reason': 'TOO_COMPLEX', 'message': _TOO_COMPLEX}
        try:
            answer = json.loads(out.decode('utf-8'))
        except ValueError:
            return {'ok': False, 'status': 413, 'reason': 'TOO_COMPLEX', 'message': _TOO_COMPLEX}
        return answer if isinstance(answer, dict) else {'ok': False, 'status': 413, 'reason': 'TOO_COMPLEX', 'message': _TOO_COMPLEX}
    except OSError:
        if proc is not None and proc.poll() is None:
            proc.kill()
        return {'ok': False, 'status': 503, 'reason': 'DECODER_UNAVAILABLE',
                'message': 'GovOS could not start its file reader. Try again later, or type your marks in.'}
    finally:
        if job is not None:
            job.close()
        _SLOTS.release()


def _child_main() -> int:                                   # pragma: no cover - exercised through decode_isolated
    request = json.loads(sys.stdin.buffer.read().decode('utf-8'))
    # Decoders write to fd 1 from C; keep it for the one JSON answer and send everything else to stderr.
    answer_fd = os.dup(1)
    os.dup2(2, 1)
    answer = decode(request['kind'], base64.b64decode(request['raw']), ocr=request.get('ocr', False))
    data = memoryview(json.dumps(answer).encode('utf-8'))
    while data:
        data = data[os.write(answer_fd, data):]
    os.close(answer_fd)
    return 0


if __name__ == '__main__':
    sys.exit(_child_main())
