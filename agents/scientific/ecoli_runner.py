from typing import Any

from schemas.process import ModelResult, ProcessState

from agents.scientific.ecoli_model import (
    run_ecoli_model,
)

from agents.scientific.engineering_analysis import (
    calculate_engineering_analysis,
)


# Scientific parameters that currently have prototype assumptions.
# These are intentionally recorded as assumptions rather than
# silently treated as user-provided values.

DEFAULTS = {
    "initial_biomass": 1.0,
    "initial_substrate": 20.0,
    "initial_product": 0.0,
    "initial_volume": 2.0,
    "mu_max": 0.5,
    "Ks": 1.0,
    "Yxs": 0.5,
    "Ypx": 0.10,
    "feed_rate": 0.02,
    "feed_substrate": 500.0,
    "duration": 10.0,
}


def _get_parameter(
    process_state: ProcessState,
    name: str,
    default: Any = None,
) -> Any:
    """
    Find a parameter by name in ProcessState.

    Prefer the exact canonical parameter name when duplicate
    human-readable and normalized parameters are present.
    """

    target = name.strip().lower()

    # First look for the canonical scientific parameter name.
    for parameter in process_state.parameters:
        if parameter.name.strip() == name.strip():
            return parameter.value

    # Fall back to case-insensitive matching.
    for parameter in process_state.parameters:
        if parameter.name.strip().lower() == target:
            return parameter.value

    return default

def is_ecoli_model_applicable(
    process_state: ProcessState,
) -> bool:
    """
    Determine whether the current ProcessState is applicable
    to the E. coli fed-batch prototype.

    The prototype currently applies only when:
    - the organism is identified as E. coli, and
    - the process is identified as fermentation or fed-batch.

    This check deliberately uses the structured ProcessState
    rather than the selected UI example name.
    """

    organism = (
        process_state.organism or ""
    ).strip().lower()

    process = (
        process_state.process or ""
    ).strip().lower()

    ecoli_detected = any(
        term in organism
        for term in (
            "e. coli",
            "e coli",
            "escherichia coli",
        )
    )

    fermentation_detected = any(
        term in process
        for term in (
            "fermentation",
            "fermenter",
        )
    )

    fed_batch_detected = any(
        term in process
        for term in (
            "fed-batch",
            "fed batch",
            "fedbatch",
        )
    )

    return (
        ecoli_detected
        and (
            fermentation_detected
            or fed_batch_detected
        )
    )

def get_ecoli_model_readiness(
    process_state: ProcessState,
) -> dict[str, Any]:
    """
    Determine whether the E. coli fed-batch model has enough
    process-specific information to run responsibly.

    Applicability answers:
        "Could this model apply to this process?"

    Readiness answers:
        "Do we have enough user-provided process inputs
         to execute this model?"

    Model-specific constants such as mu_max, Ks, Yxs and Ypx
    may remain prototype assumptions. Process-specific operating
    inputs should be explicitly provided before simulation.
    """

    validation = validate_ecoli_inputs(process_state)

    required_process_parameters = [
        "initial_biomass",
        "initial_substrate",
        "initial_product",
        "initial_volume",
        "feed_rate",
        "feed_substrate",
        "duration",
    ]

    provided = set(validation["provided_parameters"])

    missing_required = [
        parameter
        for parameter in required_process_parameters
        if parameter not in provided
    ]

    return {
        "ready": len(missing_required) == 0,
        "required_process_parameters": required_process_parameters,
        "provided_process_parameters": [
            parameter
            for parameter in required_process_parameters
            if parameter in provided
        ],
        "missing_required_parameters": missing_required,
        "validation": validation,
    }

def _parameter_was_provided(
    process_state: ProcessState,
    name: str,
) -> bool:
    """
    Return True when the requested parameter exists in ProcessState
    and contains a non-null value.
    """

    target = name.strip().lower()

    for parameter in process_state.parameters:
        if parameter.name.strip().lower() == target:
            return parameter.value is not None

    return False


def validate_ecoli_inputs(
    process_state: ProcessState,
) -> dict[str, Any]:
    """
    Validate the scientific inputs required by the current
    E. coli fed-batch prototype.

    At this prototype stage, missing parameters are allowed to
    fall back to documented defaults. The validation result records
    which parameters came from the process description and which
    were assumed.
    """

    required_parameters = list(
        DEFAULTS.keys()
    )

    provided_parameters: list[str] = []
    assumed_parameters: list[str] = []
    missing_parameters: list[str] = []

    for parameter_name in required_parameters:
        if _parameter_was_provided(
            process_state,
            parameter_name,
        ):
            provided_parameters.append(
                parameter_name
            )
        else:
            assumed_parameters.append(
                parameter_name
            )

    # At this prototype stage, all parameters have fallback values.
    missing_parameters = []

    return {
        "status": (
            "complete"
            if not missing_parameters
            else "incomplete"
        ),
        "provided_parameters": (
            provided_parameters
        ),
        "assumed_parameters": (
            assumed_parameters
        ),
        "missing_parameters": (
            missing_parameters
        ),
    }


def run_from_process_state(
    process_state: ProcessState,
) -> ModelResult:
    """
    Run the E. coli scientific model using a ProcessState.

    The adapter translates the repository-level ProcessState
    representation into the inputs required by the E. coli model.

    Any parameter that is not present in ProcessState is recorded
    as a prototype assumption in the returned ModelResult.
    """

    validation = validate_ecoli_inputs(
        process_state
    )

    X0 = _get_parameter(
        process_state,
        "initial_biomass",
        DEFAULTS["initial_biomass"],
    )

    S0 = _get_parameter(
        process_state,
        "initial_substrate",
        DEFAULTS["initial_substrate"],
    )

    P0 = _get_parameter(
        process_state,
        "initial_product",
        DEFAULTS["initial_product"],
    )

    V0 = _get_parameter(
        process_state,
        "initial_volume",
        DEFAULTS["initial_volume"],
    )

    mu_max = _get_parameter(
        process_state,
        "mu_max",
        DEFAULTS["mu_max"],
    )

    Ks = _get_parameter(
        process_state,
        "Ks",
        DEFAULTS["Ks"],
    )

    Yxs = _get_parameter(
        process_state,
        "Yxs",
        DEFAULTS["Yxs"],
    )

    Ypx = _get_parameter(
        process_state,
        "Ypx",
        DEFAULTS["Ypx"],
    )

    F = _get_parameter(
        process_state,
        "feed_rate",
        DEFAULTS["feed_rate"],
    )

    Sf = _get_parameter(
        process_state,
        "feed_substrate",
        DEFAULTS["feed_substrate"],
    )

    duration = _get_parameter(
        process_state,
        "duration",
        DEFAULTS["duration"],
    )

    # ---------------------------------------------------------------
    # Run scientific model
    # ---------------------------------------------------------------

    result = run_ecoli_model(
        X0=float(X0),
        S0=float(S0),
        P0=float(P0),
        V0=float(V0),
        mu_max=float(mu_max),
        Ks=float(Ks),
        Yxs=float(Yxs),
        Ypx=float(Ypx),
        F=float(F),
        Sf=float(Sf),
        duration=float(duration),
    )

    # ---------------------------------------------------------------
    # Record ProcessState provenance
    # ---------------------------------------------------------------

    result.model_metadata["process_state"] = {
        "process": process_state.process,
        "organism": process_state.organism,
        "product": process_state.product,
        "equipment": process_state.equipment,
        "scale": process_state.scale,
    }

    # ---------------------------------------------------------------
    # Record input validation
    # ---------------------------------------------------------------

    result.model_metadata[
        "input_validation"
    ] = validation

    # ---------------------------------------------------------------
    # Record assumptions
    # ---------------------------------------------------------------

    assumptions: list[dict[str, Any]] = []

    for parameter_name in validation[
        "assumed_parameters"
    ]:
        assumptions.append(
            {
                "parameter": parameter_name,
                "value": DEFAULTS[
                    parameter_name
                ],
                "reason": (
                    "Parameter was not provided in "
                    "ProcessState; prototype default "
                    "value was used."
                ),
            }
        )

    result.model_metadata[
        "input_assumptions"
    ] = assumptions

    # ---------------------------------------------------------------
    # Record exact numerical inputs used by the model
    # ---------------------------------------------------------------

    result.model_metadata[
        "input_parameters"
    ] = {
        "initial_biomass": float(X0),
        "initial_substrate": float(S0),
        "initial_product": float(P0),
        "initial_volume": float(V0),
        "mu_max": float(mu_max),
        "Ks": float(Ks),
        "Yxs": float(Yxs),
        "Ypx": float(Ypx),
        "feed_rate": float(F),
        "feed_substrate": float(Sf),
        "duration": float(duration),
    }

    # ---------------------------------------------------------------
    # Engineering analysis
    # ---------------------------------------------------------------

    engineering_analysis = (
        calculate_engineering_analysis(
            result
        )
    )

    result.model_metadata[
        "engineering_analysis"
    ] = engineering_analysis.model_dump(
        mode="json"
    )

    return result