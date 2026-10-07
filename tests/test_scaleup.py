from agents.scientific.scaleup import calculate_first_pass_scale_up


def test_first_pass_scale_up_scales_volume_and_feed_rate():
    result = calculate_first_pass_scale_up(
        lab_volume_L=2.0,
        target_volume_L=200.0,
        initial_biomass_g_L=1.0,
        initial_substrate_g_L=20.0,
        initial_product_g_L=0.0,
        feed_rate_L_h=0.02,
        feed_substrate_g_L=500.0,
        duration_h=10.0,
    )

    assert result["scale_factor"] == 100.0
    assert result["scaled_feed_rate_L_h"] == 2.0
    assert result["scaled_initial_biomass_mass_g"] == 200.0
    assert result["scaled_initial_substrate_mass_g"] == 4000.0
    assert result["scaled_substrate_feed_mass_g"] == 10000.0
    assert result["expected_final_volume_L"] == 220.0


def test_first_pass_scale_up_preserves_concentrations():
    result = calculate_first_pass_scale_up(
        lab_volume_L=2.0,
        target_volume_L=20.0,
        initial_biomass_g_L=1.5,
        initial_substrate_g_L=25.0,
        initial_product_g_L=0.2,
        feed_rate_L_h=0.2,
        feed_substrate_g_L=500.0,
        duration_h=5.0,
    )

    assert result["preserved_concentrations"] is True
    assert result["initial_biomass_g_L"] == 1.5
    assert result["initial_substrate_g_L"] == 25.0
    assert result["initial_product_g_L"] == 0.2


def test_scale_up_flags_large_transition_and_unchecked_engineering_criteria():
    result = calculate_first_pass_scale_up(
        lab_volume_L=2.0,
        target_volume_L=5500.0,
        initial_biomass_g_L=1.0,
        initial_substrate_g_L=20.0,
        initial_product_g_L=0.0,
        feed_rate_L_h=0.02,
        feed_substrate_g_L=500.0,
        duration_h=10.0,
    )

    assert result["large_scale_factor_flag"] is True
    assert result["vessel_capacity_status"] == "not_evaluated"
    assert result["engineering_checks"]["mixing"] == "not_evaluated"
    assert result["engineering_checks"]["oxygen_transfer"] == "not_evaluated"
    assert result["engineering_checks"]["heat_transfer"] == "not_evaluated"


def test_scale_up_vessel_capacity_check():
    result = calculate_first_pass_scale_up(
        lab_volume_L=2.0,
        target_volume_L=200.0,
        initial_biomass_g_L=1.0,
        initial_substrate_g_L=20.0,
        initial_product_g_L=0.0,
        feed_rate_L_h=0.02,
        feed_substrate_g_L=500.0,
        duration_h=10.0,
        max_working_volume_L=250.0,
    )

    assert result["expected_final_volume_L"] == 220.0
    assert result["vessel_capacity_status"] == "pass"

    result_fail = calculate_first_pass_scale_up(
        lab_volume_L=2.0,
        target_volume_L=200.0,
        initial_biomass_g_L=1.0,
        initial_substrate_g_L=20.0,
        initial_product_g_L=0.0,
        feed_rate_L_h=0.02,
        feed_substrate_g_L=500.0,
        duration_h=10.0,
        max_working_volume_L=210.0,
    )

    assert result_fail["vessel_capacity_status"] == "check"
