from __future__ import annotations

from math import pi
from typing import Any


def _positive_or_none(value: float | None) -> float | None:
    if value is None or value <= 0:
        return None
    return float(value)


def _ratio(target: float | None, lab: float | None) -> float | None:
    if target is None or lab is None or lab <= 0:
        return None
    return target / lab


def _status_from_ratio(ratio: float | None, tolerance: float = 0.10) -> str:
    if ratio is None:
        return "not_evaluated"
    if abs(ratio - 1.0) <= tolerance:
        return "screened_match"
    return "different"


def calculate_engineering_scale_up(
    *,
    lab_volume_L: float,
    target_volume_L: float,
    lab_vessel_diameter_m: float | None = None,
    target_vessel_diameter_m: float | None = None,
    lab_liquid_height_m: float | None = None,
    target_liquid_height_m: float | None = None,
    lab_impeller_diameter_m: float | None = None,
    target_impeller_diameter_m: float | None = None,
    lab_agitation_rpm: float | None = None,
    target_agitation_rpm: float | None = None,
    lab_power_number: float | None = None,
    target_power_number: float | None = None,
    fluid_density_kg_m3: float = 1000.0,
    lab_viscosity_Pa_s: float | None = None,
    target_viscosity_Pa_s: float | None = None,
    lab_mixing_time_s: float | None = None,
    lab_gas_flow_L_min: float | None = None,
    target_gas_flow_L_min: float | None = None,
    lab_kla_1_h: float | None = None,
    target_kla_1_h: float | None = None,
    target_cstar_g_L: float | None = None,
    target_do_g_L: float | None = None,
    target_heat_duty_W: float | None = None,
    target_overall_heat_transfer_U_W_m2K: float | None = None,
    target_heat_transfer_area_m2: float | None = None,
    target_delta_T_K: float | None = None,
    heat_release_kJ_per_gO2: float | None = None,
    additional_heat_load_W: float | None = None,
    qO2_g_gX_h: float | None = None,
    biomass_trajectory_g_L: list[float] | None = None,
    trajectory_time_h: list[float] | None = None,
) -> dict[str, Any]:
    """Calculate engineering scale-up screening metrics from supplied and calculated data.

    Geometry and operating values may be calculated upstream from explicit scale-up
    assumptions. This function never silently invents equipment-specific properties
    such as power number, kLa, heat-transfer coefficients, or oxygen-transfer data.

    Implemented screening calculations:
    - geometric ratios and H/T, D/T where dimensions are supplied
    - impeller tip speed
    - stirred-tank power and P/V using P = Np*rho*N^3*D^5
    - gas flow as vvm
    - kLa comparison when lab/target kLa are supplied
    - target OTR when kLa, C* and DO are supplied
    - biological oxygen demand OUR = qO2*X when qO2 and a biomass trajectory are supplied
    - target oxygen-transfer capacity margin and critical biomass concentration when OTR and OUR are both available
    - target heat-removal capacity U*A*DeltaT when supplied
    """

    if lab_volume_L <= 0 or target_volume_L <= 0:
        raise ValueError("lab_volume_L and target_volume_L must be > 0.")
    if fluid_density_kg_m3 <= 0:
        raise ValueError("fluid_density_kg_m3 must be > 0.")

    positive_inputs = {
        "lab_vessel_diameter_m": lab_vessel_diameter_m,
        "target_vessel_diameter_m": target_vessel_diameter_m,
        "lab_liquid_height_m": lab_liquid_height_m,
        "target_liquid_height_m": target_liquid_height_m,
        "lab_impeller_diameter_m": lab_impeller_diameter_m,
        "target_impeller_diameter_m": target_impeller_diameter_m,
        "lab_agitation_rpm": lab_agitation_rpm,
        "target_agitation_rpm": target_agitation_rpm,
        "lab_power_number": lab_power_number,
        "lab_viscosity_Pa_s": lab_viscosity_Pa_s,
        "target_viscosity_Pa_s": target_viscosity_Pa_s,
        "lab_mixing_time_s": lab_mixing_time_s,
        "target_power_number": target_power_number,
        "lab_gas_flow_L_min": lab_gas_flow_L_min,
        "target_gas_flow_L_min": target_gas_flow_L_min,
        "lab_kla_1_h": lab_kla_1_h,
        "target_kla_1_h": target_kla_1_h,
        "target_cstar_g_L": target_cstar_g_L,
        "target_do_g_L": target_do_g_L,
        "target_heat_duty_W": target_heat_duty_W,
        "target_overall_heat_transfer_U_W_m2K": target_overall_heat_transfer_U_W_m2K,
        "target_heat_transfer_area_m2": target_heat_transfer_area_m2,
        "target_delta_T_K": target_delta_T_K,
        "heat_release_kJ_per_gO2": heat_release_kJ_per_gO2,
        "additional_heat_load_W": additional_heat_load_W,
        "qO2_g_gX_h": qO2_g_gX_h,
    }
    for name, value in positive_inputs.items():
        if value is not None and value < 0:
            raise ValueError(f"{name} must be >= 0 when provided.")

    lab_volume_m3 = lab_volume_L / 1000.0
    target_volume_m3 = target_volume_L / 1000.0

    # Geometry
    lab_ht_ratio = None
    target_ht_ratio = None
    if lab_vessel_diameter_m and lab_liquid_height_m:
        lab_ht_ratio = lab_liquid_height_m / lab_vessel_diameter_m
    if target_vessel_diameter_m and target_liquid_height_m:
        target_ht_ratio = target_liquid_height_m / target_vessel_diameter_m

    lab_impeller_to_tank = None
    target_impeller_to_tank = None
    if lab_impeller_diameter_m and lab_vessel_diameter_m:
        lab_impeller_to_tank = lab_impeller_diameter_m / lab_vessel_diameter_m
    if target_impeller_diameter_m and target_vessel_diameter_m:
        target_impeller_to_tank = target_impeller_diameter_m / target_vessel_diameter_m

    geometry_ratios = {
        "vessel_diameter_ratio": _ratio(target_vessel_diameter_m, lab_vessel_diameter_m),
        "liquid_height_ratio": _ratio(target_liquid_height_m, lab_liquid_height_m),
        "impeller_diameter_ratio": _ratio(target_impeller_diameter_m, lab_impeller_diameter_m),
        "H_over_T_lab": lab_ht_ratio,
        "H_over_T_target": target_ht_ratio,
        "D_over_T_lab": lab_impeller_to_tank,
        "D_over_T_target": target_impeller_to_tank,
    }

    geometry_status = "not_evaluated"
    if all(
        value is not None
        for value in (
            geometry_ratios["H_over_T_lab"],
            geometry_ratios["H_over_T_target"],
            geometry_ratios["D_over_T_lab"],
            geometry_ratios["D_over_T_target"],
        )
    ):
        geometry_status = "screened_match" if (
            abs(geometry_ratios["H_over_T_target"] - geometry_ratios["H_over_T_lab"]) <= 0.10
            and abs(geometry_ratios["D_over_T_target"] - geometry_ratios["D_over_T_lab"]) <= 0.10
        ) else "different"

    # Tip speed u_tip = pi * D * N, N in rev/s.
    lab_tip_speed_m_s = None
    target_tip_speed_m_s = None
    if lab_impeller_diameter_m and lab_agitation_rpm:
        lab_tip_speed_m_s = pi * lab_impeller_diameter_m * lab_agitation_rpm / 60.0
    if target_impeller_diameter_m and target_agitation_rpm:
        target_tip_speed_m_s = pi * target_impeller_diameter_m * target_agitation_rpm / 60.0
    tip_speed_ratio = _ratio(target_tip_speed_m_s, lab_tip_speed_m_s)

    # Dimensionless mixing groups used in similarity analysis.
    # Re_i = rho*N*D^2/mu and Fr = N^2*D/g, with N in rev/s.
    lab_reynolds = None
    target_reynolds = None
    if lab_impeller_diameter_m and lab_agitation_rpm and lab_viscosity_Pa_s and lab_viscosity_Pa_s > 0:
        lab_reynolds = fluid_density_kg_m3 * (lab_agitation_rpm / 60.0) * lab_impeller_diameter_m**2 / lab_viscosity_Pa_s
    if target_impeller_diameter_m and target_agitation_rpm and target_viscosity_Pa_s and target_viscosity_Pa_s > 0:
        target_reynolds = fluid_density_kg_m3 * (target_agitation_rpm / 60.0) * target_impeller_diameter_m**2 / target_viscosity_Pa_s
    reynolds_ratio = _ratio(target_reynolds, lab_reynolds)

    gravity = 9.80665
    lab_froude = None
    target_froude = None
    if lab_impeller_diameter_m and lab_agitation_rpm:
        lab_froude = (lab_agitation_rpm / 60.0)**2 * lab_impeller_diameter_m / gravity
    if target_impeller_diameter_m and target_agitation_rpm:
        target_froude = (target_agitation_rpm / 60.0)**2 * target_impeller_diameter_m / gravity
    froude_ratio = _ratio(target_froude, lab_froude)

    # Compare classical similarity criteria without silently selecting one.
    # For constant P/V, the geometric/turbulent screening relation is N2/N1=(D1/D2)^(2/3)
    # when density and power number are unchanged. Constant-Re includes viscosity and density.
    criteria_comparison: dict[str, Any] = {}
    if lab_agitation_rpm and lab_impeller_diameter_m and target_impeller_diameter_m:
        d_ratio = lab_impeller_diameter_m / target_impeller_diameter_m
        criteria_comparison["constant_tip_speed"] = lab_agitation_rpm * d_ratio
        criteria_comparison["constant_P_over_V"] = lab_agitation_rpm * d_ratio ** (2.0 / 3.0)
        criteria_comparison["constant_Re"] = None
        if lab_viscosity_Pa_s and target_viscosity_Pa_s and lab_viscosity_Pa_s > 0 and target_viscosity_Pa_s > 0:
            density_ratio = fluid_density_kg_m3 / fluid_density_kg_m3
            criteria_comparison["constant_Re"] = lab_agitation_rpm * d_ratio**2 * (target_viscosity_Pa_s / lab_viscosity_Pa_s) * density_ratio
        criteria_comparison["constant_Fr"] = lab_agitation_rpm * d_ratio ** 0.5
        if lab_mixing_time_s and lab_mixing_time_s > 0:
            criteria_comparison["constant_dimensionless_mixing_time"] = lab_mixing_time_s
        else:
            criteria_comparison["constant_dimensionless_mixing_time"] = None
    else:
        criteria_comparison = {
            "constant_tip_speed": None,
            "constant_P_over_V": None,
            "constant_Re": None,
            "constant_Fr": None,
            "constant_dimensionless_mixing_time": None,
        }

    predicted_mixing_time_s = None
    if lab_mixing_time_s and lab_mixing_time_s > 0 and lab_agitation_rpm and target_agitation_rpm and target_agitation_rpm > 0:
        # Screening estimate from constant dimensionless mixing time (N*t_m constant).
        predicted_mixing_time_s = lab_mixing_time_s * (lab_agitation_rpm / target_agitation_rpm)

    # Stirred-tank power: P = Np * rho * N^3 * D^5.
    def stirred_power_w(np_: float | None, rpm: float | None, diameter_m: float | None) -> float | None:
        if not all(value is not None and value > 0 for value in (np_, rpm, diameter_m)):
            return None
        rev_s = rpm / 60.0
        return np_ * fluid_density_kg_m3 * rev_s**3 * diameter_m**5

    lab_power_W = stirred_power_w(lab_power_number, lab_agitation_rpm, lab_impeller_diameter_m)
    target_power_W = stirred_power_w(target_power_number, target_agitation_rpm, target_impeller_diameter_m)
    lab_power_density_W_m3 = lab_power_W / lab_volume_m3 if lab_power_W is not None else None
    target_power_density_W_m3 = target_power_W / target_volume_m3 if target_power_W is not None else None
    power_density_ratio = _ratio(target_power_density_W_m3, lab_power_density_W_m3)

    # Aeration: vvm = gas flow (L/min) / working volume (L).
    lab_vvm = lab_gas_flow_L_min / lab_volume_L if lab_gas_flow_L_min is not None else None
    target_vvm = target_gas_flow_L_min / target_volume_L if target_gas_flow_L_min is not None else None
    vvm_ratio = _ratio(target_vvm, lab_vvm)

    # kLa comparison and target OTR = kLa * (C* - CL).
    kla_ratio = _ratio(target_kla_1_h, lab_kla_1_h)
    target_otr_g_L_h = None
    if all(value is not None for value in (target_kla_1_h, target_cstar_g_L, target_do_g_L)):
        driving_force = target_cstar_g_L - target_do_g_L
        target_otr_g_L_h = target_kla_1_h * max(driving_force, 0.0)

    # Oxygen demand: OUR = qO2 * X.
    # The current E. coli model is concentration-based and explicitly assumes
    # no oxygen limitation. Therefore this is a post-processing demand check:
    # under concentration-preserving scale-up, the target OUR concentration
    # follows the laboratory biomass concentration trajectory.
    oxygen_demand: dict[str, Any] = {
        "qO2_g_gX_h": qO2_g_gX_h,
        "lab_peak_our_g_L_h": None,
        "lab_peak_biomass_g_L": None,
        "lab_peak_our_time_h": None,
        "target_peak_our_g_L_h": None,
        "target_peak_our_g_h": None,
        "target_critical_biomass_g_L": None,
        "transfer_capacity_ratio": None,
        "transfer_margin_g_L_h": None,
        "status": "not_evaluated",
        "basis": "OUR = qO2 × X; target concentration trajectory assumed concentration-preserving from the scientific model.",
    }

    if qO2_g_gX_h is not None and qO2_g_gX_h > 0 and biomass_trajectory_g_L:
        biomass = [float(value) for value in biomass_trajectory_g_L]
        peak_index = max(range(len(biomass)), key=biomass.__getitem__)
        peak_biomass = biomass[peak_index]
        peak_our = qO2_g_gX_h * peak_biomass
        peak_time = None
        if trajectory_time_h and len(trajectory_time_h) == len(biomass):
            peak_time = float(trajectory_time_h[peak_index])

        oxygen_demand["lab_peak_biomass_g_L"] = peak_biomass
        oxygen_demand["lab_peak_our_g_L_h"] = peak_our
        oxygen_demand["lab_peak_our_time_h"] = peak_time
        oxygen_demand["target_peak_our_g_L_h"] = peak_our
        oxygen_demand["target_peak_our_g_h"] = peak_our * target_volume_L

        if target_otr_g_L_h is not None:
            oxygen_demand["transfer_capacity_ratio"] = _ratio(target_otr_g_L_h, peak_our)
            oxygen_demand["transfer_margin_g_L_h"] = target_otr_g_L_h - peak_our
            oxygen_demand["target_critical_biomass_g_L"] = target_otr_g_L_h / qO2_g_gX_h
            oxygen_demand["status"] = (
                "screening_capacity_available"
                if target_otr_g_L_h >= peak_our
                else "screening_capacity_exceeded"
            )
        else:
            oxygen_demand["status"] = "our_calculated_otr_not_available"

    # Heat generation and heat-removal capacity.
    # When qO2 and a process-specific heat-release basis are supplied, metabolic
    # heat is calculated from the same peak oxygen-demand basis used above:
    # Q_met = OUR_total * heat_release / 3.6, with kJ/h converted to W.
    metabolic_heat_generation_W = None
    target_metabolic_heat_generation_W = None
    target_total_heat_generation_W = None
    target_heat_duty_basis_W = target_heat_duty_W
    thermal_critical_biomass_g_L = None
    heat_generation_status = "not_evaluated"

    if (
        heat_release_kJ_per_gO2 is not None
        and heat_release_kJ_per_gO2 > 0
        and oxygen_demand.get("target_peak_our_g_h") is not None
    ):
        target_metabolic_heat_generation_W = (
            oxygen_demand["target_peak_our_g_h"]
            * heat_release_kJ_per_gO2
            / 3.6
        )
        metabolic_heat_generation_W = target_metabolic_heat_generation_W
        target_total_heat_generation_W = (
            target_metabolic_heat_generation_W
            + (additional_heat_load_W or 0.0)
        )
        heat_generation_status = "calculated_from_oxygen_demand"
        if target_heat_duty_W is None:
            target_heat_duty_basis_W = target_total_heat_generation_W
    elif additional_heat_load_W is not None and additional_heat_load_W > 0:
        target_total_heat_generation_W = additional_heat_load_W
        heat_generation_status = "additional_load_only"
        if target_heat_duty_W is None:
            target_heat_duty_basis_W = additional_heat_load_W
    elif target_heat_duty_W is not None:
        heat_generation_status = "manual_total_duty_only"

    # Heat-removal capacity Q = U*A*DeltaT.
    target_heat_capacity_W = None
    if all(
        value is not None
        for value in (
            target_overall_heat_transfer_U_W_m2K,
            target_heat_transfer_area_m2,
            target_delta_T_K,
        )
    ):
        target_heat_capacity_W = (
            target_overall_heat_transfer_U_W_m2K
            * target_heat_transfer_area_m2
            * target_delta_T_K
        )

    heat_capacity_ratio = _ratio(target_heat_capacity_W, target_heat_duty_basis_W)
    heat_margin_W = None
    if target_heat_capacity_W is not None and target_heat_duty_basis_W is not None:
        heat_margin_W = target_heat_capacity_W - target_heat_duty_basis_W

    if (
        target_heat_capacity_W is not None
        and target_heat_duty_basis_W is not None
    ):
        heat_status = "capacity_available" if target_heat_capacity_W >= target_heat_duty_basis_W else "capacity_check"
    elif target_heat_duty_basis_W is not None:
        heat_status = "duty_calculated_capacity_not_available"
    else:
        heat_status = "not_evaluated"

    if (
        target_heat_capacity_W is not None
        and additional_heat_load_W is not None
        and qO2_g_gX_h is not None
        and heat_release_kJ_per_gO2 is not None
        and qO2_g_gX_h > 0
        and heat_release_kJ_per_gO2 > 0
    ):
        available_metabolic_heat_W = target_heat_capacity_W - additional_heat_load_W
        if available_metabolic_heat_W > 0:
            watts_per_g_L = qO2_g_gX_h * heat_release_kJ_per_gO2 / 3.6
            thermal_critical_biomass_g_L = available_metabolic_heat_W / (watts_per_g_L * target_volume_L)

    checks = {
        "reactor_geometry": geometry_status,
        "tip_speed": _status_from_ratio(tip_speed_ratio),
        "power_per_volume": _status_from_ratio(power_density_ratio),
        "aeration_vvm": _status_from_ratio(vvm_ratio),
        "kla": _status_from_ratio(kla_ratio),
        "oxygen_transfer": "calculated" if target_otr_g_L_h is not None else "not_evaluated",
        "heat_transfer": heat_status,
    }

    return {
        "inputs": {
            "lab_volume_L": lab_volume_L,
            "target_volume_L": target_volume_L,
            "fluid_density_kg_m3": fluid_density_kg_m3,
        },
        "geometry": geometry_ratios,
        "tip_speed": {
            "lab_m_s": lab_tip_speed_m_s,
            "target_m_s": target_tip_speed_m_s,
            "ratio": tip_speed_ratio,
            "status": checks["tip_speed"],
        },
        "similarity": {
            "lab_reynolds": lab_reynolds,
            "target_reynolds": target_reynolds,
            "reynolds_ratio": reynolds_ratio,
            "lab_froude": lab_froude,
            "target_froude": target_froude,
            "froude_ratio": froude_ratio,
            "criteria_comparison_target_rpm": criteria_comparison,
            "predicted_target_mixing_time_s": predicted_mixing_time_s,
        },
        "power": {
            "lab_W": lab_power_W,
            "target_W": target_power_W,
            "lab_W_m3": lab_power_density_W_m3,
            "target_W_m3": target_power_density_W_m3,
            "ratio": power_density_ratio,
            "status": checks["power_per_volume"],
        },
        "aeration": {
            "lab_vvm": lab_vvm,
            "target_vvm": target_vvm,
            "ratio": vvm_ratio,
            "status": checks["aeration_vvm"],
        },
        "oxygen": {
            "lab_kla_1_h": lab_kla_1_h,
            "target_kla_1_h": target_kla_1_h,
            "kla_ratio": kla_ratio,
            "target_cstar_g_L": target_cstar_g_L,
            "target_do_g_L": target_do_g_L,
            "target_otr_g_L_h": target_otr_g_L_h,
            "status": checks["oxygen_transfer"],
        },
        "oxygen_demand": oxygen_demand,
        "heat": {
            "heat_release_kJ_per_gO2": heat_release_kJ_per_gO2,
            "additional_heat_load_W": additional_heat_load_W,
            "metabolic_heat_generation_W": metabolic_heat_generation_W,
            "target_metabolic_heat_generation_W": target_metabolic_heat_generation_W,
            "target_total_heat_generation_W": target_total_heat_generation_W,
            "target_heat_duty_W": target_heat_duty_W,
            "target_heat_duty_basis_W": target_heat_duty_basis_W,
            "target_U_W_m2K": target_overall_heat_transfer_U_W_m2K,
            "target_area_m2": target_heat_transfer_area_m2,
            "target_delta_T_K": target_delta_T_K,
            "target_heat_capacity_W": target_heat_capacity_W,
            "capacity_to_duty_ratio": heat_capacity_ratio,
            "heat_margin_W": heat_margin_W,
            "thermal_critical_biomass_g_L": thermal_critical_biomass_g_L,
            "generation_status": heat_generation_status,
            "status": heat_status,
        },
        "checks": checks,
        "basis": (
            "Engineering screening combines user-supplied equipment/process data with "
            "explicitly calculated geometry and scale-up values. Equipment-specific "
            "properties are not silently inferred."
        ),
        "warnings": [
            "A screened match is not proof of process equivalence.",
            "Geometry may be calculated from explicit H/T and D/T assumptions; calculated geometry is not measured equipment data.",
            "Power calculation uses P = Np*rho*N^3*D^5 and therefore requires an appropriate power number for the impeller/system.",
            "OTR is calculated only when target kLa, oxygen saturation concentration and dissolved-oxygen concentration are supplied.",
            "OUR is calculated only when a specific oxygen uptake rate qO2 and a biomass trajectory are supplied; qO2 is process-specific and must not be guessed.",
            "The OUR-to-OTR comparison is a screening capacity check under the current concentration-preserving scale-up assumption; it does not model dissolved-oxygen dynamics or oxygen-limited kinetics.",
            "Heat generation can be estimated from peak OUR only when a process-specific heat release per oxygen consumed is supplied; ScaleUp AI does not assume a universal metabolic heat constant.",
            "When no manual total heat duty is supplied, the calculated thermal screening duty is metabolic heat plus any stated additional heat load.",
            "Heat-transfer capacity is calculated as U*A*DeltaT only when all three target heat-transfer inputs are supplied.",
            "Reynolds and Froude numbers are similarity diagnostics; Froude effects are especially relevant to free-surface vortexing and unbaffled systems.",
            "Classical mixing scale-up criteria are mutually conflicting; the comparison table shows alternatives rather than declaring a universal best criterion.",
        ],
    }


def suggest_engineering_inputs(
    *,
    lab_volume_L: float,
    target_volume_L: float,
    lab_vessel_diameter_m: float | None = None,
    lab_liquid_height_m: float | None = None,
    lab_impeller_diameter_m: float | None = None,
    lab_agitation_rpm: float | None = None,
    geometry_H_over_T: float = 2.0,
    geometry_D_over_T: float = 1.0 / 3.0,
    mixing_basis: str = "constant_tip_speed",
    lab_gas_flow_L_min: float | None = None,
    aeration_basis: str = "constant_vvm",
) -> dict[str, Any]:
    """Generate editable Phase-2 engineering suggestions from scale and limited lab data.

    Geometry is estimated from working volume only when explicit lab geometry is not
    supplied. The geometric assumptions are returned explicitly so the UI can label
    them as assumptions rather than measured equipment data.

    Agitation and aeration are only propagated when a laboratory value is supplied.
    No equipment-specific power number, kLa, heat-transfer coefficient, or gas-transfer
    correlation is invented here.
    """
    if lab_volume_L <= 0 or target_volume_L <= 0:
        raise ValueError("lab_volume_L and target_volume_L must be > 0.")
    if geometry_H_over_T <= 0 or geometry_D_over_T <= 0:
        raise ValueError("Geometry ratios must be > 0.")

    import math

    def cylinder_geometry(volume_L: float) -> tuple[float, float]:
        volume_m3 = volume_L / 1000.0
        # V = pi/4 * D^2 * H and H = (H/T)*D
        diameter = (4.0 * volume_m3 / (math.pi * geometry_H_over_T)) ** (1.0 / 3.0)
        height = geometry_H_over_T * diameter
        return diameter, height

    if lab_vessel_diameter_m and lab_liquid_height_m:
        lab_D = lab_vessel_diameter_m
        lab_H = lab_liquid_height_m
        geometry_source = "user_provided_lab_geometry"
    else:
        lab_D, lab_H = cylinder_geometry(lab_volume_L)
        geometry_source = "estimated_from_volume_and_H_over_T"

    target_D, target_H = cylinder_geometry(target_volume_L)

    if lab_impeller_diameter_m:
        lab_Di = lab_impeller_diameter_m
        impeller_source = "user_provided_lab_impeller"
    else:
        lab_Di = geometry_D_over_T * lab_D
        impeller_source = "estimated_from_D_over_T"

    target_Di = geometry_D_over_T * target_D

    target_rpm = None
    agitation_source = "not_evaluated"
    if lab_agitation_rpm and lab_agitation_rpm > 0:
        if mixing_basis == "constant_tip_speed":
            target_rpm = lab_agitation_rpm * lab_Di / target_Di
            agitation_source = "calculated_constant_tip_speed"
        elif mixing_basis == "constant_P_over_V":
            # Assuming the same Np and density, solve P/V constant from
            # P/V = Np*rho*N^3*D^5/V.
            target_rpm = lab_agitation_rpm * (
                (lab_Di / target_Di) ** (5.0 / 3.0)
                * (target_volume_L / lab_volume_L) ** (1.0 / 3.0)
            )
            agitation_source = "calculated_constant_P_over_V"
        else:
            raise ValueError(f"Unsupported mixing basis: {mixing_basis}")

    target_gas = None
    aeration_source = "not_evaluated"
    if lab_gas_flow_L_min and lab_gas_flow_L_min > 0:
        if aeration_basis == "constant_vvm":
            lab_vvm = lab_gas_flow_L_min / lab_volume_L
            target_gas = lab_vvm * target_volume_L
            aeration_source = "calculated_constant_vvm"
        else:
            raise ValueError(f"Unsupported aeration basis: {aeration_basis}")

    return {
        "geometry": {
            "lab_vessel_diameter_m": lab_D,
            "target_vessel_diameter_m": target_D,
            "lab_liquid_height_m": lab_H,
            "target_liquid_height_m": target_H,
            "lab_impeller_diameter_m": lab_Di,
            "target_impeller_diameter_m": target_Di,
            "H_over_T": geometry_H_over_T,
            "D_over_T": geometry_D_over_T,
            "source": geometry_source,
            "impeller_source": impeller_source,
        },
        "mixing": {
            "basis": mixing_basis,
            "lab_agitation_rpm": lab_agitation_rpm,
            "target_agitation_rpm": target_rpm,
            "source": agitation_source,
        },
        "aeration": {
            "basis": aeration_basis,
            "lab_gas_flow_L_min": lab_gas_flow_L_min,
            "target_gas_flow_L_min": target_gas,
            "source": aeration_source,
        },
        "assumptions": [
            f"Cylindrical geometry estimated using H/T = {geometry_H_over_T:g}.",
            f"Impeller diameter estimated using D/T = {geometry_D_over_T:g} when lab impeller diameter is not supplied.",
            "Estimated geometry is a screening basis, not measured equipment data.",
        ],
    }
