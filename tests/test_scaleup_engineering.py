import math

from agents.scientific.scaleup_engineering import calculate_engineering_scale_up


def test_tip_speed_and_power_per_volume_are_calculated():
    result = calculate_engineering_scale_up(
        lab_volume_L=2.0,
        target_volume_L=200.0,
        lab_impeller_diameter_m=0.05,
        target_impeller_diameter_m=0.232,
        lab_agitation_rpm=300,
        target_agitation_rpm=300,
        lab_power_number=5.0,
        target_power_number=5.0,
    )

    assert math.isclose(
        result["tip_speed"]["lab_m_s"], math.pi * 0.05 * 300 / 60,
        rel_tol=1e-9,
    )
    assert result["power"]["lab_W"] is not None
    assert result["power"]["target_W"] is not None
    assert result["power"]["lab_W_m3"] is not None
    assert result["power"]["target_W_m3"] is not None


def test_aeration_vvm_and_kla_are_calculated_when_supplied():
    result = calculate_engineering_scale_up(
        lab_volume_L=2.0,
        target_volume_L=200.0,
        lab_gas_flow_L_min=2.0,
        target_gas_flow_L_min=200.0,
        lab_kla_1_h=100.0,
        target_kla_1_h=100.0,
    )

    assert result["aeration"]["lab_vvm"] == 1.0
    assert result["aeration"]["target_vvm"] == 1.0
    assert result["oxygen"]["kla_ratio"] == 1.0
    assert result["oxygen"]["status"] == "not_evaluated"


def test_otr_and_heat_capacity_are_calculated():
    result = calculate_engineering_scale_up(
        lab_volume_L=2.0,
        target_volume_L=200.0,
        target_kla_1_h=100.0,
        target_cstar_g_L=0.008,
        target_do_g_L=0.002,
        target_heat_duty_W=10000.0,
        target_overall_heat_transfer_U_W_m2K=500.0,
        target_heat_transfer_area_m2=30.0,
        target_delta_T_K=10.0,
    )

    assert math.isclose(result["oxygen"]["target_otr_g_L_h"], 0.6)
    assert result["heat"]["target_heat_capacity_W"] == 150000.0
    assert result["heat"]["status"] == "capacity_available"


def test_geometry_ratios_are_reported_without_inventing_missing_values():
    result = calculate_engineering_scale_up(
        lab_volume_L=2.0,
        target_volume_L=200.0,
        lab_vessel_diameter_m=0.12,
        target_vessel_diameter_m=1.2,
        lab_liquid_height_m=0.24,
        target_liquid_height_m=2.4,
        lab_impeller_diameter_m=0.04,
        target_impeller_diameter_m=0.4,
    )

    assert result["geometry"]["vessel_diameter_ratio"] == 10.0
    assert result["geometry"]["liquid_height_ratio"] == 10.0
    assert result["geometry"]["impeller_diameter_ratio"] == 10.0
    assert result["geometry"]["H_over_T_lab"] == 2.0
    assert result["geometry"]["H_over_T_target"] == 2.0
    assert result["checks"]["reactor_geometry"] == "screened_match"


def test_engineering_suggestions_auto_generate_geometry_and_target_agitation():
    from agents.scientific.scaleup_engineering import suggest_engineering_inputs

    suggestion = suggest_engineering_inputs(
        lab_volume_L=2.0,
        target_volume_L=200.0,
        lab_agitation_rpm=300.0,
        geometry_H_over_T=2.0,
        geometry_D_over_T=1.0 / 3.0,
        mixing_basis="constant_tip_speed",
    )

    assert suggestion["geometry"]["lab_vessel_diameter_m"] > 0
    assert suggestion["geometry"]["target_vessel_diameter_m"] > suggestion["geometry"]["lab_vessel_diameter_m"]
    assert suggestion["geometry"]["lab_impeller_diameter_m"] > 0
    assert suggestion["mixing"]["target_agitation_rpm"] > 0
    assert suggestion["mixing"]["source"] == "calculated_constant_tip_speed"


def test_engineering_suggestions_scale_gas_flow_at_constant_vvm():
    from agents.scientific.scaleup_engineering import suggest_engineering_inputs

    suggestion = suggest_engineering_inputs(
        lab_volume_L=2.0,
        target_volume_L=200.0,
        lab_gas_flow_L_min=2.0,
        aeration_basis="constant_vvm",
    )

    assert suggestion["aeration"]["lab_gas_flow_L_min"] == 2.0
    assert suggestion["aeration"]["target_gas_flow_L_min"] == 200.0


def test_similarity_diagnostics_and_classical_criteria_are_calculated():
    from agents.scientific.scaleup_engineering import calculate_engineering_scale_up

    result = calculate_engineering_scale_up(
        lab_volume_L=2.0,
        target_volume_L=2000.0,
        lab_impeller_diameter_m=0.05,
        target_impeller_diameter_m=0.5,
        lab_agitation_rpm=300.0,
        target_agitation_rpm=30.0,
        fluid_density_kg_m3=1000.0,
        lab_viscosity_Pa_s=0.001,
        target_viscosity_Pa_s=0.001,
        lab_mixing_time_s=60.0,
    )

    similarity = result["similarity"]
    assert similarity["lab_reynolds"] is not None
    assert similarity["target_reynolds"] is not None
    assert math.isclose(similarity["reynolds_ratio"], 10.0)
    assert similarity["lab_froude"] is not None
    assert similarity["target_froude"] is not None
    criteria = similarity["criteria_comparison_target_rpm"]
    assert math.isclose(criteria["constant_tip_speed"], 30.0)
    assert math.isclose(criteria["constant_P_over_V"], 300.0 * 0.1 ** (2.0 / 3.0))
    assert math.isclose(criteria["constant_Re"], 3.0)
    assert math.isclose(criteria["constant_Fr"], 300.0 * math.sqrt(0.1))
    assert similarity["predicted_target_mixing_time_s"] == 600.0


def test_oxygen_demand_is_calculated_from_biomass_trajectory_and_qo2():
    result = calculate_engineering_scale_up(
        lab_volume_L=2.0,
        target_volume_L=200.0,
        target_kla_1_h=100.0,
        target_cstar_g_L=0.008,
        target_do_g_L=0.002,
        qO2_g_gX_h=0.20,
        biomass_trajectory_g_L=[1.0, 5.0, 10.0],
        trajectory_time_h=[0.0, 1.0, 2.0],
    )

    demand = result["oxygen_demand"]
    assert math.isclose(demand["lab_peak_biomass_g_L"], 10.0)
    assert math.isclose(demand["lab_peak_our_g_L_h"], 2.0)
    assert math.isclose(demand["target_peak_our_g_L_h"], 2.0)
    assert math.isclose(demand["target_peak_our_g_h"], 400.0)
    assert math.isclose(demand["transfer_capacity_ratio"], 0.3)
    assert math.isclose(demand["transfer_margin_g_L_h"], -1.4)
    assert math.isclose(demand["target_critical_biomass_g_L"], 3.0)
    assert demand["status"] == "screening_capacity_exceeded"


def test_oxygen_demand_can_be_calculated_before_otr_is_available():
    result = calculate_engineering_scale_up(
        lab_volume_L=2.0,
        target_volume_L=200.0,
        qO2_g_gX_h=0.10,
        biomass_trajectory_g_L=[1.0, 4.0],
    )

    demand = result["oxygen_demand"]
    assert math.isclose(demand["target_peak_our_g_L_h"], 0.4)
    assert demand["transfer_capacity_ratio"] is None
    assert demand["status"] == "our_calculated_otr_not_available"


def test_metabolic_heat_generation_is_derived_from_oxygen_demand():
    result = calculate_engineering_scale_up(
        lab_volume_L=2.0,
        target_volume_L=200.0,
        qO2_g_gX_h=0.20,
        biomass_trajectory_g_L=[1.0, 5.0, 10.0],
        heat_release_kJ_per_gO2=10.0,
        additional_heat_load_W=100.0,
        target_overall_heat_transfer_U_W_m2K=500.0,
        target_heat_transfer_area_m2=1.0,
        target_delta_T_K=10.0,
    )

    heat = result["heat"]
    # Peak OUR = 2 g O2/L/h; at 200 L this is 400 g O2/h.
    # 400 g/h * 10 kJ/g / 3.6 = 1111.111... W.
    assert math.isclose(heat["target_metabolic_heat_generation_W"], 400.0 * 10.0 / 3.6)
    assert math.isclose(heat["target_total_heat_generation_W"], 100.0 + 400.0 * 10.0 / 3.6)
    assert math.isclose(heat["target_heat_duty_basis_W"], heat["target_total_heat_generation_W"])
    assert heat["status"] == "capacity_available"
    assert heat["thermal_critical_biomass_g_L"] is not None


def test_manual_heat_duty_overrides_calculated_duty_for_capacity_check():
    result = calculate_engineering_scale_up(
        lab_volume_L=2.0,
        target_volume_L=200.0,
        qO2_g_gX_h=0.10,
        biomass_trajectory_g_L=[1.0, 4.0],
        heat_release_kJ_per_gO2=10.0,
        additional_heat_load_W=100.0,
        target_heat_duty_W=500.0,
        target_overall_heat_transfer_U_W_m2K=100.0,
        target_heat_transfer_area_m2=10.0,
        target_delta_T_K=10.0,
    )

    heat = result["heat"]
    assert heat["target_total_heat_generation_W"] is not None
    assert heat["target_heat_duty_basis_W"] == 500.0
    assert heat["target_heat_capacity_W"] == 10000.0
    assert heat["status"] == "capacity_available"


def test_heat_duty_can_be_calculated_without_heat_transfer_capacity():
    result = calculate_engineering_scale_up(
        lab_volume_L=2.0,
        target_volume_L=200.0,
        qO2_g_gX_h=0.10,
        biomass_trajectory_g_L=[1.0, 4.0],
        heat_release_kJ_per_gO2=10.0,
    )

    heat = result["heat"]
    assert heat["target_heat_duty_basis_W"] is not None
    assert heat["target_heat_capacity_W"] is None
    assert heat["status"] == "duty_calculated_capacity_not_available"
