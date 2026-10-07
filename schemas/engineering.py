from pydantic import BaseModel, Field


class EngineeringAnalysis(BaseModel):
    """Engineering-level quantities derived from a scientific model result."""

    status: str = "complete"
    duration_h: float
    initial_volume_L: float
    final_volume_L: float
    feed_volume_L: float

    initial_biomass_g_L: float
    final_biomass_g_L: float
    initial_biomass_mass_g: float
    final_biomass_mass_g: float
    biomass_formed_g: float

    initial_substrate_g_L: float
    final_substrate_g_L: float
    initial_substrate_mass_g: float
    final_substrate_mass_g: float
    substrate_fed_g: float | None = None
    substrate_consumed_g: float | None = None

    initial_product_g_L: float
    final_product_g_L: float
    initial_product_mass_g: float
    final_product_mass_g: float
    product_formed_g: float

    biomass_yield_g_g: float | None = None
    product_yield_g_g: float | None = None
    biomass_productivity_g_L_h: float | None = None
    product_productivity_g_L_h: float | None = None

    feed_rate_L_h: float | None = None
    feed_substrate_g_L: float | None = None
    dilution_rate_1_h: float | None = None

    expected_feed_volume_L: float | None = None
    volume_balance_error_L: float | None = None
    volume_balance_status: str = "not_available"

    warnings: list[str] = Field(default_factory=list)
