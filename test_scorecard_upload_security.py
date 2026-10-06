"""`/api/results/parse` takes an anonymous upload; nothing in it may make the server allocate without bound.

Every payload here is a few kilobytes and is generated in the test. They reproduce what the audit found:
a PDF whose compressed streams expand far past the upload size (zlib reaches ~1000:1), and an image whose
OCR working copy would be enormous (a 10 x 20000 strip upscaled to 1600 x 3,200,000). Each must be refused
with a clean 4xx -- and the server must go on reading a normal scorecard afterwards.

Run: python -m pytest test_scorecard_upload_security.py -q
"""
from __future__ import annotations

import base64
import io
import os
import struct
import tempfile
import tracemalloc
import unittest
import zlib

import app as govos
from tools import scorecard_decode as sd

MB = 1024 * 1024
LINES = ['Staff Selection Commission', 'Combined Graduate Level Examination 2025', 'Roll Number : 2201234567',
         'Category : OBC', 'Tier-I Marks Obtained : 145.50', 'Result : Qualified']


# --------------------------------------------------------------------------- payload builders
def zeros_bomb(decoded: int) -> bytes:
    """A zlib stream of `decoded` zero bytes, built a megabyte at a time (never held whole)."""
    co = zlib.compressobj(9)
    parts = [co.compress(b'\0' * min(MB, decoded - i)) for i in range(0, decoded, MB)]
    return b''.join(parts) + co.flush()


def pdf(*streams: bytes, filters: tuple = None, page: bytes = b'[0 0 612 792]', resources: bytes = b'<< >>') -> bytes:
    """A minimal PDF whose page draws its first stream; every stream is declared FlateDecode unless told."""
    filters = filters or tuple(b'/FlateDecode' for _ in streams)
    objs = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
            b'<< /Type /Page /Parent 2 0 R /MediaBox ' + page + b' /Contents 4 0 R /Resources ' + resources + b' >>']
    for data, flt in zip(streams, filters):
        objs.append(b'<< /Length %d /Filter %s >>\nstream\n' % (len(data), flt) + data + b'\nendstream')
    out, offs = b'%PDF-1.4\n', []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += b'%d 0 obj\n' % i + o + b'\nendobj\n'
    x = len(out)
    out += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objs) + 1) + b''.join(b'%010d 00000 n \n' % o for o in offs)
    return out + b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objs) + 1, x)


FONT = b'<< /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >>'


def scorecard_pdf() -> bytes:
    """A text scorecard: one small Flate content stream."""
    content = b'BT /F1 12 Tf ' + b' '.join(b'1 0 0 1 72 %d Tm (%s) Tj' % (700 - 20 * i, l.encode()) for i, l in enumerate(LINES)) + b' ET'
    return pdf(zlib.compress(content), resources=FONT)


def png_header_only(width: int, height: int) -> bytes:
    """A PNG whose header declares width x height, with almost no pixel data: what an attacker sends."""
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 0, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(b'\0' * 16)) + chunk(b'IEND', b''))


def real_png(width: int, height: int, text: bool = False) -> bytes:
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new('RGB', (width, height), 'white')
    if text:
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default(size=40)
        for i, line in enumerate(LINES):
            draw.text((40, 40 + 100 * i), line, fill='black', font=font)
    buf = io.BytesIO()
    img.save(buf, 'PNG')
    return buf.getvalue()


def scanned_pdf() -> bytes:
    import fitz
    doc = fitz.open()
    doc.new_page().insert_image(fitz.Rect(0, 0, 595, 842), stream=real_png(1200, 700, text=True))
    return doc.tobytes(deflate=True)


def ocr_ready() -> bool:
    return sd.ocr_available()


class _Endpoint(unittest.TestCase):
    """Each test posts to the real route on its own temporary database; govos.db is never touched."""

    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        self._db = govos.DB_FILE
        govos.DB_FILE = self.path
        govos.init_database()
        govos._link_limiter().reset()          # each test starts inside the route's per-minute allowance
        self.client = govos.app.test_client()

    def tearDown(self):
        govos.DB_FILE = self._db
        try:
            os.remove(self.path)
        except OSError:
            pass

    def post(self, raw: bytes, filename: str = 'scorecard.pdf'):
        r = self.client.post('/api/results/parse', json={'filename': filename, 'examId': 'exam-ssc-cgl-2026',
                                                          'contentBase64': base64.b64encode(raw).decode()})
        return r.status_code, r.get_json()

    def assertReadsScorecard(self, raw: bytes, filename: str = 'scorecard.pdf', method: str = 'TEXT_LAYER'):
        status, body = self.post(raw, filename)
        self.assertEqual(status, 200, body)
        self.assertTrue(body['ok'], body)
        self.assertEqual(body['method'], method)
        self.assertEqual(body['fields'].get('marks'), 145.5, body['fields'])
        self.assertEqual(body['fields'].get('category'), 'OBC')

    def assertRefused(self, raw: bytes, status: int, reason: str, filename: str = 'scorecard.pdf'):
        got, body = self.post(raw, filename)
        self.assertEqual((got, body.get('reason')), (status, reason), body)
        self.assertFalse(body['ok'])
        self.assertTrue(body.get('message'))
        return body


# --------------------------------------------------------------------------- the bounded inflater itself
class BoundedInflateTests(unittest.TestCase):

    def test_a_small_stream_inflates_exactly(self):
        data = b'Marks Obtained 145.50 ' * 100
        out, size, eof = sd.inflate_bounded(zlib.compress(data), 1 * MB)
        self.assertEqual((out, size, eof), (data, len(data), True))

    def test_counting_keeps_nothing(self):
        out, size, eof = sd.inflate_bounded(zeros_bomb(3 * MB), 4 * MB, keep=False)
        self.assertEqual((out, size, eof), (None, 3 * MB, True))

    def test_a_1kb_bomb_is_stopped_at_the_limit_without_allocating_its_expansion(self):
        bomb = zeros_bomb(1 * MB)            # deflate tops out near 1032:1, so ~1 KB of zlib becomes 1 MB
        self.assertLess(len(bomb), 1100)
        with self.assertRaises(sd.InflateLimitExceeded):
            sd.inflate_bounded(bomb, 256 * 1024)

    def test_a_large_bomb_never_allocates_past_limit_plus_one_chunk(self):
        bomb = zeros_bomb(200 * MB)          # ~200 KB of input
        tracemalloc.start()
        try:
            with self.assertRaises(sd.InflateLimitExceeded):
                sd.inflate_bounded(bomb, 4 * MB)
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
        self.assertLess(peak, 4 * MB + 3 * MB, f'peak {peak} bytes')

    def test_a_stream_that_fails_part_way_reports_what_it_decoded(self):
        broken = bytearray(zeros_bomb(3 * MB))
        broken[-4:] = b'\0\0\0\0'                # valid deflate data, wrong checksum: fails at the very end
        with self.assertRaises(zlib.error) as caught:
            sd.inflate_bounded(bytes(broken), 8 * MB, keep=False)
        self.assertIsInstance(caught.exception, sd.InflateDataError)
        self.assertGreaterEqual(caught.exception.decoded, 2 * MB)

    def test_malformed_zlib_raises_zlib_error(self):
        with self.assertRaises(zlib.error):
            sd.inflate_bounded(b'\x78\x9c' + b'\xff' * 64, MB)

    def test_it_stops_at_the_end_of_the_stream_and_ignores_what_follows(self):
        out, size, eof = sd.inflate_bounded(zlib.compress(b'abc') + b'\nendstream\n' + zeros_bomb(10 * MB), 1024)
        self.assertEqual((out, size, eof), (b'abc', 3, True))


# --------------------------------------------------------------------------- decompression through the route
class DecompressionTests(_Endpoint):

    def test_1_a_small_valid_compressed_scorecard_parses(self):
        self.assertReadsScorecard(scorecard_pdf())

    def test_2_a_malformed_zlib_stream_is_a_clean_422(self):
        self.assertRefused(pdf(b'\x78\x9c' + b'\xde\xad\xbe\xef' * 64), 422, 'MALFORMED_COMPRESSED_DATA')

    def test_2b_a_declared_flate_stream_that_is_not_zlib_at_all_is_a_clean_422(self):
        self.assertRefused(pdf(b'this is not compressed data at all'), 422, 'MALFORMED_COMPRESSED_DATA')

    def test_3_a_1kb_bomb_is_refused_once_it_passes_the_limit(self):
        bomb = pdf(zeros_bomb(1 * MB))
        self.assertLess(len(bomb), 1500)
        original = sd.INFLATE_STREAM_LIMIT
        sd.INFLATE_STREAM_LIMIT = 512 * 1024      # the same code path, at a limit a 1 KB bomb can exceed
        try:
            self.assertRefused(bomb, 413, 'DECOMPRESSED_TOO_LARGE')
        finally:
            sd.INFLATE_STREAM_LIMIT = original

    def test_4_a_stream_past_the_production_limit_is_a_clean_413(self):
        bomb = pdf(zeros_bomb(sd.INFLATE_STREAM_LIMIT + MB))
        self.assertLess(len(bomb), 64 * 1024, 'the upload is tiny; only its expansion is large')
        body = self.assertRefused(bomb, 413, 'DECOMPRESSED_TOO_LARGE')
        self.assertIn('one compressed part', body['message'])

    def test_5_streams_under_the_per_stream_limit_cannot_exceed_the_total_together(self):
        each = 40 * MB                            # under INFLATE_STREAM_LIMIT (48 MB) one by one
        self.assertLess(each, sd.INFLATE_STREAM_LIMIT)
        streams = [zeros_bomb(each) for _ in range(3)]    # 120 MB together, over INFLATE_TOTAL_LIMIT (96 MB)
        body = self.assertRefused(pdf(*streams), 413, 'DECOMPRESSED_TOO_LARGE')
        self.assertIn('together', body['message'])

    def test_5c_undeclared_streams_that_fail_their_checksum_still_count_toward_the_total(self):
        # The audit's attack: streams whose dictionaries declare no filter, each inflating to 40 MB and then failing
        # its checksum. They used to be skipped without counting what they decoded, so ~170 of them in an 8 MB
        # upload burned seconds of CPU per request and were never refused.
        broken = bytearray(zeros_bomb(40 * MB))
        broken[-4:] = b'\0\0\0\0'
        part = b'1 0 obj\n<< /Length 5 >>\nstream\n' + bytes(broken) + b'\nendstream\nendobj\n'
        body = self.assertRefused(b'%PDF-1.4\n' + part * 4, 413, 'DECOMPRESSED_TOO_LARGE')
        self.assertIn('together', body['message'])

    def test_5d_a_flood_of_stream_keywords_is_refused_quickly(self):
        import time
        flood = b'%PDF-1.4\n' + b'stream\n' * 600_000          # ~4 MB, far more places a reader could start than any scorecard
        started = time.perf_counter()
        self.assertRefused(flood, 413, 'TOO_MANY_PARTS')
        self.assertLess(time.perf_counter() - started, 3.0)

    def test_5e_a_client_over_its_upload_rate_is_answered_429(self):
        for _ in range(govos.LINK_RATE['scorecard']):
            self.assertNotEqual(self.post(scorecard_pdf())[0], 429)
        status, body = self.post(scorecard_pdf())
        self.assertEqual((status, body.get('error')), (429, 'RATE_LIMITED'))

    def test_5b_a_stream_cannot_hide_its_length_behind_an_early_endstream(self):
        # A stored deflate block holding the bytes "endstream", then 60 MB of zeros, in one valid zlib stream:
        # a reader that trusts /Length or the first `endstream` would see 20 bytes; a decoder sees 60 MB.
        decoy = b'\nendstream\nendobj\n'
        stored = b'\x00' + struct.pack('<HH', len(decoy), 0xffff ^ len(decoy)) + decoy
        co = zlib.compressobj(9, zlib.DEFLATED, -15)
        rest = b''.join(co.compress(b'\0' * MB) for _ in range(60)) + co.flush()
        adler = zlib.adler32(b'\0' * MB * 60, zlib.adler32(decoy))
        stream = b'\x78\x9c' + stored + rest + struct.pack('>I', adler & 0xffffffff)
        self.assertEqual(len(zlib.decompress(stream[:2] + stored + rest + stream[-4:])), 60 * MB + len(decoy))
        doc = pdf(stream)
        self.assertIn(b'stream\n\x78\x9c\x00', doc)
        self.assertRefused(doc, 413, 'DECOMPRESSED_TOO_LARGE')

    def test_6_the_server_keeps_reading_scorecards_after_refusing_bombs(self):
        self.assertRefused(pdf(zeros_bomb(sd.INFLATE_STREAM_LIMIT + MB)), 413, 'DECOMPRESSED_TOO_LARGE')
        self.assertRefused(pdf(b'\x78\x9c' + b'\x00\xff' * 32), 422, 'MALFORMED_COMPRESSED_DATA')
        self.assertReadsScorecard(scorecard_pdf())
        status, body = self.client.get('/api/sqlite/status').status_code, None
        self.assertEqual(status, 200)

    def test_7_valid_scorecards_still_parse(self):
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        for i, line in enumerate(LINES):
            page.insert_text((72, 90 + 24 * i), line, fontsize=13)
        self.assertReadsScorecard(doc.tobytes(deflate=True))     # PyMuPDF-written, Flate fonts and content
        self.assertReadsScorecard(scorecard_pdf())               # hand-built, one Flate content stream
        if ocr_ready():
            self.assertReadsScorecard(scanned_pdf(), 'scan.pdf', method='OCR')


# --------------------------------------------------------------------------- images and OCR through the route
@unittest.skipUnless(ocr_ready(), 'the OCR libraries are not installed; images are refused before any size check')
class ImageTests(_Endpoint):

    def test_8_a_normal_scorecard_photo_parses(self):
        self.assertReadsScorecard(real_png(1200, 700, text=True), 'scorecard.png', method='OCR')

    def test_9_the_10x20000_strip_is_refused_before_any_decode(self):
        self.assertRefused(real_png(10, 20000), 413, 'IMAGE_TOO_LARGE', 'strip.png')
        self.assertRefused(png_header_only(10, 20000), 413, 'IMAGE_TOO_LARGE', 'strip.png')

    def test_10_an_image_with_too_many_pixels_is_refused_from_its_header(self):
        self.assertRefused(png_header_only(9000, 6000), 413, 'IMAGE_TOO_LARGE', 'huge.png')       # 54 MP
        self.assertRefused(png_header_only(60000, 60000), 413, 'IMAGE_TOO_LARGE', 'bomb.png')     # 3.6 GP declared

    def test_11_an_image_too_large_only_after_the_ocr_upscale_is_refused(self):
        # 120 x 2300: 0.28 MP, aspect 19:1 -- fine as it is, but widened to 1600 px it would be 1600 x 30666.
        sd.check_image_size(120, 2300, upscale_to=None)
        body = self.assertRefused(real_png(120, 2300), 413, 'IMAGE_TOO_LARGE', 'narrow.png')
        self.assertIn('enlarge', body['message'])

    def test_12_a_malformed_image_is_a_clean_422(self):
        self.assertRefused(b'\x89PNG\r\n\x1a\n' + b'garbage' * 50, 422, 'IMAGE_UNREADABLE', 'broken.png')
        self.assertRefused(b'\xff\xd8\xff' + b'\x00' * 300, 422, 'IMAGE_UNREADABLE', 'broken.jpg')

    def test_12b_formats_a_scorecard_never_comes_in_are_not_parsed(self):
        from PIL import Image
        buf = io.BytesIO()
        Image.new('RGB', (100, 100), 'white').save(buf, 'TIFF')
        self.assertRefused(buf.getvalue(), 422, 'IMAGE_UNREADABLE', 'scan.png')

    def test_13_the_server_keeps_reading_photos_after_refusing_images(self):
        self.assertRefused(png_header_only(10, 20000), 413, 'IMAGE_TOO_LARGE', 'strip.png')
        self.assertRefused(png_header_only(60000, 60000), 413, 'IMAGE_TOO_LARGE', 'bomb.png')
        self.assertRefused(b'\x89PNG\r\n\x1a\nxx', 422, 'IMAGE_UNREADABLE', 'broken.png')
        self.assertReadsScorecard(real_png(1200, 700, text=True), 'scorecard.png', method='OCR')

    def test_a_scanned_pdf_declaring_a_huge_page_image_is_refused_before_rendering(self):
        image = b'<< /Type /XObject /Subtype /Image /Width 30000 /Height 30000 /ColorSpace /DeviceGray /BitsPerComponent 8 /Length 4 /Filter /DCTDecode >>\nstream\n\xff\xd8\xff\xd9\nendstream'
        draw = zlib.compress(b'q 612 0 0 792 0 0 cm /Im1 Do Q')
        doc = pdf(draw, resources=b'<< /XObject << /Im1 5 0 R >> >>').replace(b'xref', b'5 0 obj\n' + image + b'\nendobj\nxref', 1)
        status, body = self.post(doc, 'scan.pdf')
        self.assertEqual((status, body.get('reason')), (413, 'IMAGE_TOO_LARGE'), body)

    def test_a_scanned_pdf_with_an_absurd_page_shape_is_refused_before_rendering(self):
        self.assertRefused(pdf(zlib.compress(b'% nothing'), page=b'[0 0 14400 20]'), 413, 'PAGE_TOO_LARGE', 'scan.pdf')

    def test_a_large_page_is_rendered_at_a_lower_dpi_not_refused(self):
        self.assertEqual(sd._render_dpi(595, 842), sd.RENDER_DPI)                         # A4 at 200 dpi
        dpi = sd._render_dpi(14400, 14400)                                                 # 200 x 200 inches
        self.assertLess((14400 / 72 * dpi) ** 2, sd.MAX_RENDER_PIXELS * 1.001)


# --------------------------------------------------------------------------- the isolation layer
class IsolationTests(unittest.TestCase):

    def test_a_bomb_the_preflight_cannot_measure_is_stopped_by_the_child_memory_cap(self):
        # Flate hidden behind ASCIIHex: the bytes after `stream` are hex, so no pre-flight sees the 64 MB of
        # text operators inside; PyMuPDF would expand them past 1 GB. The child is capped and killed.
        unit = b'BT /F1 12 Tf 10 10 Td (AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA) Tj ET\n'
        hidden = zlib.compress(unit * (64 * MB // len(unit)), 9).hex().encode() + b'>'
        doc = pdf(hidden, filters=(b'[/ASCIIHexDecode /FlateDecode]',), resources=FONT)
        self.assertEqual(sd.preflight_pdf(doc)['decodedBytes'], 0)
        answer = sd.decode_isolated('pdf', doc, ocr=False, memory=768 * MB)
        self.assertEqual((answer.get('ok'), answer.get('status'), answer.get('reason')), (False, 413, 'TOO_COMPLEX'), answer)

    def test_a_decode_that_runs_too_long_is_stopped(self):
        answer = sd.decode_isolated('pdf', scorecard_pdf(), ocr=False, timeout=0.01)
        self.assertEqual(answer.get('reason'), 'TOO_COMPLEX')

    def test_the_child_reads_a_scorecard_and_the_parent_holds_no_decoder_state(self):
        answer = sd.decode_isolated('pdf', scorecard_pdf(), ocr=False)
        self.assertTrue(answer['ok'], answer)
        self.assertIn('145.50', answer['text'])
        self.assertIsNone(sd._OCR_ENGINE, 'the OCR models load in the child, never in the server')


if __name__ == '__main__':
    unittest.main()
