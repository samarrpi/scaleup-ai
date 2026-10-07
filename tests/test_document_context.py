from io import BytesIO

from pypdf import PdfWriter

from agents.document_ingestion import attach_document_context
from agents.process_understanding import understand_process


def _pdf_bytes(page_count=2):
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=612, height=792)
    buf = BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_supporting_pdf_does_not_overwrite_primary_process_description():
    state = understand_process(
        "Process: Fermentation\nOrganism: E. coli\nProduct: Insulin\n"
        "Operations: Media preparation -> Inoculation -> Fermentation -> Harvest"
    )
    state = attach_document_context(state, _pdf_bytes(3), "paper.pdf")

    assert state.process == "Fermentation"
    assert state.organism == "E. coli"
    assert state.product == "Insulin"
    assert state.metadata["supporting_document"]["source"] == "paper.pdf"
    assert state.metadata["supporting_document"]["page_count"] == 3


def test_supporting_document_keyword_signals_are_metadata_not_process_facts():
    state = understand_process("Process: Cell culture")
    state = attach_document_context(state, _pdf_bytes(1), "paper.pdf")

    assert "keyword_signals" in state.metadata["supporting_document"]
    assert state.process == "Cell culture"
