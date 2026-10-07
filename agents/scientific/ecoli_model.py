from typing import Any

from schemas.process import ModelResult


def simulate_ecoli(
    X0: float,
    S0: float,
    P0: float,
    V0: float,
    mu_max: float,
    Ks: float,
    Yxs: float,
    Ypx: float,
    F: float,
    Sf: float,
    duration: float,
    time_step: float = 0.01,
) -> dict[str, list[float]]:
    """
    Simulate a simple fed-batch E. coli fermentation.

    State variables
    ---------------
    X : biomass concentration (g/L)
    S : substrate concentration (g/L)
    P : recombinant product concentration (g/L)
    V : reactor volume (L)

    Parameters
    ----------
    X0 : initial biomass concentration (g/L)
    S0 : initial substrate concentration (g/L)
    P0 : initial product concentration (g/L)
    V0 : initial reactor volume (L)

    mu_max : maximum specific growth rate (1/h)
    Ks : Monod half-saturation constant (g/L)
    Yxs : biomass yield on substrate (g biomass/g substrate)
    Ypx : product yield on biomass formed (g product/g biomass)

    F : feed flow rate (L/h)
    Sf : substrate concentration in feed (g/L)

    duration : simulation duration (h)
    time_step : integration time step (h)

    Model
    -----
    Monod growth:

        mu = mu_max * S / (Ks + S)

    Biomass balance:

        dX/dt = mu * X - (F/V) * X

    Substrate balance:

        dS/dt = -(mu/Yxs) * X + (F/V) * (Sf - S)

    Product balance:

        dP/dt = Ypx * (mu * X) - (F/V) * P

    Volume balance:

        dV/dt = F

    Numerical method
    ----------------
    Explicit Euler integration.
    """

    # -------------------------
    # Input validation
    # -------------------------

    if X0 < 0:
        raise ValueError("X0 must be >= 0.")

    if S0 < 0:
        raise ValueError("S0 must be >= 0.")

    if P0 < 0:
        raise ValueError("P0 must be >= 0.")

    if V0 <= 0:
        raise ValueError("V0 must be > 0.")

    if mu_max <= 0:
        raise ValueError("mu_max must be > 0.")

    if Ks < 0:
        raise ValueError("Ks must be >= 0.")

    if Yxs <= 0:
        raise ValueError("Yxs must be > 0.")

    if Ypx < 0:
        raise ValueError("Ypx must be >= 0.")

    if F < 0:
        raise ValueError("F must be >= 0.")

    if Sf < 0:
        raise ValueError("Sf must be >= 0.")

    if duration < 0:
        raise ValueError("duration must be >= 0.")

    if time_step <= 0:
        raise ValueError("time_step must be > 0.")

    # -------------------------
    # Simulation storage
    # -------------------------

    times: list[float] = []
    biomass: list[float] = []
    substrate: list[float] = []
    product: list[float] = []
    volume: list[float] = []

    # -------------------------
    # Initial state
    # -------------------------

    t = 0.0
    X = X0
    S = S0
    P = P0
    V = V0

    # -------------------------
    # Numerical integration
    # -------------------------

    while t <= duration + 1e-12:

        times.append(t)
        biomass.append(X)
        substrate.append(S)
        product.append(P)
        volume.append(V)

        if t >= duration:
            break

        # Monod specific growth rate
        if S <= 0:
            mu = 0.0
        else:
            mu = mu_max * S / (Ks + S)

        # Specific substrate consumption rate
        qS = mu / Yxs

        # Differential balances
        dXdt = mu * X - (F / V) * X

        dSdt = (
            -qS * X
            + (F / V) * (Sf - S)
        )

        dPdt = (
            Ypx * mu * X
            - (F / V) * P
        )

        dVdt = F

        # Do not step beyond requested duration.
        dt = min(time_step, duration - t)

        # Euler integration
        X = X + dXdt * dt
        S = S + dSdt * dt
        P = P + dPdt * dt
        V = V + dVdt * dt

        # Numerical protection
        X = max(0.0, X)
        S = max(0.0, S)
        P = max(0.0, P)
        V = max(V0, V)

        t = t + dt

    return {
        "time": times,
        "biomass": biomass,
        "substrate": substrate,
        "product": product,
        "volume": volume,
    }


def run_ecoli_model(
    X0: float,
    S0: float,
    P0: float,
    V0: float,
    mu_max: float,
    Ks: float,
    Yxs: float,
    Ypx: float,
    F: float,
    Sf: float,
    duration: float,
    time_step: float = 0.01,
) -> ModelResult:
    """
    Run the E. coli scientific model and return the
    repository-standard ModelResult.
    """

    result = simulate_ecoli(
        X0=X0,
        S0=S0,
        P0=P0,
        V0=V0,
        mu_max=mu_max,
        Ks=Ks,
        Yxs=Yxs,
        Ypx=Ypx,
        F=F,
        Sf=Sf,
        duration=duration,
        time_step=time_step,
    )

    return ModelResult(
        predictions={
            "final_biomass_g_L": result["biomass"][-1],
            "final_substrate_g_L": result["substrate"][-1],
            "final_product_g_L": result["product"][-1],
            "final_volume_L": result["volume"][-1],
            "simulation_time_h": result["time"][-1],
            "time_h": result["time"],
            "biomass_g_L": result["biomass"],
            "substrate_g_L": result["substrate"],
            "product_g_L": result["product"],
            "volume_L": result["volume"],
        },
        uncertainty={
            "status": "not_quantified",
            "reason": (
                "This deterministic prototype does not yet estimate "
                "parameter or prediction uncertainty."
            ),
        },
        important_parameters=[
            "mu_max",
            "Ks",
            "Yxs",
            "Ypx",
            "F",
            "Sf",
        ],
        sensitivity={},
        model_metadata={
            "model_name": "Fed-batch E. coli mechanistic model",
            "model_version": "0.1",
            "organism": "E. coli",
            "process_type": "fed-batch fermentation",
            "numerical_method": "explicit Euler",
            "time_step_h": time_step,
            "units": {
                "biomass": "g/L",
                "substrate": "g/L",
                "product": "g/L",
                "volume": "L",
                "time": "h",
                "feed_rate": "L/h",
            },
            "assumptions": [
                "Well-mixed reactor",
                "Monod substrate-limited growth",
                "Growth-associated product formation",
                "Constant feed rate",
                "Feed contains substrate but no biomass or product",
                "No oxygen limitation",
                "No temperature effect",
                "No pH effect",
                "No biomass death",
                "No maintenance metabolism",
            ],
        },
    )


def summarize_result(
    result: dict[str, list[float]]
) -> dict[str, Any]:
    """
    Return the final values from a fed-batch simulation.
    """

    return {
        "final_biomass_g_L": result["biomass"][-1],
        "final_substrate_g_L": result["substrate"][-1],
        "final_product_g_L": result["product"][-1],
        "final_volume_L": result["volume"][-1],
        "simulation_time_h": result["time"][-1],
    }