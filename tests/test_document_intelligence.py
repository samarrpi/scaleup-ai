from io import BytesIO

from pypdf import PdfWriter

from agents.document_ingestion import extract_pdf_pages, understand_pdf


def _pdf_with_text(texts: list[str]) -> bytes:
    # pypdf cannot create text content directly; use blank pages for structural tests.
    writer = PdfWriter()
    for _ in texts:
        writer.add_blank_page(width=612, height=792)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_document_report_is_present_and_conservative_for_blank_pdf():
    state = understand_pdf(_pdf_with_text(["", ""]), source_name="paper.pdf")
    report = state.metadata["document_intelligence"]
    assert report["page_count"] == 2
    assert report["claims"] == []
    assert any("OCR" in warning for warning in report["warnings"])


def test_document_report_never_promotes_keyword_signals_to_process_identity():
    state = understand_pdf(_pdf_with_text(["E. coli fermentation"]), source_name="paper.pdf")
    assert state.process is None
    assert state.organism is None
    assert state.product is None
