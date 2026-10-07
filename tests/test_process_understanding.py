from pathlib import Path

from agents.process_understanding import understand_process
from schemas.process import ProcessState, Provenance


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def read_example(filename: str) -> str:
    return (EXAMPLES / filename).read_text(encoding="utf-8")


def parameter_by_name(state: ProcessState, name: str):
    return next(parameter for parameter in state.parameters if parameter.name == name)


def test_clean_example_extracts_directly_stated_process_information():
    state = understand_process(read_example("clean_process.txt"))

    assert state.process == "Fermentation"
    assert state.organism == "E. coli"
    assert state.product == "Insulin"
    assert parameter_by_name(state, "Temperature").value == "37 C"
    assert parameter_by_name(state, "Feed rate").value == "0.5 L/h"
    assert state.objectives[0].name == "Maximize product titer"
    assert not state.missing_information


def test_messy_example_returns_a_conservative_process_state():
    state = understand_process(read_example("messy_process.txt"))

    assert isinstance(state, ProcessState)
    assert state.metadata["source"] == "local_extraction"
    assert state.organism is None
    assert "Organism is missing." in state.missing_information
    assert "37 C" not in [parameter.value for parameter in state.parameters]


def test_missing_information_example_keeps_unspecified_parameters_unset():
    state = understand_process(read_example("missing_information.txt"))

    assert state.process == "Cell culture"
    assert state.organism == "Mammalian cell line"
    assert state.product == "Antibody"
    assert state.parameters == []
    assert "Operating parameters are not explicitly stated." in state.missing_information


def test_ambiguous_example_preserves_qualitative_values_and_flags_fields():
    state = understand_process(read_example("ambiguous_information.txt"))

    assert parameter_by_name(state, "Temperature").value == "about 30 C"
    assert parameter_by_name(state, "pH").value == "maybe 6.5"
    assert parameter_by_name(state, "Agitation").value == "around 150 rpm or 200 rpm"
    assert any(message.startswith("Temperature is stated") for message in state.ambiguities)
    assert any(message.startswith("pH is stated") for message in state.ambiguities)
    assert any(message.startswith("Agitation is stated") for message in state.ambiguities)


def test_contradictory_example_preserves_values_and_reports_conflict():
    state = understand_process(read_example("contradiction.txt"))

    temperatures = [
        parameter.value
        for parameter in state.parameters
        if parameter.name == "Temperature"
    ]
    assert temperatures == ["25 C", "37 C"]
    assert any(message.startswith("Temperature has conflicting stated values") for message in state.contradictions)


def test_structured_llm_provenance_is_preserved_and_unknown_values_stay_unknown():
    class SourceAwareClient:
        def structured_extract(self, user_description, schema):
            return {
                "process": "Fermentation",
                "parameters": [
                    {"name": "temperature", "value": "high", "source": "calculated"},
                    {"name": "pH", "value": "unknown", "source": "not_a_provenance"},
                ],
            }

    state = understand_process("A supplied process description.", SourceAwareClient())

    assert parameter_by_name(state, "temperature").source is Provenance.CALCULATED
    assert parameter_by_name(state, "pH").source is Provenance.UNKNOWN


def test_llm_failure_uses_local_fallback_without_raw_error_details():
    class FailingClient:
        def structured_extract(self, user_description, schema):
            raise RuntimeError("secret adapter failure")

    state = understand_process(read_example("clean_process.txt"), FailingClient())

    assert state.metadata["source"] == "local_extraction"
    assert state.metadata["llm_fallback"] == "used"
    assert state.process == "Fermentation"
    assert "secret adapter failure" not in str(state.model_dump())
from agents.process_understanding import understand_process


def test_extracts_initial_biomass_from_natural_language():
    state = understand_process(
        "A fermentation process used an initial biomass concentration of 1 g/L."
    )

    parameter = next(
        p for p in state.parameters
        if p.name == "initial_biomass"
    )

    assert parameter.value == 1.0
    assert parameter.unit == "g/L"


def test_extracts_initial_substrate_from_natural_language():
    state = understand_process(
        "The initial glucose concentration was 20 g/L."
    )

    parameter = next(
        p for p in state.parameters
        if p.name == "initial_substrate"
    )

    assert parameter.value == 20.0
    assert parameter.unit == "g/L"


def test_extracts_initial_volume_from_natural_language():
    state = understand_process(
        "The reactor volume was initially 2 L."
    )

    parameter = next(
        p for p in state.parameters
        if p.name == "initial_volume"
    )

    assert parameter.value == 2.0
    assert parameter.unit == "L"


def test_extracts_feed_rate_from_natural_language():
    state = understand_process(
        "The fermentation used a feed rate of 0.02 L/h."
    )

    parameter = next(
        p for p in state.parameters
        if p.name == "feed_rate"
    )

    assert parameter.value == 0.02
    assert parameter.unit == "L/h"


def test_extracts_feed_substrate_from_natural_language():
    state = understand_process(
        "The feed contained glucose at a concentration of 500 g/L."
    )

    parameter = next(
        p for p in state.parameters
        if p.name == "feed_substrate"
    )

    assert parameter.value == 500.0
    assert parameter.unit == "g/L"


def test_extracts_duration_from_natural_language():
    state = understand_process(
        "The fermentation lasted for 10 h."
    )

    parameter = next(
        p for p in state.parameters
        if p.name == "duration"
    )

    assert parameter.value == 10.0
    assert parameter.unit == "h"