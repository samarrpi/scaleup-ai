from agents.scientific.ecoli_runner import run_from_process_state
from agents.scientific.engineering_analysis import calculate_engineering_analysis
from schemas.process import Parameter, ProcessState


def test_engineering_analysis_returns_structured_result():
    process_state = ProcessState(
        process="fed-batch fermentation",
        organism="E. coli",
        product="recombinant protein",
        equipment="2 L bioreactor",
        scale="2 L",
        parameters=[
            Parameter(name="initial_biomass", value=1.0, unit="g/L"),
            Parameter(name="initial_substrate", value=20.0, unit="g/L"),
            Parameter(name="initial_product", value=0.0, unit="g/L"),
            Parameter(name="initial_volume", value=2.0, unit="L"),
            Parameter(name="mu_max", value=0.5, unit="1/h"),
            Parameter(name="Ks", value=1.0, unit="g/L"),
            Parameter(name="Yxs", value=0.5, unit="g/g"),
            Parameter(name="Ypx", value=0.10, unit="g/g"),
            Parameter(name="feed_rate", value=0.02, unit="L/h"),
            Parameter(name="feed_substrate", value=500.0, unit="g/L"),
            Parameter(name="duration", value=10.0, unit="h"),
        ],
    )

    result = run_from_process_state(process_state)
    analysis = calculate_engineering_analysis(result)

    assert analysis.status == "complete"
    assert abs(analysis.final_volume_L - 2.2) < 1e-9
    assert abs(analysis.feed_volume_L - 0.2) < 1e-9
    assert analysis.final_product_g_L > 0
    assert analysis.product_productivity_g_L_h is not None
    assert analysis.volume_balance_status == "pass"


def test_engineering_analysis_calculates_feed_substrate():
    process_state = ProcessState(
        parameters=[
            Parameter(name="initial_biomass", value=1.0, unit="g/L"),
            Parameter(name="initial_substrate", value=20.0, unit="g/L"),
            Parameter(name="initial_volume", value=2.0, unit="L"),
            Parameter(name="feed_rate", value=0.02, unit="L/h"),
            Parameter(name="feed_substrate", value=500.0, unit="g/L"),
            Parameter(name="duration", value=10.0, unit="h"),
        ]
    )

    result = run_from_process_state(process_state)
    analysis = calculate_engineering_analysis(result)

    assert analysis.initial_biomass_mass_g == 2.0
    assert analysis.substrate_fed_g == 100.0
    assert analysis.substrate_consumed_g is not None
    assert analysis.product_yield_g_g is not None
