from __future__ import annotations

from typing import Any


DEFAULT_LARGE_SCALE_FACTOR_THRESHOLD = 100.0


def calculate_first_pass_scale_up(
    lab_volume_L: float,
    target_volume_L: float,
    initial_biomass_g_L: float,
    initial_substrate_g_L: float,
    initial_product_g_L: float,
    feed_rate_L_h: float,
    feed_substrate_g_L: float,
    duration_h: float,
    max_working_volume_L: float | None = None,
    scale_up_basis: str = "Constant concentration and volumetric feed rate",
    large_scale_factor_threshold: float = DEFAULT_LARGE_SCALE_FACTOR_THRESHOLD,
) -> dict[str, Any]:
    """Perform a first-pass volumetric scale-up screening calculation.

    The implemented basis preserves initial concentrations and scales the
    laboratory volumetric feed rate in proportion to working volume. This is
    a screening calculation, not final equipment design. Mixing, oxygen
    transfer, heat transfer, power input, geometry and gas-transfer effects
    are deliberately not modelled here.

    ``max_working_volume_L`` is optional. If omitted/zero, vessel-capacity
    status is reported as ``not_evaluated`` rather than assumed.
    """

    values = {
        "lab_volume_L": lab_volume_L,
        "target_volume_L": target_volume_L,
        "initial_biomass_g_L": initial_biomass_g_L,
        "initial_substrate_g_L": initial_substrate_g_L,
        "initial_product_g_L": initial_product_g_L,
        "feed_rate_L_h": feed_rate_L_h,
        "feed_substrate_g_L": feed_substrate_g_L,
        "duration_h": duration_h,
    }

    for name, value in values.items():
        if value is None:
            raise ValueError(f"{name} is required.")
        if value < 0:
            raise ValueError(f"{name} must be >= 0.")

    if lab_volume_L <= 0:
        raise ValueError("lab_volume_L must be > 0.")
    if target_volume_L <= 0:
        raise ValueError("target_volume_L must be > 0.")
    if duration_h <= 0:
        raise ValueError("duration_h must be > 0.")
    if max_working_volume_L is not None and max_working_volume_L < 0:
        raise ValueError("max_working_volume_L must be >= 0 when provided.")
    if large_scale_factor_threshold <= 0:
        raise ValueError("large_scale_factor_threshold must be > 0.")

    scale_factor = target_volume_L / lab_volume_L
    scaled_feed_rate = feed_rate_L_h * scale_factor

    scaled_initial_biomass_mass = initial_biomass_g_L * target_volume_L
    scaled_initial_substrate_mass = initial_substrate_g_L * target_volume_L
    scaled_initial_product_mass = initial_product_g_L * target_volume_L

    scaled_feed_volume = scaled_feed_rate * duration_h
    scaled_substrate_feed_mass = scaled_feed_volume * feed_substrate_g_L
    expected_final_volume = target_volume_L + scaled_feed_volume

    if max_working_volume_L and max_working_volume_L > 0:
        if expected_final_volume <= max_working_volume_L:
            vessel_capacity_status = "pass"
            vessel_capacity_message = (
                "Expected final volume is within the stated maximum working volume."
            )
        else:
            vessel_capacity_status = "check"
            vessel_capacity_message = (
                "Expected final volume exceeds the stated maximum working volume."
            )
    else:
        vessel_capacity_status = "not_evaluated"
        vessel_capacity_message = (
            "Maximum working volume was not provided; vessel capacity was not evaluated."
        )

    warnings = [
        "First-pass volumetric scaling only; this is not final equipment design.",
        "Mixing equivalence has not been evaluated.",
        "Oxygen-transfer equivalence has not been evaluated.",
        "Heat-transfer capacity has not been evaluated.",
        "Power input, reactor geometry and gas-transfer effects have not been evaluated.",
        "Final equipment design requires scale-dependent engineering analysis and validation.",
    ]

    if scale_factor > large_scale_factor_threshold:
        warnings.insert(1,
            f"Large scale transition flagged: {scale_factor:.4g}x exceeds the "
            f"screening threshold of {large_scale_factor_threshold:.4g}x."
        )

    if vessel_capacity_status == "check":
        warnings.insert(1, vessel_capacity_message)

    return {
        "scale_up_basis": scale_up_basis,
        "lab_volume_L": lab_volume_L,
        "target_volume_L": target_volume_L,
        "max_working_volume_L": max_working_volume_L,
        "scale_factor": scale_factor,
        "large_scale_factor_threshold": large_scale_factor_threshold,
        "large_scale_factor_flag": scale_factor > large_scale_factor_threshold,
        "initial_biomass_g_L": initial_biomass_g_L,
        "initial_substrate_g_L": initial_substrate_g_L,
        "initial_product_g_L": initial_product_g_L,
        "feed_rate_L_h": feed_rate_L_h,
        "scaled_feed_rate_L_h": scaled_feed_rate,
        "feed_substrate_g_L": feed_substrate_g_L,
        "duration_h": duration_h,
        "scaled_initial_biomass_mass_g": scaled_initial_biomass_mass,
        "scaled_initial_substrate_mass_g": scaled_initial_substrate_mass,
        "scaled_initial_product_mass_g": scaled_initial_product_mass,
        "scaled_feed_volume_L": scaled_feed_volume,
        "scaled_substrate_feed_mass_g": scaled_substrate_feed_mass,
        "expected_final_volume_L": expected_final_volume,
        "preserved_concentrations": True,
        "vessel_capacity_status": vessel_capacity_status,
        "vessel_capacity_message": vessel_capacity_message,
        "engineering_checks": {
            "material_balance": "screened",
            "vessel_capacity": vessel_capacity_status,
            "mixing": "not_evaluated",
            "oxygen_transfer": "not_evaluated",
            "heat_transfer": "not_evaluated",
            "power_input": "not_evaluated",
            "reactor_geometry": "not_evaluated",
            "gas_transfer": "not_evaluated",
        },
        "warnings": warnings,
    }
