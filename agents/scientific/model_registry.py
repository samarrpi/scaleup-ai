"""Small model registry for the ScaleUp AI scientific-model layer.

The registry deliberately separates model discovery from any particular model
implementation. A model can declare applicability and readiness without being
run, which lets the UI explain why a model is or is not available for a
ProcessState.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from schemas.process import ProcessState


ApplicabilityFn = Callable[[ProcessState], bool]
ReadinessFn = Callable[[ProcessState], dict[str, Any]]
RunFn = Callable[[ProcessState], Any]


@dataclass(frozen=True)
class ModelSpec:
    id: str
    name: str
    description: str
    domain: str
    applicability: ApplicabilityFn
    readiness: ReadinessFn
    run: RunFn



def _ecoli_spec() -> ModelSpec:
    from agents.scientific.ecoli_runner import (
        get_ecoli_model_readiness,
        is_ecoli_model_applicable,
        run_from_process_state,
    )

    return ModelSpec(
        id="ecoli_fed_batch",
        name="E. coli Fed-Batch Model",
        description=(
            "Mechanistic screening model for an E. coli fed-batch process "
            "using the current Monod-style growth and material-balance implementation."
        ),
        domain="bioprocess",
        applicability=is_ecoli_model_applicable,
        readiness=get_ecoli_model_readiness,
        run=run_from_process_state,
    )


_REGISTRY = (_ecoli_spec(),)


def list_models() -> list[ModelSpec]:
    return list(_REGISTRY)


def inspect_models(state: ProcessState) -> list[dict[str, Any]]:
    """Return model applicability/readiness without executing any model."""
    records: list[dict[str, Any]] = []
    for spec in _REGISTRY:
        applicable = spec.applicability(state)
        readiness = spec.readiness(state) if applicable else None
        records.append(
            {
                "id": spec.id,
                "name": spec.name,
                "description": spec.description,
                "domain": spec.domain,
                "applicable": applicable,
                "ready": bool(readiness and readiness.get("ready")),
                "readiness": readiness,
            }
        )
    return records
