from io import BytesIO

from pypdf import PdfWriter

from agents.document_ingestion import extract_pdf_pages, understand_pdf


def _blank_pdf_bytes(page_count: int = 2) -> bytes:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=612, height=792)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_extract_pdf_preserves_page_count_and_boundaries():
    result = extract_pdf_pages(_blank_pdf_bytes(3))

    assert len(result.pages) == 3
    assert [page.page for page in result.pages] == [1, 2, 3]
    assert "[PDF PAGE 1]" in result.combined_text
    assert "[PDF PAGE 3]" in result.combined_text


def test_understand_pdf_records_document_metadata():
    state = understand_pdf(_blank_pdf_bytes(2), source_name="paper.pdf")

    assert state.metadata["document_type"] == "pdf"
    assert state.metadata["document_source"] == "paper.pdf"
    assert state.metadata["page_count"] == 2
    assert any("OCR" in item for item in state.missing_information)


def test_understand_pdf_does_not_invent_content_for_blank_pages():
    state = understand_pdf(_blank_pdf_bytes(1), source_name="blank.pdf")

    assert state.process is None
    assert state.process_nodes == []
    assert state.parameters == []
