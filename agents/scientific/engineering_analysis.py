from schemas.engineering import EngineeringAnalysis
from schemas.process import ModelResult


def _safe_divide(
    numerator: float,
    denominator: float,
) -> float | None:
    """Return numerator / denominator unless denominator is zero."""

    if abs(denominator) < 1e-12:
        return None

    return numerator / denominator


def calculate_engineering_analysis(
    result: ModelResult,
) -> EngineeringAnalysis:
    """
    Calculate engineering metrics from a scientific model result.

    The current implementation is designed for the E. coli fed-batch
    prototype and uses the simulated concentration and volume
    trajectories already contained in ModelResult.

    The function converts scientific model output into engineering
    quantities such as:

    - mass balances
    - substrate consumption
    - biomass and product yields
    - productivity
    - dilution rate
    - feed volume
    - volume-balance checks
    """

    predictions = result.predictions

    time_values = predictions.get(
        "time_h",
        [],
    )

    biomass_values = predictions.get(
        "biomass_g_L",
        [],
    )

    substrate_values = predictions.get(
        "substrate_g_L",
        [],
    )

    product_values = predictions.get(
        "product_g_L",
        [],
    )

    volume_values = predictions.get(
        "volume_L",
        [],
    )

    if not time_values:
        raise ValueError(
            "Engineering analysis requires a simulation trajectory."
        )

    initial_biomass = float(
        biomass_values[0]
    )

    final_biomass = float(
        biomass_values[-1]
    )

    initial_substrate = float(
        substrate_values[0]
    )

    final_substrate = float(
        substrate_values[-1]
    )

    initial_product = float(
        product_values[0]
    )

    final_product = float(
        product_values[-1]
    )

    initial_volume = float(
        volume_values[0]
    )

    final_volume = float(
        volume_values[-1]
    )

    duration = float(
        time_values[-1]
    )

    # ---------------------------------------------------------------
    # Biomass mass balance
    # ---------------------------------------------------------------

    initial_biomass_mass = (
        initial_biomass
        * initial_volume
    )

    final_biomass_mass = (
        final_biomass
        * final_volume
    )

    biomass_formed = (
        final_biomass_mass
        - initial_biomass_mass
    )

    # ---------------------------------------------------------------
    # Substrate mass balance
    # ---------------------------------------------------------------

    initial_substrate_mass = (
        initial_substrate
        * initial_volume
    )

    final_substrate_mass = (
        final_substrate
        * final_volume
    )

    # ---------------------------------------------------------------
    # Product mass balance
    # ---------------------------------------------------------------

    initial_product_mass = (
        initial_product
        * initial_volume
    )

    final_product_mass = (
        final_product
        * final_volume
    )

    product_formed = (
        final_product_mass
        - initial_product_mass
    )

    # ---------------------------------------------------------------
    # Feed calculations
    # ---------------------------------------------------------------

    feed_volume = (
        final_volume
        - initial_volume
    )

    input_parameters = result.model_metadata.get(
        "input_parameters",
        {},
    )

    feed_rate = input_parameters.get(
        "feed_rate"
    )

    feed_substrate = input_parameters.get(
        "feed_substrate"
    )

    # ---------------------------------------------------------------
    # Substrate fed
    # ---------------------------------------------------------------

    substrate_fed = None

    if (
        feed_rate is not None
        and feed_substrate is not None
    ):
        substrate_fed = (
            float(feed_rate)
            * duration
            * float(feed_substrate)
        )

    # ---------------------------------------------------------------
    # Substrate consumed
    # ---------------------------------------------------------------

    substrate_consumed = None

    if substrate_fed is not None:
        substrate_consumed = (
            initial_substrate_mass
            + substrate_fed
            - final_substrate_mass
        )

    # ---------------------------------------------------------------
    # Yields
    # ---------------------------------------------------------------

    biomass_yield = None
    product_yield = None

    if substrate_consumed is not None:
        biomass_yield = _safe_divide(
            biomass_formed,
            substrate_consumed,
        )

        product_yield = _safe_divide(
            product_formed,
            substrate_consumed,
        )

    # ---------------------------------------------------------------
    # Productivity
    # ---------------------------------------------------------------

    biomass_productivity = _safe_divide(
        biomass_formed,
        duration,
    )

    product_productivity = _safe_divide(
        product_formed,
        duration,
    )

    # Volumetric productivity is expressed as
    # g/L/h using the initial working volume.
    product_productivity_g_L_h = _safe_divide(
        product_formed,
        initial_volume * duration,
    )

    biomass_productivity_g_L_h = _safe_divide(
        biomass_formed,
        initial_volume * duration,
    )

    # ---------------------------------------------------------------
    # Dilution rate
    # ---------------------------------------------------------------

    dilution_rate = None

    if feed_rate is not None:
        dilution_rate = _safe_divide(
            float(feed_rate),
            initial_volume,
        )

    # ---------------------------------------------------------------
    # Volume balance
    # ---------------------------------------------------------------

    expected_feed_volume = None

    if feed_rate is not None:
        expected_feed_volume = (
            float(feed_rate)
            * duration
        )

    volume_balance_error = None

    if expected_feed_volume is not None:
        volume_balance_error = (
            final_volume
            - initial_volume
            - expected_feed_volume
        )

    if volume_balance_error is not None:
        volume_balance_status = (
            "pass"
            if abs(volume_balance_error) < 1e-6
            else "check"
        )
    else:
        volume_balance_status = (
            "not_available"
        )

    # ---------------------------------------------------------------
    # Warnings
    # ---------------------------------------------------------------

    warnings: list[str] = []

    if feed_rate is None:
        warnings.append(
            "Feed rate was not available in the model inputs."
        )

    if feed_substrate is None:
        warnings.append(
            "Feed substrate concentration was not available "
            "in the model inputs."
        )

    if duration <= 0:
        warnings.append(
            "Simulation duration is zero or negative."
        )

    return EngineeringAnalysis(
        status="complete",

        duration_h=duration,

        initial_volume_L=initial_volume,
        final_volume_L=final_volume,
        feed_volume_L=feed_volume,

        initial_biomass_g_L=initial_biomass,
        final_biomass_g_L=final_biomass,

        initial_biomass_mass_g=initial_biomass_mass,
        final_biomass_mass_g=final_biomass_mass,

        biomass_formed_g=biomass_formed,

        initial_substrate_g_L=initial_substrate,
        final_substrate_g_L=final_substrate,

        initial_substrate_mass_g=initial_substrate_mass,
        final_substrate_mass_g=final_substrate_mass,

        substrate_fed_g=substrate_fed,
        substrate_consumed_g=substrate_consumed,

        initial_product_g_L=initial_product,
        final_product_g_L=final_product,

        initial_product_mass_g=initial_product_mass,
        final_product_mass_g=final_product_mass,

        product_formed_g=product_formed,

        biomass_yield_g_g=biomass_yield,
        product_yield_g_g=product_yield,

        biomass_productivity_g_L_h=(
            biomass_productivity_g_L_h
        ),

        product_productivity_g_L_h=(
            product_productivity_g_L_h
        ),

        feed_rate_L_h=(
            float(feed_rate)
            if feed_rate is not None
            else None
        ),

        feed_substrate_g_L=(
            float(feed_substrate)
            if feed_substrate is not None
            else None
        ),

        dilution_rate_1_h=dilution_rate,

        expected_feed_volume_L=(
            expected_feed_volume
        ),

        volume_balance_error_L=(
            volume_balance_error
        ),

        volume_balance_status=(
            volume_balance_status
        ),

        warnings=warnings,
    )