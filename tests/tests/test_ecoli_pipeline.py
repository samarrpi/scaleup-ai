from schemas.process import ModelResult
from agents.scientific.ecoli_pipeline import simulate_from_description


def test_simulate_from_description_returns_model_result():
    description = """
    Process: fed-batch fermentation
    Organism: E. coli
    Product: recombinant protein
    Initial biomass: 1 g/L
    Initial glucose: 20 g/L
    Initial volume: 2 L
    Feed rate: 0.02 L/h
    Feed glucose concentration: 500 g/L
    Duration: 10 h
    """

    result = simulate_from_description(description)

    assert isinstance(result, ModelResult)
    assert result.predictions["final_biomass_g_L"] > 0
    assert result.predictions["final_product_g_L"] > 0
    assert abs(result.predictions["final_volume_L"] - 2.2) < 1e-9