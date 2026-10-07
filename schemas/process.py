from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class Provenance(str, Enum):
    """Indicates where a piece of information came from."""

    USER_PROVIDED = "user_provided"
    MODEL_INFERRED = "model_inferred"
    CALCULATED = "calculated"
    ASSUMED = "assumed"
    UNKNOWN = "unknown"


class EvidenceStatus(str, Enum):
    """Validation state of a source-backed evidence record."""

    UNVERIFIED = "unverified"
    VALIDATED = "validated"
    REJECTED = "rejected"
    DERIVED = "derived"


class Evidence(BaseModel):
    """Traceability record connecting a claim to its source location."""

    id: str
    source: str
    page: Optional[int] = None
    location: Optional[str] = None
    excerpt: Optional[str] = None
    status: EvidenceStatus = EvidenceStatus.UNVERIFIED
    limitation: Optional[str] = None


class ProcessNode(BaseModel):
    """Typed process entity used by the process graph."""

    id: str
    kind: str
    name: str
    description: Optional[str] = None
    provenance: Provenance = Provenance.UNKNOWN
    evidence_ids: list[str] = Field(default_factory=list)


class ProcessRelation(BaseModel):
    """Directed typed relation between two process graph nodes."""

    source_node_id: str
    relation: str
    target_node_id: str
    provenance: Provenance = Provenance.UNKNOWN
    evidence_ids: list[str] = Field(default_factory=list)


class UncertaintyFinding(BaseModel):
    """Structured missing, ambiguous, or contradictory finding."""

    id: str
    category: str
    message: str
    subject: Optional[str] = None
    evidence_ids: list[str] = Field(default_factory=list)


class Parameter(BaseModel):
    """A process variable that can be observed or potentially manipulated."""

    name: str
    value: Optional[Any] = None
    unit: Optional[str] = None
    parameter_type: Optional[str] = None
    range: Optional[str] = None
    controllable: Optional[bool] = None
    measurable: Optional[bool] = None
    description: Optional[str] = None
    source: Provenance = Provenance.UNKNOWN
    evidence_ids: list[str] = Field(default_factory=list)


class Objective(BaseModel):
    """A desired process outcome."""

    name: str
    direction: Optional[str] = None
    target: Optional[Any] = None
    unit: Optional[str] = None
    description: Optional[str] = None
    source: Provenance = Provenance.UNKNOWN
    evidence_ids: list[str] = Field(default_factory=list)


class Constraint(BaseModel):
    """A restriction that the process or optimization must respect."""

    name: str
    condition: Optional[str] = None
    value: Optional[Any] = None
    unit: Optional[str] = None
    description: Optional[str] = None
    source: Provenance = Provenance.UNKNOWN
    evidence_ids: list[str] = Field(default_factory=list)


class Experiment(BaseModel):
    """A historical or planned experiment."""

    inputs: dict[str, Any] = Field(default_factory=dict)
    conditions: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[str] = None
    source: Optional[str] = None
    equipment: Optional[str] = None
    scale: Optional[str] = None


class ModelResult(BaseModel):
    """Output from a scientific or computational model."""

    predictions: dict[str, Any] = Field(default_factory=dict)
    uncertainty: dict[str, Any] = Field(default_factory=dict)
    important_parameters: list[str] = Field(default_factory=list)
    sensitivity: dict[str, Any] = Field(default_factory=dict)
    model_metadata: dict[str, Any] = Field(default_factory=dict)


class Recommendation(BaseModel):
    """A future recommendation produced by an optimization or planning layer."""

    recommended_action: str
    reason: Optional[str] = None
    expected_outcome: Optional[str] = None
    uncertainty: Optional[str] = None
    evidence: list[str] = Field(default_factory=list)


class ProcessState(BaseModel):
    """
    Canonical structured representation of a biological or chemical process.

    The representation intentionally separates process facts, graph structure,
    source evidence, and uncertainty so downstream scientific models can use
    the same process knowledge without losing traceability.
    """

    process: Optional[str] = None
    organism: Optional[str] = None
    product: Optional[str] = None
    equipment: Optional[str] = None
    scale: Optional[str] = None

    parameters: list[Parameter] = Field(default_factory=list)
    objectives: list[Objective] = Field(default_factory=list)
    constraints: list[Constraint] = Field(default_factory=list)

    experiments: list[Experiment] = Field(default_factory=list)
    models: list[ModelResult] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)

    # Process topology and traceability are first-class state, not UI-only data.
    process_nodes: list[ProcessNode] = Field(default_factory=list)
    process_relations: list[ProcessRelation] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    field_evidence: dict[str, list[str]] = Field(default_factory=dict)
    uncertainty_findings: list[UncertaintyFinding] = Field(default_factory=list)

    missing_information: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)

    metadata: dict[str, Any] = Field(default_factory=dict)
