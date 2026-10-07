"""Conservatively translate process descriptions into ``ProcessState`` objects.

This module is an interpretation boundary, not a scientific model. It extracts
only information supported by the supplied description, preserves qualitative
wording, and leaves unknown values unset. Important omissions, ambiguity, and
contradictions are recorded explicitly rather than inferred or resolved.

The module also provides a conservative bridge from natural-language scientific
parameters to the canonical parameter names expected by scientific models.
"""

from __future__ import annotations

import re
from typing import Any, Protocol, Type

from pydantic import BaseModel, Field, ValidationError

from schemas.process import (
    Constraint,
    Evidence,
    EvidenceStatus,
    Objective,
    Parameter,
    ProcessNode,
    ProcessRelation,
    ProcessState,
    Provenance,
    UncertaintyFinding,
)


class StructuredExtraction(BaseModel):
    """Intermediate contract shared by structured LLM and local extraction.

    Values in this model are not canonical scientific facts. They are the
    conservative extraction result that is subsequently normalized into a
    ``ProcessState``.
    """

    process: str | None = None
    organism: str | None = None
    product: str | None = None
    equipment: str | None = None
    scale: str | None = None

    parameters: list[dict[str, Any]] = Field(
        default_factory=list
    )

    objectives: list[dict[str, Any]] = Field(
        default_factory=list
    )

    constraints: list[dict[str, Any]] = Field(
        default_factory=list
    )

    operations: list[str] = Field(
        default_factory=list
    )

    missing_information: list[str] = Field(
        default_factory=list
    )

    ambiguities: list[str] = Field(
        default_factory=list
    )

    contradictions: list[str] = Field(
        default_factory=list
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )


class StructuredLLMClient(Protocol):
    """Minimal contract for a conservative schema-driven LLM adapter.

    Implementations must extract only input-supported information, preserve
    qualitative wording, and report gaps, ambiguity, and contradictions rather
    than inventing values or resolving conflicts.
    """

    def structured_extract(
        self,
        user_description: str,
        schema: Type[BaseModel],
    ) -> dict[str, Any] | BaseModel:
        ...


# ============================================================================
# SCIENTIFIC PARAMETER VOCABULARY
# ============================================================================

SCIENTIFIC_PARAMETER_ALIASES: dict[str, list[str]] = {
    "initial_biomass": [
        "initial biomass",
        "starting biomass",
        "initial biomass concentration",
        "starting biomass concentration",
        "initial cell concentration",
        "starting cell concentration",
    ],
    "initial_substrate": [
        "initial substrate",
        "starting substrate",
        "initial substrate concentration",
        "starting substrate concentration",
        "initial glucose",
        "starting glucose",
        "initial glucose concentration",
        "starting glucose concentration",
    ],
    "initial_product": [
        "initial product",
        "starting product",
        "initial product concentration",
        "starting product concentration",
    ],
    "initial_volume": [
        "initial volume",
        "starting volume",
        "working volume",
        "reactor volume",
        "initial reactor volume",
        "starting reactor volume",
    ],
    "mu_max": [
        "mu_max",
        "mu max",
        "maximum specific growth rate",
        "maximum specific growth",
    ],
    "Ks": [
        "Ks",
        "K_s",
        "half saturation constant",
        "half-saturation constant",
        "monod constant",
    ],
    "Yxs": [
        "Yxs",
        "Y_xs",
        "biomass yield on substrate",
        "biomass yield from substrate",
    ],
    "Ypx": [
        "Ypx",
        "Y_px",
        "product yield on biomass",
        "product yield from biomass",
    ],
    "feed_rate": [
        "feed rate",
        "feeding rate",
        "substrate feed rate",
        "glucose feed rate",
    ],
    "feed_substrate": [
        "feed substrate concentration",
        "feed glucose concentration",
        "substrate concentration in feed",
        "glucose concentration in feed",
    ],
    "duration": [
        "duration",
        "process duration",
        "fermentation duration",
        "fermentation time",
        "cultivation time",
        "run time",
        "process time",
    ],
}


SUPPORTED_SCIENTIFIC_UNITS = (
    "g/L",
    "g/g",
    "L/h",
    "L",
    "h",
    "1/h",
    "%",
    "rpm",
)


# ============================================================================
# PUBLIC API
# ============================================================================


def understand_process(
    user_description: str,
    llm_client: StructuredLLMClient | None = None,
) -> ProcessState:
    """Return a validated ProcessState for a natural-language description.

    The function prefers schema-based structured extraction.

    Both extraction paths record only information supported by the input.
    They do not invent scientific values, retain qualitative wording, leave
    unknown values unset, and record important gaps, ambiguity, and
    contradictions without resolving them.
    """

    description = (
        user_description or ""
    ).strip()

    if not description:
        return ProcessState(
            missing_information=[
                "No process description was provided."
            ],
            metadata={
                "input_status": "empty"
            },
        )

    try:
        extraction = _get_structured_extraction(
            description,
            llm_client,
        )

        return _materialize_process_state(
            extraction,
            description,
        )

    except Exception:
        return ProcessState(
            missing_information=[
                (
                    "The process description could not be "
                    "parsed into a validated ProcessState."
                )
            ],
            metadata={
                "parse_status": "failed"
            },
        )


# ============================================================================
# STRUCTURED EXTRACTION
# ============================================================================


def _get_structured_extraction(
    description: str,
    llm_client: StructuredLLMClient | None,
) -> StructuredExtraction:

    if llm_client is not None:
        try:
            payload = llm_client.structured_extract(
                description,
                StructuredExtraction,
            )

            return _normalize_structure(
                payload
            )

        except Exception:
            extraction = _extract_local_structure(
                description
            )

            extraction.metadata[
                "llm_fallback"
            ] = "used"

            return extraction

    return _extract_local_structure(
        description
    )


def _normalize_structure(
    payload: Any,
) -> StructuredExtraction:

    if isinstance(
        payload,
        StructuredExtraction,
    ):
        return payload

    if isinstance(
        payload,
        BaseModel,
    ):
        payload = payload.model_dump(
            mode="python"
        )

    if isinstance(
        payload,
        dict,
    ):
        try:
            return StructuredExtraction.model_validate(
                payload
            )

        except ValidationError as exc:
            raise ValueError(
                "Structured output could not be validated."
            ) from exc

    raise TypeError(
        "Structured extraction must evaluate to a mapping "
        "or a BaseModel instance."
    )


# ============================================================================
# PROCESSSTATE MATERIALIZATION
# ============================================================================


def _materialize_process_state(
    extraction: StructuredExtraction,
    description: str,
) -> ProcessState:

    evidence_records: list[Evidence] = []
    field_evidence: dict[str, list[str]] = {}

    def add_evidence(
        claim_key: str,
        label: str,
        value: Any = None,
        *,
        source: str = "user_input",
        status: EvidenceStatus = EvidenceStatus.VALIDATED,
        limitation: str | None = None,
    ) -> list[str]:
        line_no, excerpt = _locate_evidence_line(description, label, value)
        evidence_id = f"ev-{len(evidence_records) + 1:04d}"
        record = Evidence(
            id=evidence_id,
            source=source,
            page=None,
            location=f"line {line_no}" if line_no is not None else None,
            excerpt=excerpt,
            status=status,
            limitation=limitation,
        )
        evidence_records.append(record)
        field_evidence.setdefault(claim_key, []).append(evidence_id)
        return [evidence_id]

    parameters = []
    for item in extraction.parameters:
        name = str(item.get("name") or "Parameter").strip()
        if not name:
            continue
        evidence_ids = add_evidence(
            f"parameter:{name}",
            name,
            item.get("value"),
        )
        parameters.append(
            Parameter(
                name=name,
                value=item.get("value"),
                unit=item.get("unit"),
                parameter_type=item.get("parameter_type"),
                range=item.get("range"),
                controllable=item.get("controllable"),
                measurable=item.get("measurable"),
                description=item.get("description"),
                source=_coerce_provenance(item.get("source")),
                evidence_ids=evidence_ids,
            )
        )

    objectives = []
    for item in extraction.objectives:
        name = str(item.get("name") or "Objective").strip()
        if not name:
            continue
        evidence_ids = add_evidence(f"objective:{name}", "Objective", name)
        objectives.append(
            Objective(
                name=name,
                direction=item.get("direction"),
                target=item.get("target"),
                unit=item.get("unit"),
                description=item.get("description"),
                source=_coerce_provenance(item.get("source")),
                evidence_ids=evidence_ids,
            )
        )

    constraints = []
    for item in extraction.constraints:
        name = str(item.get("name") or "Constraint").strip()
        condition = item.get("condition")
        if not (condition or name):
            continue
        evidence_ids = add_evidence(f"constraint:{name}", "Constraint", condition or name)
        constraints.append(
            Constraint(
                name=name,
                condition=condition,
                value=item.get("value"),
                unit=item.get("unit"),
                description=item.get("description"),
                source=_coerce_provenance(item.get("source")),
                evidence_ids=evidence_ids,
            )
        )

    for field_name, value in [
        ("process", extraction.process),
        ("organism", extraction.organism),
        ("product", extraction.product),
        ("equipment", extraction.equipment),
        ("scale", extraction.scale),
    ]:
        if value:
            add_evidence(field_name, field_name, value)

    process_nodes, process_relations = _build_process_graph(
        extraction.operations,
        evidence_records,
        description,
    )

    state = ProcessState(
        process=extraction.process,
        organism=extraction.organism,
        product=extraction.product,
        equipment=extraction.equipment,
        scale=extraction.scale,

        parameters=parameters,
        objectives=objectives,
        constraints=constraints,

        process_nodes=process_nodes,
        process_relations=process_relations,
        evidence=evidence_records,
        field_evidence=field_evidence,

        missing_information=list(
            extraction.missing_information
            or []
        ),

        ambiguities=list(
            extraction.ambiguities
            or []
        ),

        contradictions=list(
            extraction.contradictions
            or []
        ),

        metadata=(
            extraction.metadata
            or {}
        ),
    )

    if (
        not state.process
        and "process"
        not in (state.metadata or {})
    ):
        state.missing_information.append(
            "Process type is missing."
        )

    if (
        not state.organism
        and "organism"
        not in (state.metadata or {})
    ):
        state.missing_information.append(
            "Organism is missing."
        )

    if (
        not state.product
        and "product"
        not in (state.metadata or {})
    ):
        state.missing_information.append(
            "Product is missing."
        )

    state.uncertainty_findings = _build_uncertainty_findings(state)

    unique_missing: list[str] = []
    seen: set[str] = set()

    for item in state.missing_information:
        if item not in seen:
            unique_missing.append(
                item
            )

            seen.add(item)

    state.missing_information = (
        unique_missing
    )

    return state


def _coerce_provenance(
    value: Any,
) -> Provenance:
    """Return a recognized provenance value."""

    if isinstance(
        value,
        Provenance,
    ):
        return value

    if isinstance(
        value,
        str,
    ):
        try:
            return Provenance(
                value
            )
        except ValueError:
            pass

    return Provenance.UNKNOWN


# ============================================================================
# LOCAL EXTRACTION
# ============================================================================


def _extract_local_structure(
    description: str,
) -> StructuredExtraction:

    normalized = description.strip()

    process = _extract_label_value(
        normalized,
        [
            "process",
            "process type",
            "bioprocess",
            "procedure",
        ],
    )

    organism = _extract_label_value(
        normalized,
        [
            "organism",
            "strain",
            "cell line",
        ],
    )

    product = _extract_label_value(
        normalized,
        [
            "product",
            "target product",
            "desired output",
        ],
    )

    equipment = _extract_label_value(
        normalized,
        [
            "equipment",
            "reactor",
            "bioreactor",
            "fermenter",
        ],
    )

    scale = _extract_label_value(
        normalized,
        [
            "scale",
            "batch scale",
            "pilot scale",
            "production scale",
        ],
    )

    parameter_entries = _extract_parameters(
        normalized
    )

    objective_entries = _extract_objectives(
        normalized
    )

    constraint_entries = _extract_constraints(
        normalized
    )

    operations = _extract_operations(normalized)

    missing_information = (
        _infer_missing_information(
            process,
            organism,
            product,
            parameter_entries,
        )
    )

    ambiguities = _detect_ambiguities(
        normalized
    )

    contradictions = _detect_contradictions(
        normalized
    )

    return StructuredExtraction(
        process=process,
        organism=organism,
        product=product,
        equipment=equipment,
        scale=scale,

        parameters=parameter_entries,
        objectives=objective_entries,
        constraints=constraint_entries,
        operations=operations,

        missing_information=missing_information,
        ambiguities=ambiguities,
        contradictions=contradictions,

        metadata={
            "source": "local_extraction"
        },
    )


# ============================================================================
# LABEL / VALUE EXTRACTION
# ============================================================================


def _extract_label_value(
    text: str,
    labels: list[str],
) -> str | None:

    for label in labels:

        match = re.search(
            rf"\b{re.escape(label)}\b"
            rf"\s*[:\-]?\s*(.+?)(?:\n|$)",
            text,
            flags=(
                re.IGNORECASE
                | re.MULTILINE
            ),
        )

        if match:
            value = (
                match.group(1)
                .strip()
                .rstrip(".;")
            )

            if value:
                return value

    for label in labels:

        match = re.search(
            rf"\b{re.escape(label)}\b"
            rf"\s*[:\-]?\s*(.+)",
            text,
            flags=re.IGNORECASE,
        )

        if match:
            value = (
                match.group(1)
                .strip()
                .rstrip(".;")
            )

            if value:
                return value

    return None


# ============================================================================
# SCIENTIFIC PARAMETER EXTRACTION
# ============================================================================


def _extract_parameters(
    text: str,
) -> list[dict[str, Any]]:
    """Extract parameters while preserving user-provided information.

    Direct ``Name: value`` parameters are preserved exactly as written.

    Natural-language scientific parameters are additionally extracted
    using canonical scientific names.

    Repeated parameters are intentionally preserved because repeated
    values may represent contradictions that must not be discarded.
    """

    params: list[dict[str, Any]] = []

    lines = [
        line.strip()
        for line in text.splitlines()
    ]

    # ------------------------------------------------------------------
    # Preserve direct "Name: value" parameters.
    # ------------------------------------------------------------------

    for line in lines:

        if not line or ":" not in line:
            continue

        name, value = line.split(
            ":",
            1,
        )

        name = name.strip()

        value = (
            value.strip()
            .rstrip(".;")
        )

        if not name or not value:
            continue

        key = name.lower()

        if key in {
            "process",
            "organism",
            "product",
            "objective",
            "constraint",
            "equipment",
            "scale",
            "operations",
            "process steps",
            "steps",
            "sequence",
            "operation sequence",
        }:
            continue

        # Preserve the exact user-facing parameter name.
        #
        # Example:
        #
        # Feed rate: 0.5 L/h
        #
        # remains:
        #
        # Feed rate = 0.5 L/h
        params.append(
            {
                "name": name,
                "value": value,
                "source": "user_provided",
            }
        )

    # ------------------------------------------------------------------
    # Add natural-language scientific parameters.
    # ------------------------------------------------------------------

    scientific_parameters = (
        _extract_scientific_parameters(
            text
        )
    )

    # Do not deduplicate the complete parameter list.
    #
    # Repeated parameters may represent contradictions and must remain
    # visible to the contradiction-detection layer.
    params.extend(
        scientific_parameters
    )

    return params


def _extract_scientific_parameters(
    text: str,
) -> list[dict[str, Any]]:
    """Extract canonical scientific parameters from natural language.

    Examples supported by the current prototype:

        Initial biomass concentration was 1 g/L.
        Initial glucose was 20 g/L.
        Reactor volume was 2 L.
        Feed rate was 0.02 L/h.
        Feed glucose concentration was 500 g/L.
        The fermentation lasted 10 h.
        Feed contained glucose at a concentration of 500 g/L.
        Fermentation lasted for 10 h.

    A value is only extracted when the description explicitly contains
    a numeric value and a supported unit.
    """

    extracted: list[dict[str, Any]] = []

    for line in text.splitlines():

        stripped = line.strip()

        if not stripped:
            continue

        for canonical_name, aliases in (
            SCIENTIFIC_PARAMETER_ALIASES.items()
        ):

            found_for_parameter = False

            for alias in aliases:

                pattern = (
                    rf"\b{re.escape(alias)}\b"
                )

                matches = re.finditer(
                    pattern,
                    stripped,
                    flags=re.IGNORECASE,
                )

                for match in matches:

                    tail = stripped[
                        match.end():
                    ]

                    parsed = _find_numeric_value(
                        tail
                    )

                    if parsed is None:
                        continue

                    numeric_value, unit = (
                        parsed
                    )

                    extracted.append(
                        {
                            "name": canonical_name,
                            "value": numeric_value,
                            "unit": unit,
                            "source": "user_provided",
                        }
                    )

                    found_for_parameter = True
                    break

                if found_for_parameter:
                    break

    # ------------------------------------------------------------------
    # Handle cases where the numeric value appears before the label,
    # or where the parameter is expressed as a natural-language phrase.
    #
    # Examples:
    #
    # "The feed contained 500 g/L glucose."
    # "Feed contained glucose at a concentration of 500 g/L."
    # "The fermentation lasted 10 h."
    # "Fermentation lasted for 10 h."
    # ------------------------------------------------------------------

    special_patterns = [
        (
            "feed_substrate",
            (
                r"\bfeed\b.{0,30}?"
                r"(?P<value>[0-9]+(?:\.[0-9]+)?)"
                r"\s*(?P<unit>g/L)\b"
                r".{0,30}"
                r"\b(?:glucose|substrate)\b"
            ),
        ),
        (
            "feed_substrate",
            (
                r"\bfeed\b.{0,50}?"
                r"\b(?:contained|contains|with)\b.{0,30}?"
                r"\b(?:glucose|substrate)\b"
                r".{0,50}?"
                r"\b(?:concentration|at)\b.{0,15}?"
                r"(?P<value>[0-9]+(?:\.[0-9]+)?)"
                r"\s*(?P<unit>g/L)\b"
            ),
        ),
        (
            "duration",
            (
                r"\b(?:fermentation|cultivation|process|run)\b"
                r".{0,30}?"
                r"\b(?:lasted|continued|ran)\b"
                r".{0,15}?"
                r"(?P<value>[0-9]+(?:\.[0-9]+)?)"
                r"\s*(?P<unit>h)\b"
            ),
        ),
    ]

    for canonical_name, pattern in (
        special_patterns
    ):

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:

            extracted.append(
                {
                    "name": canonical_name,
                    "value": float(
                        match.group("value")
                    ),
                    "unit": match.group("unit"),
                    "source": "user_provided",
                }
            )

    return extracted


def _find_numeric_value(
    text: str,
) -> tuple[float, str] | None:
    """Find the first supported numeric value nearby."""

    pattern = (
        r"(?P<value>-?[0-9]+(?:\.[0-9]+)?)"
        r"\s*"
        r"(?P<unit>"
        r"g/L|g/g|L/h|1/h|L|h|%|rpm"
        r")\b"
    )

    match = re.search(
        pattern,
        text[:120],
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    return (
        float(
            match.group("value")
        ),
        match.group("unit"),
    )


def _parse_numeric_value(
    value: str,
) -> tuple[float, str] | None:
    """Parse a value such as '20 g/L'."""

    return _find_numeric_value(
        value
    )


def _canonical_parameter_name(
    name: str,
) -> str | None:
    """Map a scientific alias to a canonical scientific name."""

    normalized = (
        name.strip()
        .lower()
        .replace("-", " ")
    )

    for canonical_name, aliases in (
        SCIENTIFIC_PARAMETER_ALIASES.items()
    ):

        for alias in aliases:

            alias_normalized = (
                alias.lower()
                .replace("-", " ")
            )

            if (
                normalized
                == alias_normalized
            ):
                return canonical_name

    return None


# ============================================================================
# OBJECTIVES
# ============================================================================


def _extract_objectives(
    text: str,
) -> list[dict[str, Any]]:

    entries: list[dict[str, Any]] = []

    for line in text.splitlines():

        stripped = line.strip()

        if not stripped:
            continue

        if re.search(
            (
                r"\b(objective|goal|target|"
                r"maximize|minimize|improve|maintain)\b"
            ),
            stripped,
            flags=re.IGNORECASE,
        ):

            clean = stripped

            if ":" in stripped:

                _, clean = stripped.split(
                    ":",
                    1,
                )

            clean = (
                clean.strip()
                .rstrip(".;")
            )

            if clean:

                entries.append(
                    {
                        "name": (
                            clean[:120]
                            or "Objective"
                        ),

                        "direction": (
                            "maximize"
                            if (
                                "maximize"
                                in stripped.lower()
                                or "improve"
                                in stripped.lower()
                            )
                            else (
                                "minimize"
                                if (
                                    "minimize"
                                    in stripped.lower()
                                )
                                else None
                            )
                        ),

                        "source": "user_provided",
                    }
                )

    return entries


# ============================================================================
# CONSTRAINTS
# ============================================================================


def _extract_constraints(
    text: str,
) -> list[dict[str, Any]]:

    entries: list[dict[str, Any]] = []

    for line in text.splitlines():

        stripped = line.strip()

        if not stripped:
            continue

        if re.search(
            (
                r"\b(maximum|minimum|must not|"
                r"cannot exceed|keep below|"
                r"keep under|limit|not exceed|"
                r"no more than|at least|at most)\b"
            ),
            stripped,
            flags=re.IGNORECASE,
        ):

            entries.append(
                {
                    "name": "Constraint",
                    "condition": stripped,
                    "source": "user_provided",
                }
            )

    return entries


# ============================================================================
# PROCESS GRAPH + EVIDENCE
# ============================================================================

def _locate_evidence_line(
    description: str,
    label: str,
    value: Any = None,
) -> tuple[int | None, str | None]:
    """Locate the most plausible source line for an extracted claim."""

    label_text = str(label or "").strip().lower()
    value_text = str(value).strip().lower() if value is not None else ""

    lines = description.splitlines()
    candidates: list[tuple[int, str, int]] = []
    for index, line in enumerate(lines, start=1):
        lower = line.lower()
        score = 0
        if label_text and label_text in lower:
            score += 3
        if value_text and value_text in lower:
            score += 2
        if score:
            candidates.append((index, line.strip(), score))

    if not candidates:
        return None, None

    candidates.sort(key=lambda item: (-item[2], item[0]))
    line_no, excerpt, _ = candidates[0]
    return line_no, excerpt


def _extract_operations(text: str) -> list[str]:
    """Extract only explicitly labelled operation sequences."""

    labels = ("operations", "process steps", "steps", "sequence", "operation sequence")
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or ":" not in stripped:
            continue
        label, value = stripped.split(":", 1)
        if label.strip().lower() not in labels:
            continue
        parts = re.split(r"\s*(?:->|→|;|\|)\s*", value.strip())
        operations = [part.strip().rstrip(".;") for part in parts if part.strip()]
        return operations
    return []


def _build_process_graph(
    operations: list[str],
    evidence_records: list[Evidence],
    description: str,
) -> tuple[list[ProcessNode], list[ProcessRelation]]:
    """Build a conservative graph only from an explicit operation sequence."""

    if not operations:
        return [], []

    # The operation sequence is explicitly sourced from the input. Attach the
    # same line evidence to each operation and each sequential edge.
    line_no, excerpt = _locate_evidence_line(description, "Operations")
    evidence_id = None
    if line_no is not None:
        evidence_id = next(
            (item.id for item in evidence_records if item.location == f"line {line_no}"),
            None,
        )
        if evidence_id is None:
            evidence_id = f"ev-{len(evidence_records) + 1:04d}"
            evidence_records.append(
                Evidence(
                    id=evidence_id,
                    source="user_input",
                    location=f"line {line_no}",
                    excerpt=excerpt,
                    status=EvidenceStatus.VALIDATED,
                )
            )

    nodes: list[ProcessNode] = []
    for index, operation in enumerate(operations, start=1):
        nodes.append(
            ProcessNode(
                id=f"op-{index:03d}",
                kind="operation",
                name=operation,
                provenance=Provenance.USER_PROVIDED,
                evidence_ids=[evidence_id] if evidence_id else [],
            )
        )

    relations: list[ProcessRelation] = []
    for left, right in zip(nodes, nodes[1:]):
        relations.append(
            ProcessRelation(
                source_node_id=left.id,
                relation="precedes",
                target_node_id=right.id,
                provenance=Provenance.USER_PROVIDED,
                evidence_ids=[evidence_id] if evidence_id else [],
            )
        )

    return nodes, relations


def _build_uncertainty_findings(state: ProcessState) -> list[UncertaintyFinding]:
    findings: list[UncertaintyFinding] = []
    for category, messages in (
        ("missing", state.missing_information),
        ("ambiguous", state.ambiguities),
        ("contradictory", state.contradictions),
    ):
        for index, message in enumerate(messages, start=1):
            findings.append(
                UncertaintyFinding(
                    id=f"{category}-{index:03d}",
                    category=category,
                    message=message,
                )
            )
    return findings


# ============================================================================
# MISSING INFORMATION
# ============================================================================


def _infer_missing_information(
    process: str | None,
    organism: str | None,
    product: str | None,
    parameters: list[dict[str, Any]],
) -> list[str]:

    missing: list[str] = []

    if not process:
        missing.append(
            "Process type is missing."
        )

    if not organism:
        missing.append(
            "Organism is missing."
        )

    if not product:
        missing.append(
            "Product is missing."
        )

    if not parameters:
        missing.append(
            "Operating parameters are not explicitly stated."
        )

    return missing


# ============================================================================
# AMBIGUITY DETECTION
# ============================================================================


def _detect_ambiguities(
    text: str,
) -> list[str]:

    ambiguities: list[str] = []

    qualifiers = (
        r"\b(about|approximately|roughly|around|"
        r"maybe|possibly|likely|unclear|uncertain|"
        r"or|either|some|several|a few|approx|rough)\b"
    )

    for line in text.splitlines():

        stripped = line.strip()

        if not stripped:
            continue

        if not re.search(
            qualifiers,
            stripped,
            flags=re.IGNORECASE,
        ):
            continue

        field_name, value = (
            _directly_labelled_field(
                stripped
            )
        )

        if field_name:

            ambiguities.append(
                f"{field_name} is stated with "
                f"qualitative or uncertain wording: "
                f"{value!r}."
            )

        else:

            ambiguities.append(
                "The description contains qualitative "
                "or uncertain wording."
            )

    return list(
        dict.fromkeys(
            ambiguities
        )
    )


# ============================================================================
# CONTRADICTION DETECTION
# ============================================================================


def _detect_contradictions(
    text: str,
) -> list[str]:

    contradictions: list[str] = []

    for label, display_name in [
        ("temperature", "Temperature"),
        ("pH", "pH"),
        ("agitation", "Agitation"),
        ("feed rate", "Feed rate"),
        ("pressure", "Pressure"),
    ]:

        matches = [
            m.group("value")
            .strip()
            .rstrip(".;")
            for m in re.finditer(
                (
                    rf"\b{re.escape(label)}\b"
                    rf"\s*[:\-]?"
                    rf"\s*(?P<value>[^\n]+)"
                ),
                text,
                flags=re.IGNORECASE,
            )
        ]

        unique = list(
            dict.fromkeys(
                matches
            )
        )

        if len(unique) > 1:

            stated_values = "; ".join(
                repr(value)
                for value in unique
            )

            contradictions.append(
                f"{display_name} has conflicting "
                f"stated values: {stated_values}."
            )

    return contradictions


# ============================================================================
# DIRECTLY LABELLED FIELD
# ============================================================================


def _directly_labelled_field(
    line: str,
) -> tuple[str | None, str]:

    match = re.match(
        r"(?P<field>[^:]+):\s*(?P<value>.+)",
        line,
    )

    if not match:
        return None, line

    return (
        match.group("field").strip(),
        match.group("value")
        .strip()
        .rstrip(".;"),
    )