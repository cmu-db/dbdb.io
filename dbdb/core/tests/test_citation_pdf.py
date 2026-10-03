import io
from unittest.mock import MagicMock, patch

from django.test import TestCase
from PyPDF2 import PdfReader

from dbdb.core.models import CitationUrl, CitationUrlContent
from dbdb.core.utils.citations import fetch_url_metadata, process_citation_url

# The RDD paper from NSDI 2012 (Zaharia et al.). Its PageRank formula
# "a/N + (1 - a)Σci" sets the minus sign in TeX's CMSY10 math font, where
# the minus glyph is code 0 and the font has no /Encoding or /ToUnicode map.
# PyPDF2 extracts it as a literal NUL, which Postgres rejects in text fields.
NSDI_URL = "https://www.usenix.org/system/files/conference/nsdi12/nsdi12-final138.pdf"


def _build_pdf() -> bytes:
    """
    Build a minimal one-page PDF that mimics the NSDI paper: pdfTeX metadata
    with no /Title, body text in a normal font, and a CMSY10 minus sign (\\000).
    """
    content = (
        b"BT /F1 10 Tf 72 720 Td (Resilient Distributed Datasets) Tj ET\n"
        b"BT /F1 10 Tf 72 700 Td [(its rank to a=N+ \\050 1)] TJ "
        b"/F2 10 Tf [(\\000)] TJ /F1 10 Tf [(a\\051 ci)] TJ ET\n"
    )
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Times-Roman "
        b"/Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /POQFJL+CMSY10 >>",
        b"<< /Producer (pdfTeX-1.40.11) /Creator (TeX) "
        b"/CreationDate (D:20120314225627-07'00') /ModDate (D:20120314225627-07'00') "
        b"/Trapped /False >>",
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(b"%d 0 obj\n" % i + obj + b"\nendobj\n")
    xref = out.tell()
    out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1))
    for off in offsets:
        out.write(b"%010d 00000 n \n" % off)
    out.write(
        b"trailer\n<< /Size %d /Root 1 0 R /Info 7 0 R >>\nstartxref\n%d\n%%%%EOF\n"
        % (len(objects) + 1, xref)
    )
    return out.getvalue()


NSDI_PDF = _build_pdf()


def _mock_pdf_response(*args, **kwargs):
    resp = MagicMock()
    resp.status_code = 200
    resp.encoding = None
    resp.headers = {
        "Content-Type": "application/pdf",
        "Content-Length": str(len(NSDI_PDF)),
    }
    resp.iter_content.return_value = [NSDI_PDF]
    resp.__enter__.return_value = resp
    return resp


@patch("dbdb.core.utils.citations.requests.get", side_effect=_mock_pdf_response)
class CitationPdfNulTestCase(TestCase):

    def test_fixture_reproduces_nul(self, mock_get):
        # Guard: the fixture must still produce a NUL, otherwise the tests below prove nothing
        text = PdfReader(io.BytesIO(NSDI_PDF)).pages[0].extract_text()
        self.assertIn("\x00", text)

    def test_fetch_strips_nul(self, mock_get):
        info = fetch_url_metadata(NSDI_URL, skip_spamcheck=True)
        self.assertEqual(info["status"], CitationUrl.Status.VALID)
        self.assertIsNone(info["title"])
        self.assertIn("Resilient Distributed Datasets", info["text"])
        self.assertNotIn("\x00", info["raw"])
        self.assertNotIn("\x00", info["text"])

    def test_process_saves_content(self, mock_get):
        citation = CitationUrl.objects.create(url=NSDI_URL)
        citation, info = process_citation_url(citation, skip_spamcheck=True)

        citation.refresh_from_db()
        self.assertEqual(citation.status, CitationUrl.Status.VALID)
        self.assertEqual(citation.last_contenttype, "application/pdf")
        content = CitationUrlContent.objects.get(citation=citation)
        self.assertIn("Resilient Distributed Datasets", content.text)
        self.assertNotIn("\x00", content.raw)

    def test_process_dry_run_writes_nothing(self, mock_get):
        citation = CitationUrl.objects.create(url=NSDI_URL)
        citation, info = process_citation_url(citation, skip_spamcheck=True, dry_run=True)

        self.assertEqual(citation.status, CitationUrl.Status.VALID)
        self.assertIn("Resilient Distributed Datasets", info["text"])
        citation.refresh_from_db()
        self.assertEqual(citation.status, CitationUrl.Status.UNKNOWN)
        self.assertIsNone(citation.last_checked)
        self.assertFalse(CitationUrlContent.objects.filter(citation=citation).exists())
