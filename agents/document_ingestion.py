"""Page-aware scientific document intelligence for ScaleUp AI.

This layer separates *document observation* from *process interpretation*.
It preserves page boundaries, detects coarse document sections, and extracts
reviewable candidate claims. Candidate claims are deliberately not promoted
to ProcessState facts unless the source contains explicit, structured labels.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import re
from typing import BinaryIO

from pypdf import PdfReader

from agents.process_understanding import understand_process
from schemas.document import DocumentClaim, DocumentIntelligenceReport, DocumentSection
from schemas.process import Evidence, EvidenceStatus, ProcessState


@dataclass(frozen=True)
class DocumentPage:
    page: int
    text: str


@dataclass(frozen=True)
class DocumentExtraction:
    source_name: str
    pages: list[DocumentPage]
    combined_text: str
    report: DocumentIntelligenceReport


_SECTION_ALIASES = {
    "abstract": "abstract",
    "introduction": "introduction",
    "background": "introduction",
    "materials and methods": "methods",
    "materials & methods": "methods",
    "methods": "methods",
    "experimental": "methods",
    "experimental methods": "methods",
    "experimental procedure": "methods",
    "results": "results",
    "results and discussion": "results_discussion",
    "discussion": "discussion",
    "conclusion": "conclusion",
    "conclusions": "conclusion",
    "references": "references",
}

_CLAIM_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("temperature", re.compile(r"\b(?:temperature|incubated|cultured|maintained)\b.{0,100}?\b\d+(?:\.\d+)?\s*°?\s*C\b", re.I)),
    ("pH", re.compile(r"\bpH\s*(?:was|of|=|:)?\s*\d+(?:\.\d+)?\b", re.I)),
    ("agitation", re.compile(r"\b(?:agitation|agitated|shaking|stirring|stirred)\b.{0,100}?\b\d+(?:\.\d+)?\s*(?:rpm|min\-?1)\b", re.I)),
    ("feed", re.compile(r"\b(?:feed|feeding|fed[- ]batch)\b.{0,120}?\b\d+(?:\.\d+)?\s*(?:mL|L)\s*(?:/|per)\s*(?:h|hr|hour)\b", re.I)),
    ("volume", re.compile(r"\b(?:working volume|culture volume|reactor volume|volume)\b.{0,80}?\b\d+(?:\.\d+)?\s*(?:mL|L)\b", re.I)),
    ("dissolved_oxygen", re.compile(r"\b(?:dissolved oxygen|DO)\b.{0,100}?\b\d+(?:\.\d+)?\s*%?\b", re.I)),
    ("pressure", re.compile(r"\b(?:pressure|operating pressure)\b.{0,80}?\b\d+(?:\.\d+)?\s*(?:bar|kPa|atm|psi)\b", re.I)),
    ("duration", re.compile(r"\b(?:for|duration of|cultivation time|fermentation time)\b.{0,60}?\b\d+(?:\.\d+)?\s*(?:h|hr|hours|min|days)\b", re.I)),
    ("organism", re.compile(r"\b(?:E\.?\s*coli|Saccharomyces|Pichia|CHO cells?|yeast|bacteria|mammalian cells?)\b", re.I)),
    ("process", re.compile(r"\b(?:fed[- ]batch|batch culture|continuous culture|fermentation|cultivation|cell culture|bioreactor)\b", re.I)),
]


def extract_pdf_pages(data: bytes | BinaryIO, source_name: str = "uploaded_pdf") -> DocumentExtraction:
    """Extract page text and build a transparent document-intelligence report."""
    reader = PdfReader(BytesIO(data) if isinstance(data, bytes) else data)
    pages: list[DocumentPage] = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        pages.append(DocumentPage(page=page_number, text=text))

    combined_parts = [f"[PDF PAGE {item.page}]\n{item.text}".strip() for item in pages]
    combined_text = "\n\n".join(combined_parts)
    report = _build_document_report(source_name, pages)

    return DocumentExtraction(
        source_name=source_name,
        pages=pages,
        combined_text=combined_text,
        report=report,
    )


def _normalise_heading(text: str) -> str:
    text = re.sub(r"^\s*\d+(?:\.\d+)*\s*", "", text.strip())
    text = re.sub(r"\s+", " ", text).strip().strip(".:-")
    return text.lower()


def _looks_like_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 90 or stripped.endswith((".", ";")):
        return False
    normal = _normalise_heading(stripped)
    if normal in _SECTION_ALIASES:
        return True
    if re.match(r"^\d+(?:\.\d+)*\s+[A-Z][A-Za-z0-9 /&-]{2,80}$", stripped):
        return True
    words = stripped.split()
    return 1 <= len(words) <= 7 and stripped.isupper() and any(c.isalpha() for c in stripped)


def _detect_sections(pages: list[DocumentPage]) -> list[DocumentSection]:
    sections: list[DocumentSection] = []
    current_title = "Document start"
    current_type = "other"
    current_start = 1
    buffer: list[str] = []
    section_counter = 0

    def flush(end_page: int) -> None:
        nonlocal section_counter, buffer, current_title, current_type, current_start
        if not buffer and current_title == "Document start":
            return
        section_counter += 1
        preview = re.sub(r"\s+", " ", " ".join(buffer)).strip()[:320]
        sections.append(
            DocumentSection(
                id=f"sec-{section_counter:03d}",
                title=current_title,
                section_type=current_type,
                start_page=current_start,
                end_page=end_page,
                text_preview=preview,
            )
        )
        buffer = []

    for page in pages:
        lines = page.text.splitlines() if page.text else []
        for line in lines:
            if _looks_like_heading(line):
                flush(page.page)
                current_title = line.strip()
                current_type = _SECTION_ALIASES.get(_normalise_heading(line), "other")
                current_start = page.page
            else:
                buffer.append(line)
    flush(pages[-1].page if pages else 1)
    return sections


def _section_for_page(sections: list[DocumentSection], page: int) -> DocumentSection | None:
    candidates = [s for s in sections if s.start_page <= page <= s.end_page]
    return candidates[-1] if candidates else None


def _build_candidate_claims(pages: list[DocumentPage], sections: list[DocumentSection]) -> list[DocumentClaim]:
    claims: list[DocumentClaim] = []
    seen: set[tuple[str, int, str]] = set()

    for page in pages:
        if not page.text:
            continue
        section = _section_for_page(sections, page.page)
        section_name = section.title if section else None
        for raw_line in page.text.splitlines():
            line = re.sub(r"\s+", " ", raw_line).strip()
            if not line or len(line) < 8:
                continue
            for claim_type, pattern in _CLAIM_PATTERNS:
                match = pattern.search(line)
                if not match:
                    continue
                key = (claim_type, page.page, line)
                if key in seen:
                    continue
                seen.add(key)
                claim_id = f"claim-{len(claims) + 1:04d}"
                claims.append(
                    DocumentClaim(
                        id=claim_id,
                        claim_type=claim_type,
                        text=line[:500],
                        page=page.page,
                        section=section_name,
                        basis="rule_based_candidate",
                        promotion_status="candidate",
                    )
                )
                break
    return claims


def _build_document_report(source_name: str, pages: list[DocumentPage]) -> DocumentIntelligenceReport:
    sections = _detect_sections(pages)
    claims = _build_candidate_claims(pages, sections)
    warnings: list[str] = []
    pages_with_text = sum(bool(page.text) for page in pages)
    if pages_with_text == 0:
        warnings.append("No extractable text was found. OCR is required for scanned/image-only PDFs.")
    if pages_with_text < len(pages):
        warnings.append(f"{len(pages) - pages_with_text} page(s) contain no extractable text and may require OCR.")
    warnings.append("Candidate claims are reviewable observations, not automatically promoted ProcessState facts.")
    return DocumentIntelligenceReport(
        source_name=source_name,
        page_count=len(pages),
        pages_with_text=pages_with_text,
        sections=sections,
        claims=claims,
        warnings=warnings,
    )


def _document_keyword_signals(pages: list[DocumentPage]) -> dict[str, int]:
    """Return transparent keyword counts without promoting them to process facts."""
    text = "\n".join(page.text for page in pages).lower()
    terms = {
        "E. coli": r"\be\.?\s*coli\b",
        "fermentation": r"\bferment(?:ation|ed|ing)\b",
        "fed-batch": r"\bfed[- ]batch\b",
        "bioreactor": r"\bbioreactor\b",
        "cultivation": r"\bcultivat(?:ion|ed|e)\b",
        "scale-up": r"\bscale[- ]up\b",
    }
    return {label: len(re.findall(pattern, text, flags=re.IGNORECASE)) for label, pattern in terms.items() if re.search(pattern, text, flags=re.IGNORECASE)}


def _explicit_labeled_content(pages: list[DocumentPage]) -> str:
    """Return only explicitly labelled lines suitable for conservative promotion."""
    labels = re.compile(
        r"^\s*(?:Process|Process type|Bioprocess|Organism|Strain|Product|Target product|"
        r"Equipment|Reactor|Bioreactor|Fermenter|Scale|Batch scale|Pilot scale|Production scale|"
        r"Operations|Process steps|Steps|Objective|Target|Temperature|pH|Agitation|Feed rate|"
        r"Initial biomass|Initial substrate|Initial glucose|Initial product|Initial volume|"
        r"Feed substrate concentration|Feed glucose concentration|Duration)\s*[:\-]",
        re.I,
    )
    selected: list[str] = []
    for page in pages:
        for line in page.text.splitlines():
            if labels.search(line):
                selected.append(line.strip())
    return "\n".join(selected)


def attach_document_context(state: ProcessState, data: bytes, source_name: str) -> ProcessState:
    """Attach document metadata/signals without treating keyword matches as facts."""
    document = extract_pdf_pages(data, source_name=source_name)
    keyword_signals = _document_keyword_signals(document.pages)
    state.metadata = {
        **(state.metadata or {}),
        "supporting_document": {
            "source": source_name,
            "document_type": "pdf",
            "page_count": len(document.pages),
            "page_text_extracted": document.report.pages_with_text,
            "extractable_pages": [page.page for page in document.pages if page.text],
            "keyword_signals": keyword_signals,
            "role": "supporting_document",
            "document_intelligence": document.report.model_dump(mode="python"),
        },
    }
    return state


def understand_pdf(data: bytes, source_name: str = "uploaded_pdf") -> ProcessState:
    """Build a conservative ProcessState from explicit PDF labels plus a document report.

    General scientific prose is retained as candidate claims, not promoted into process
    facts. This prevents arbitrary occurrences of words such as 'E. coli' or 'scale-up'
    from becoming false process identity, parameters, or operations.
    """
    document = extract_pdf_pages(data, source_name=source_name)
    labelled_text = _explicit_labeled_content(document.pages)

    if labelled_text:
        state = understand_process(labelled_text)
        for evidence in state.evidence:
            evidence.source = source_name
            if evidence.location and evidence.location.startswith("line "):
                try:
                    line_no = int(evidence.location.split()[1])
                except (IndexError, ValueError):
                    line_no = None
                if line_no is not None:
                    labelled_lines = labelled_text.splitlines()
                    excerpt = labelled_lines[line_no - 1] if 0 < line_no <= len(labelled_lines) else evidence.excerpt
                    evidence.excerpt = excerpt
                    page = _find_page_for_excerpt(document.pages, excerpt)
                    evidence.page = page
                    evidence.location = f"PDF page {page}" if page is not None else evidence.location
    else:
        state = ProcessState()

    report_dict = document.report.model_dump(mode="python")
    state.metadata = {
        **(state.metadata or {}),
        "document_source": source_name,
        "document_type": "pdf",
        "page_count": len(document.pages),
        "page_text_extracted": document.report.pages_with_text,
        "document_ingestion": "page_aware_text_and_rule_based_document_intelligence",
        "document_intelligence": report_dict,
    }

    if document.report.pages_with_text == 0:
        state.missing_information.append("The uploaded PDF contains no extractable text. OCR is required for scanned-image PDFs.")
    else:
        state.missing_information.append("PDF-derived candidate claims require semantic review before they are promoted to ProcessState facts.")

    if not state.process:
        state.missing_information.append("Process identity was not explicitly labelled in the PDF extraction and has not been inferred from general prose.")
    if not state.organism:
        state.missing_information.append("Organism/material identity was not explicitly labelled in the PDF extraction and has not been inferred from keyword occurrences.")
    if not state.product:
        state.missing_information.append("Product identity was not explicitly labelled in the PDF extraction and has not been inferred from general prose.")

    # Deduplicate missing information while preserving order.
    state.missing_information = list(dict.fromkeys(state.missing_information))
    return state


def _find_page_for_excerpt(pages: list[DocumentPage], excerpt: str | None) -> int | None:
    if not excerpt:
        return None
    needle = excerpt.strip().lower()
    for page in pages:
        if needle and needle in page.text.lower():
            return page.page
    return None
