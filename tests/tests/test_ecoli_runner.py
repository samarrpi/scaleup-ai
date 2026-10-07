from schemas.process import ModelResult, Parameter, ProcessState

from agents.scientific.ecoli_runner import (
    get_ecoli_model_readiness,
    is_ecoli_model_applicable,
    run_from_process_state,
    validate_ecoli_inputs,
)


def test_run_from_process_state_returns_model_result():
    process_state = ProcessState(
        process="fed-batch fermentation",
        organism="E. coli",
        product="recombinant protein",
        equipment="2 L bioreactor",
        scale="2 L",
        parameters=[
            Parameter(
                name="initial_biomass",
                value=1.0,
                unit="g/L",
            ),
            Parameter(
                name="initial_substrate",
                value=20.0,
                unit="g/L",
            ),
            Parameter(
                name="initial_product",
                value=0.0,
                unit="g/L",
            ),
            Parameter(
                name="initial_volume",
                value=2.0,
                unit="L",
            ),
            Parameter(
                name="mu_max",
                value=0.5,
                unit="1/h",
            ),
            Parameter(
                name="Ks",
                value=1.0,
                unit="g/L",
            ),
            Parameter(
                name="Yxs",
                value=0.5,
                unit="g/g",
            ),
            Parameter(
                name="Ypx",
                value=0.10,
                unit="g/g",
            ),
            Parameter(
                name="feed_rate",
                value=0.02,
                unit="L/h",
            ),
            Parameter(
                name="feed_substrate",
                value=500.0,
                unit="g/L",
            ),
            Parameter(
                name="duration",
                value=10.0,
                unit="h",
            ),
        ],
    )

    result = run_from_process_state(process_state)

    assert isinstance(result, ModelResult)

    assert result.predictions["final_biomass_g_L"] > 0
    assert result.predictions["final_product_g_L"] > 0
    assert abs(result.predictions["final_volume_L"] - 2.2) < 1e-9

    assert result.model_metadata["process_state"]["process"] == (
        "fed-batch fermentation"
    )


def test_validation_identifies_provided_parameters():
    process_state = ProcessState(
        parameters=[
            Parameter(
                name="initial_biomass",
                value=1.0,
                unit="g/L",
            ),
            Parameter(
                name="initial_volume",
                value=2.0,
                unit="L",
            ),
        ]
    )

    validation = validate_ecoli_inputs(process_state)

    assert "initial_biomass" in validation["provided_parameters"]
    assert "initial_volume" in validation["provided_parameters"]

    assert "mu_max" in validation["assumed_parameters"]
    assert "Ks" in validation["assumed_parameters"]


def test_model_records_input_assumptions():
    process_state = ProcessState(
        parameters=[
            Parameter(
                name="initial_biomass",
                value=1.0,
                unit="g/L",
            ),
        ]
    )

    result = run_from_process_state(process_state)

    assumptions = result.model_metadata["input_assumptions"]

    assumption_names = [
        assumption["parameter"]
        for assumption in assumptions
    ]

    assert "mu_max" in assumption_names
    assert "Ks" in assumption_names
    assert "Yxs" in assumption_names


def test_ecoli_model_is_applicable_to_ecoli_fed_batch():
    process_state = ProcessState(
        process="fed-batch fermentation",
        organism="E. coli",
    )

    assert is_ecoli_model_applicable(process_state) is True


def test_ecoli_model_is_not_applicable_to_unrelated_process():
    process_state = ProcessState(
        process="distillation",
        organism="E. coli",
    )

    assert is_ecoli_model_applicable(process_state) is False


def test_ecoli_model_is_not_applicable_to_non_ecoli_process():
    process_state = ProcessState(
        process="fed-batch fermentation",
        organism="yeast",
    )

    assert is_ecoli_model_applicable(process_state) is False


def test_ecoli_model_is_not_ready_when_process_inputs_are_missing():
    process_state = ProcessState(
        process="fermentation",
        organism="E. coli",
        product="insulin",
        parameters=[
            Parameter(
                name="feed_rate",
                value=0.5,
                unit="L/h",
            ),
        ],
    )

    readiness = get_ecoli_model_readiness(process_state)

    assert readiness["ready"] is False

    assert "initial_biomass" in readiness["missing_required_parameters"]
    assert "initial_substrate" in readiness["missing_required_parameters"]
    assert "initial_volume" in readiness["missing_required_parameters"]
    assert "feed_substrate" in readiness["missing_required_parameters"]
    assert "duration" in readiness["missing_required_parameters"]

    assert "feed_rate" in readiness["provided_process_parameters"]


def test_ecoli_model_is_ready_when_required_process_inputs_are_provided():
    process_state = ProcessState(
        process="fed-batch fermentation",
        organism="E. coli",
        product="recombinant protein",
        parameters=[
            Parameter(
                name="initial_biomass",
                value=1.0,
                unit="g/L",
            ),
            Parameter(
                name="initial_substrate",
                value=20.0,
                unit="g/L",
            ),
            Parameter(
                name="initial_product",
                value=0.0,
                unit="g/L",
            ),
            Parameter(
                name="initial_volume",
                value=2.0,
                unit="L",
            ),
            Parameter(
                name="feed_rate",
                value=0.02,
                unit="L/h",
            ),
            Parameter(
                name="feed_substrate",
                value=500.0,
                unit="g/L",
            ),
            Parameter(
                name="duration",
                value=10.0,
                unit="h",
            ),
        ],
    )

    readiness = get_ecoli_model_readiness(process_state)

    assert readiness["ready"] is True
    assert readiness["missing_required_parameters"] == []