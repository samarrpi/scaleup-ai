from typing import Optional

from pydantic import BaseModel, Field


class DocumentSection(BaseModel):
    """Page-aware structural section detected in a source document."""

    id: str
    title: str
    section_type: str = "other"
    start_page: int
    end_page: int
    text_preview: str = ""


class DocumentClaim(BaseModel):
    """Candidate scientific claim retained for review, not automatically promoted."""

    id: str
    claim_type: str
    text: str
    page: Optional[int] = None
    section: Optional[str] = None
    basis: str = "rule_based_candidate"
    promotion_status: str = "candidate"
    evidence_id: Optional[str] = None


class DocumentIntelligenceReport(BaseModel):
    """Transparent document-structure report used by the UI and downstream review."""

    source_name: str
    page_count: int
    pages_with_text: int
    sections: list[DocumentSection] = Field(default_factory=list)
    claims: list[DocumentClaim] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    method: str = "page_aware_text_and_rule_based_candidate_extraction"
