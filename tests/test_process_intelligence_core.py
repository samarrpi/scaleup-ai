from pathlib import Path

from agents.process_understanding import understand_process
from agents.scientific.model_registry import inspect_models


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def read_example(filename: str) -> str:
    return (EXAMPLES / filename).read_text(encoding="utf-8")


def test_process_state_contains_traceable_evidence_records():
    state = understand_process(read_example("clean_process.txt"))

    assert state.evidence
    temperature = next(p for p in state.parameters if p.name == "Temperature")
    assert temperature.evidence_ids
    evidence = next(e for e in state.evidence if e.id == temperature.evidence_ids[0])
    assert evidence.source == "user_input"
    assert evidence.location == "line 6"
    assert evidence.excerpt == "Temperature: 37 C"


def test_explicit_operations_create_a_typed_process_graph():
    state = understand_process(read_example("ecoli_fed_batch.txt"))

    assert [node.name for node in state.process_nodes] == [
        "Media preparation",
        "Inoculation",
        "Fed-batch growth",
        "Harvest",
    ]
    assert len(state.process_relations) == 3
    assert all(relation.relation == "precedes" for relation in state.process_relations)
    assert all(relation.evidence_ids for relation in state.process_relations)


def test_graph_is_not_invented_when_no_explicit_sequence_is_given():
    state = understand_process(read_example("missing_information.txt"))

    assert state.process_nodes == []
    assert state.process_relations == []


def test_uncertainty_is_materialized_as_structured_findings():
    state = understand_process(read_example("contradiction.txt"))

    assert state.uncertainty_findings
    assert any(f.category == "contradictory" for f in state.uncertainty_findings)


def test_model_registry_separates_applicability_from_readiness():
    state = understand_process(read_example("ecoli_fed_batch.txt"))
    records = inspect_models(state)

    ecoli = next(record for record in records if record["id"] == "ecoli_fed_batch")
    assert ecoli["applicable"] is True
    assert ecoli["ready"] is True
