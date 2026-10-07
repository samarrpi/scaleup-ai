from __future__ import annotations

from typing import Any


def _ratio_status(ratio: float | None, tolerance: float) -> str:
    if ratio is None:
        return "not_evaluated"
    return "meets_basis" if abs(ratio - 1.0) <= tolerance else "deviates_from_basis"


def _deviation_percent(ratio: float | None) -> float | None:
    if ratio is None:
        return None
    return (ratio - 1.0) * 100.0


def _fmt(value: float | None, unit: str = "") -> str:
    if value is None:
        return "Not evaluated"
    return f"{value:.6g}{(' ' + unit) if unit else ''}"


def assess_integrated_scale_up(
    *,
    scaleup_result: dict[str, Any],
    engineering_result: dict[str, Any],
    model_result: Any | None = None,
    p_over_v_tolerance: float = 0.10,
    tip_speed_tolerance: float = 0.10,
    vvm_tolerance: float = 0.10,
    kla_tolerance: float = 0.10,
    max_target_feed_rate_L_h: float | None = None,
    max_biomass_g_L: float | None = None,
) -> dict[str, Any]:
    """Integrate Phase 1 + Phase 2 outputs into an engineering screening assessment.

    This is an assessment layer, not equipment approval or process validation. It
    reports whether selected scale-up criteria are met, deviate from their stated
    basis, or cannot be evaluated from the available data.
    """

    if p_over_v_tolerance < 0 or tip_speed_tolerance < 0 or vvm_tolerance < 0 or kla_tolerance < 0:
        raise ValueError("Assessment tolerances must be >= 0.")

    checks = engineering_result.get("checks", {})
    power = engineering_result.get("power", {})
    tip = engineering_result.get("tip_speed", {})
    aeration = engineering_result.get("aeration", {})
    oxygen = engineering_result.get("oxygen", {})
    heat = engineering_result.get("heat", {})

    criteria: list[dict[str, Any]] = []

    def add_ratio_criterion(name: str, lab: float | None, target: float | None, ratio: float | None, basis: str, tolerance: float, unit: str):
        criteria.append(
            {
                "criterion": name,
                "category": "engineering_check",
                "laboratory": lab,
                "target": target,
                "ratio": ratio,
                "deviation_percent": _deviation_percent(ratio),
                "unit": unit,
                "basis": basis,
                "tolerance_percent": tolerance * 100.0,
                "status": _ratio_status(ratio, tolerance),
            }
        )

    add_ratio_criterion(
        "Power per volume",
        power.get("lab_W_m3"),
        power.get("target_W_m3"),
        power.get("ratio"),
        "Selected Phase 2 mixing basis",
        p_over_v_tolerance,
        "W/m³",
    )
    add_ratio_criterion(
        "Impeller tip speed",
        tip.get("lab_m_s"),
        tip.get("target_m_s"),
        tip.get("ratio"),
        "Selected Phase 2 mixing basis",
        tip_speed_tolerance,
        "m/s",
    )
    add_ratio_criterion(
        "Aeration (vvm)",
        aeration.get("lab_vvm"),
        aeration.get("target_vvm"),
        aeration.get("ratio"),
        "Selected Phase 2 aeration basis",
        vvm_tolerance,
        "vvm",
    )
    add_ratio_criterion(
        "kLa",
        oxygen.get("lab_kla_1_h"),
        oxygen.get("target_kla_1_h"),
        oxygen.get("kla_ratio"),
        "Supplied/measured kLa comparison",
        kla_tolerance,
        "1/h",
    )

    # Geometry is already assessed by Phase 2; carry it into the integrated view.
    criteria.append(
        {
            "criterion": "Reactor geometry",
            "category": "engineering_check",
            "laboratory": None,
            "target": None,
            "ratio": None,
            "deviation_percent": None,
            "unit": "",
            "basis": "Geometric similarity / supplied geometry",
            "tolerance_percent": 10.0,
            "status": checks.get("reactor_geometry", "not_evaluated"),
        }
    )

    # Vessel capacity comes from Phase 1.
    capacity_status = scaleup_result.get("vessel_capacity_status", "not_evaluated")
    criteria.append(
        {
            "criterion": "Vessel capacity",
            "category": "constraint",
            "laboratory": None,
            "target": scaleup_result.get("expected_final_volume_L"),
            "ratio": None,
            "deviation_percent": None,
            "unit": "L",
            "basis": "Expected final volume vs stated maximum working volume",
            "tolerance_percent": None,
            "status": {
                "pass": "meets_constraint",
                "check": "exceeds_constraint",
            }.get(capacity_status, "not_evaluated"),
        }
    )

    # Oxygen transfer is separated into the physical transfer calculation (OTR)
    # and the biological demand calculation (OUR). When both are available,
    # Phase 3 can expose the capacity margin without treating it as final design approval.
    otr = oxygen.get("target_otr_g_L_h")
    oxygen_demand = engineering_result.get("oxygen_demand", {})
    peak_our = oxygen_demand.get("target_peak_our_g_L_h")
    oxygen_capacity_ratio = oxygen_demand.get("transfer_capacity_ratio")
    if oxygen_demand.get("status") in {
        "screening_capacity_available",
        "screening_capacity_exceeded",
        "duty_calculated_capacity_not_available",
    }:
        oxygen_status = oxygen_demand.get("status")
    elif peak_our is not None:
        oxygen_status = "our_calculated_otr_not_available"
    elif otr is not None:
        oxygen_status = "otr_calculated_our_not_evaluated"
    else:
        oxygen_status = "not_evaluated"
    criteria.append(
        {
            "criterion": "Oxygen transfer",
            "category": "engineering_check",
            "laboratory": None,
            "target": peak_our,
            "ratio": oxygen_capacity_ratio,
            "deviation_percent": None,
            "unit": "g/L/h",
            "basis": "OTR = kLa × (C* − CL) compared with OUR = qO2 × X; concentration-preserving target screening basis",
            "tolerance_percent": None,
            "status": oxygen_status,
        }
    )

    heat_status = heat.get("status", "not_evaluated")
    criteria.append(
        {
            "criterion": "Heat-transfer capacity",
            "category": "engineering_check",
            "laboratory": None,
            "target": heat.get("target_heat_capacity_W"),
            "ratio": heat.get("capacity_to_duty_ratio"),
            "deviation_percent": None,
            "unit": "W",
            "basis": "Q = U × A × ΔT compared with stated heat duty",
            "tolerance_percent": None,
            "status": heat_status,
        }
    )

    # Optional target feed-rate constraint. The ratio is constraint utilisation,
    # not a laboratory-to-target scale-up ratio.
    feed_constraint_status = "not_evaluated"
    target_feed = scaleup_result.get("scaled_feed_rate_L_h")
    feed_utilisation = None
    if max_target_feed_rate_L_h is not None and max_target_feed_rate_L_h > 0 and target_feed is not None:
        feed_utilisation = target_feed / max_target_feed_rate_L_h
        if feed_utilisation > 1.0:
            feed_constraint_status = "exceeds_constraint"
        elif abs(feed_utilisation - 1.0) <= 1e-9:
            feed_constraint_status = "at_constraint"
        else:
            feed_constraint_status = "within_constraint"
    criteria.append(
        {
            "criterion": "Target feed-rate constraint",
            "category": "constraint",
            "laboratory": None,
            "target": target_feed,
            "ratio": feed_utilisation,
            "utilisation_percent": (feed_utilisation * 100.0) if feed_utilisation is not None else None,
            "deviation_percent": None,
            "unit": "L/h",
            "basis": "Scaled target feed rate vs optional maximum target feed rate",
            "limit": max_target_feed_rate_L_h,
            "tolerance_percent": None,
            "status": feed_constraint_status,
        }
    )

    # Optional biomass concentration constraint. The current E. coli model is a
    # concentration model; under first-pass concentration-preserving scaling the
    # same concentration trajectory is the screening reference for the target scale.
    biomass_constraint_status = "not_evaluated"
    max_biomass = None
    if model_result is not None:
        predictions = getattr(model_result, "predictions", {}) or {}
        biomass_values = predictions.get("biomass_g_L", [])
        if biomass_values:
            max_biomass = max(float(value) for value in biomass_values)
    biomass_utilisation = None
    if max_biomass_g_L is not None and max_biomass_g_L > 0 and max_biomass is not None:
        biomass_utilisation = max_biomass / max_biomass_g_L
        if biomass_utilisation > 1.0:
            biomass_constraint_status = "exceeds_constraint"
        elif abs(biomass_utilisation - 1.0) <= 1e-9:
            biomass_constraint_status = "at_constraint"
        else:
            biomass_constraint_status = "within_constraint"
    criteria.append(
        {
            "criterion": "Maximum biomass concentration",
            "category": "constraint",
            "laboratory": max_biomass,
            "target": max_biomass,
            "ratio": biomass_utilisation,
            "utilisation_percent": (biomass_utilisation * 100.0) if biomass_utilisation is not None else None,
            "deviation_percent": None,
            "unit": "g/L",
            "basis": "Current E. coli concentration trajectory vs optional maximum biomass constraint",
            "limit": max_biomass_g_L,
            "tolerance_percent": None,
            "status": biomass_constraint_status,
        }
    )

    engineering_statuses = {
        "meets_basis",
        "deviates_from_basis",
        "screened_match",
        "different",
        "capacity_available",
        "capacity_check",
        "otr_calculated_our_not_evaluated",
        "screening_capacity_available",
        "screening_capacity_exceeded",
    }
    constraint_statuses = {
        "meets_constraint",
        "within_constraint",
        "at_constraint",
        "exceeds_constraint",
    }
    evaluated = [item for item in criteria if item["status"] in engineering_statuses or item["status"] in constraint_statuses]
    engineering_evaluated = [item for item in criteria if item.get("category") == "engineering_check" and item["status"] in engineering_statuses]
    constraints_evaluated = [item for item in criteria if item.get("category") == "constraint" and item["status"] in constraint_statuses]
    deviations = [item for item in criteria if item["status"] in {"deviates_from_basis", "different", "exceeds_constraint", "capacity_check"}]
    unresolved = [item for item in criteria if item["status"] in {"not_evaluated", "otr_calculated_our_not_evaluated"}]

    scale_factor = scaleup_result.get("scale_factor")
    large_scale = bool(scaleup_result.get("large_scale_factor_flag"))

    limitations = [
        "This is an engineering screening assessment, not final equipment design or process validation.",
        "The assessment is only as complete as the equipment/process data supplied to Phase 2.",
    ]
    if large_scale:
        limitations.append(
            f"The scale transition is {float(scale_factor):.4g}×; volumetric scaling alone does not establish engineering equivalence."
        )
    if checks.get("reactor_geometry") in {"not_evaluated", "different"}:
        limitations.append("Reactor geometry is missing or differs from the selected geometric basis.")
    if oxygen_status == "otr_calculated_our_not_evaluated":
        limitations.append("OTR was calculated, but oxygen uptake rate (OUR) is not evaluated because a process-specific qO2 basis is unavailable.")
    if oxygen_status == "our_calculated_otr_not_available":
        limitations.append("OUR was calculated, but target OTR is unavailable because the required oxygen-transfer inputs are incomplete.")
    if oxygen_status == "screening_capacity_exceeded":
        limitations.append("Calculated peak OUR exceeds the supplied target OTR on the stated screening basis; this flags an oxygen-transfer constraint for engineering review, not a final process failure determination.")
    if heat_status == "not_evaluated":
        limitations.append("Thermal generation/removal could not be assessed because a heat-duty basis and/or heat-transfer inputs were unavailable.")
    if heat_status == "duty_calculated_capacity_not_available":
        limitations.append("A target heat duty was calculated from the oxygen-demand/heat-release basis, but heat-removal capacity could not be assessed because U, area and ΔT were incomplete.")
    if heat_status == "capacity_check":
        limitations.append("The stated/calculated target heat duty exceeds the supplied U·A·ΔT screening capacity; this flags a thermal constraint for engineering review, not a final process failure determination.")

    requirement_map = {
        "Power per volume": "Laboratory/target agitation, impeller geometry, power number and fluid density.",
        "Impeller tip speed": "Laboratory/target impeller diameter and agitation speed.",
        "Aeration (vvm)": "Laboratory gas flow and working volume, plus a selected aeration basis.",
        "kLa": "Measured/supplied laboratory and target kLa, or a documented kLa correlation basis.",
        "Reactor geometry": "Measured vessel/impeller geometry or confirmed geometric-similarity assumptions.",
        "Vessel capacity": "Maximum allowable working volume of the target vessel.",
        "Oxygen transfer": "Target kLa, C*, CL, plus process-specific qO2 and the scientific biomass trajectory.",
        "Heat-transfer capacity": "Process-specific heat-release basis or total heat duty, plus heat-transfer coefficient, effective area and temperature driving force.",
    }
    data_requirements = [
        {"criterion": item["criterion"], "required_data": requirement_map[item["criterion"]]}
        for item in unresolved
        if item["criterion"] in requirement_map
    ]

    data_completeness = {
        "criteria_total": len(criteria),
        "engineering_checks_evaluated": len(engineering_evaluated),
        "constraints_evaluated": len(constraints_evaluated),
        "criteria_evaluated": len(evaluated),
        "criteria_unresolved": len(unresolved),
        "criteria_with_deviation_or_constraint_issue": len(deviations),
    }

    return {
        "assessment_type": "Integrated engineering scale-up screening",
        "scale_up_basis": scaleup_result.get("scale_up_basis", ""),
        "scale_factor": scale_factor,
        "large_scale_transition": large_scale,
        "criteria": criteria,
        "data_completeness": data_completeness,
        "deviations": deviations,
        "unresolved": unresolved,
        "data_requirements": data_requirements,
        "limitations": limitations,
        "tolerances": {
            "P_over_V": p_over_v_tolerance,
            "tip_speed": tip_speed_tolerance,
            "vvm": vvm_tolerance,
            "kLa": kla_tolerance,
        },
        "summary": {
            "evaluated": len(evaluated),
            "engineering_checks_evaluated": len(engineering_evaluated),
            "constraints_evaluated": len(constraints_evaluated),
            "unresolved": len(unresolved),
            "deviations": len(deviations),
            "large_scale_transition": large_scale,
        },
    }
