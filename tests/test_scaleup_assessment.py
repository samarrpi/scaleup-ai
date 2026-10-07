from agents.scientific.scaleup_assessment import assess_integrated_scale_up


def _phase1():
    return {
        "scale_up_basis": "Constant concentration and volumetric feed rate",
        "scale_factor": 10.0,
        "large_scale_factor_flag": False,
        "scaled_feed_rate_L_h": 2.0,
        "expected_final_volume_L": 120.0,
        "vessel_capacity_status": "pass",
    }


def _phase2():
    return {
        "checks": {
            "reactor_geometry": "screened_match",
        },
        "power": {"lab_W_m3": 100.0, "target_W_m3": 105.0, "ratio": 1.05},
        "tip_speed": {"lab_m_s": 1.0, "target_m_s": 0.98, "ratio": 0.98},
        "aeration": {"lab_vvm": 1.0, "target_vvm": 1.02, "ratio": 1.02},
        "oxygen": {
            "lab_kla_1_h": 100.0,
            "target_kla_1_h": 95.0,
            "kla_ratio": 0.95,
            "target_otr_g_L_h": 10.0,
        },
        "heat": {
            "target_heat_capacity_W": None,
            "capacity_to_duty_ratio": None,
            "status": "not_evaluated",
        },
    }


def test_integrated_assessment_meets_basis_within_tolerance():
    result = assess_integrated_scale_up(
        scaleup_result=_phase1(),
        engineering_result=_phase2(),
    )
    statuses = {row["criterion"]: row["status"] for row in result["criteria"]}
    assert statuses["Power per volume"] == "meets_basis"
    assert statuses["Impeller tip speed"] == "meets_basis"
    assert statuses["Aeration (vvm)"] == "meets_basis"
    assert statuses["kLa"] == "meets_basis"
    assert statuses["Vessel capacity"] == "meets_constraint"


def test_integrated_assessment_flags_deviation_and_unresolved_items():
    phase2 = _phase2()
    phase2["power"] = {"lab_W_m3": 100.0, "target_W_m3": 50.0, "ratio": 0.5}
    result = assess_integrated_scale_up(
        scaleup_result=_phase1(),
        engineering_result=phase2,
        max_target_feed_rate_L_h=1.0,
    )
    statuses = {row["criterion"]: row["status"] for row in result["criteria"]}
    assert statuses["Power per volume"] == "deviates_from_basis"
    assert statuses["Target feed-rate constraint"] == "exceeds_constraint"
    assert result["summary"]["deviations"] >= 2
    assert result["summary"]["unresolved"] >= 1


def test_constraint_utilisation_is_not_treated_as_scale_up_ratio():
    result = assess_integrated_scale_up(
        scaleup_result=_phase1(),
        engineering_result=_phase2(),
        max_target_feed_rate_L_h=2.5,
    )
    row = next(item for item in result["criteria"] if item["criterion"] == "Target feed-rate constraint")
    assert row["category"] == "constraint"
    assert row["utilisation_percent"] == 80.0
    assert row["status"] == "within_constraint"


def test_constraint_at_limit_is_explicit():
    result = assess_integrated_scale_up(
        scaleup_result=_phase1(),
        engineering_result=_phase2(),
        max_target_feed_rate_L_h=2.0,
    )
    row = next(item for item in result["criteria"] if item["criterion"] == "Target feed-rate constraint")
    assert row["utilisation_percent"] == 100.0
    assert row["status"] == "at_constraint"


def test_phase3_reports_data_requirements_for_unresolved_checks():
    result = assess_integrated_scale_up(
        scaleup_result=_phase1(),
        engineering_result=_phase2(),
    )
    requirement_names = {item["criterion"] for item in result["data_requirements"]}
    assert "Oxygen transfer" in requirement_names
    assert "Heat-transfer capacity" in requirement_names
    assert result["summary"]["engineering_checks_evaluated"] >= 1
    assert result["summary"]["constraints_evaluated"] == 1  # vessel capacity


def test_phase3_reports_oxygen_capacity_against_peak_our():
    phase2 = _phase2()
    phase2["oxygen_demand"] = {
        "target_peak_our_g_L_h": 0.4,
        "transfer_capacity_ratio": 1.5,
        "status": "screening_capacity_available",
    }
    assessment = assess_integrated_scale_up(
        scaleup_result=_phase1(),
        engineering_result=phase2,
    )
    names = [item["criterion"] for item in assessment["criteria"]]
    assert "Oxygen transfer" in names
    oxygen = next(item for item in assessment["criteria"] if item["criterion"] == "Oxygen transfer")
    assert oxygen["status"] == "screening_capacity_available"
