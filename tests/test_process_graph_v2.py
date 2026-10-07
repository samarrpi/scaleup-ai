from pathlib import Path

from agents.process_understanding import understand_process


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def read_example(filename: str) -> str:
    return (EXAMPLES / filename).read_text(encoding="utf-8")


def test_graph_nodes_are_typed_and_evidence_linked():
    state = understand_process(read_example("clean_process.txt"))

    assert state.process_nodes
    assert all(node.kind == "operation" for node in state.process_nodes)
    assert all(node.provenance.value == "user_provided" for node in state.process_nodes)
    assert all(node.evidence_ids for node in state.process_nodes)


def test_graph_relations_are_explicitly_sequenced_and_evidenced():
    state = understand_process(read_example("clean_process.txt"))

    assert [relation.relation for relation in state.process_relations] == [
        "precedes",
        "precedes",
        "precedes",
    ]
    assert all(relation.evidence_ids for relation in state.process_relations)


def test_graph_does_not_create_topology_without_explicit_operations():
    state = understand_process(read_example("missing_information.txt"))

    assert state.process_nodes == []
    assert state.process_relations == []
