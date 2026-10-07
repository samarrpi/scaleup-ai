# Scientific Model — Fed-Batch E. coli

## Process

2 L fed-batch E. coli fermentation producing recombinant protein.

## Inputs

- Initial reactor volume
- Initial biomass concentration
- Initial substrate concentration
- Initial product concentration
- Feed rate
- Feed substrate concentration
- Temperature
- pH
- Dissolved oxygen
- Process duration

## State Variables

- Biomass concentration X
- Substrate concentration S
- Product concentration P
- Reactor volume V

## Controllable Variables

- Feed rate
- Temperature
- pH
- Dissolved oxygen setpoint
- Agitation
- Aeration

## Measurable Variables

- Biomass
- Substrate concentration
- Product concentration
- Dissolved oxygen
- pH
- Temperature
- Reactor volume
- Feed rate

## Outputs

- Final biomass
- Final substrate
- Final product
- Biomass trajectory
- Product trajectory
- Substrate trajectory
- Process duration

## Constraints

- Maximum reactor volume
- Maximum feed rate
- Temperature operating range
- pH operating range
- Dissolved oxygen minimum
- Maximum biomass concentration

## First Mechanistic Model
### Biomass growth

dX/dt = μX

where:

- X = biomass concentration
- μ = specific growth rate
- Maximum biomass concentration

## First Mechanistic Model
### Biomass growth

dX/dt = μX

where:

- X = biomass concentration
- μ = specific growth rate
- Maximum biomass concentration
### Substrate consumption

dS/dt = -qS X

where:

- S = substrate concentration
- qS = specific substrate consumption rate
- X = biomass concentration
### Product formation

dP/dt = qP X

where:

- P = recombinant protein concentration
- qP = specific product formation rate
- X = biomass concentration
### Assumptions

1. The reactor is well mixed.
2. Biomass growth follows a simple exponential-growth model.
3. Substrate consumption is proportional to biomass.
4. Product formation is proportional to biomass.
5. Temperature, pH, and dissolved oxygen are assumed constant for the first model.
6. Feed addition is not yet included in the first calculation.
7. Oxygen transfer limitations are not yet included.
8. No biomass death or lysis is included.

## Initial Model Parameters

For the first prototype, use fixed illustrative parameter values.

### Specific growth rate

μ = 0.5 1/h

### Specific substrate consumption rate

qS = 0.2 g/g/h

### Specific product formation rate

qP = 0.05 g/g/h

These values are placeholders for the first computational prototype.
They are not validated biological parameters.

They will eventually be estimated from experimental data.
### Concentration units

- X = g biomass/L
- S = g substrate/L
- P = g product/L
- t = h

## Example Simulation

### Initial conditions

- X₀ = 1.0 g biomass/L
- S₀ = 20.0 g substrate/L
- P₀ = 0.0 g product/L

### Model parameters

- μ = 0.5 h⁻¹
- qS = 0.2 g substrate / (g biomass · h)
- qP = 0.05 g product / (g biomass · h)

### Simulation

- Start time = 0 h
- End time = 10 h

The model will calculate:

- Biomass concentration X(t)
- Substrate concentration S(t)
- Product concentration P(t)

at each time point during the simulation.

## Substrate-Limited Growth

The constant-growth-rate assumption is not sufficient when substrate
becomes limiting.

For the next model version, specific growth rate will depend on
substrate concentration using Monod kinetics:

μ(S) = μmax × S / (KS + S)

where:

- μmax = maximum specific growth rate (h⁻¹)
- S = substrate concentration (g/L)
- KS = half-saturation constant (g/L)

As substrate concentration decreases, the specific growth rate
decreases.

When S approaches zero, μ approaches zero.

### Initial illustrative parameters

- μmax = 0.5 h⁻¹
- KS = 1.0 g/L

These are illustrative prototype values and are not experimentally
validated parameters.

## Biomass Yield

Substrate consumption will be linked to biomass growth using a biomass
yield coefficient:

qS = μ / YXS

where:

- qS = specific substrate consumption rate
  (g substrate / (g biomass · h))
- μ = specific growth rate (h⁻¹)
- YXS = biomass yield on substrate
  (g biomass / g substrate)

For the first prototype:

YXS = 0.5 g biomass / g substrate

This is an illustrative value and is not experimentally validated.

## Fed-Batch Model

The next model version extends the batch model to include continuous
feed addition.

### Additional variables

- F = feed flow rate (L/h)
- Sf = substrate concentration in the feed (g/L)
- V = reactor volume (L)

### Reactor volume

dV/dt = F

As feed is added, reactor volume increases.

### Biomass balance

dX/dt = μX - (F/V)X

The first term represents biomass growth.

The second term represents dilution caused by feed addition.

### Substrate balance

dS/dt = -(μ/YXS)X + (F/V)(Sf - S)

The first term represents substrate consumption by biomass.

The second term represents substrate entering with the feed and
dilution of the existing reactor contents.

### Product balance

dP/dt = YPX(μX) - (F/V)P

The first term represents growth-associated product formation.

The second term represents dilution of product caused by feed addition.

### Growth kinetics

μ = μmax × S / (KS + S)

### Initial fed-batch parameters

- Initial reactor volume V0 = 2.0 L
- Feed rate F = 0.02 L/h
- Feed substrate concentration Sf = 500 g/L
- μmax = 0.5 h⁻¹
- KS = 1.0 g/L
- YXS = 0.5 g biomass/g substrate
- YPX = 0.10 g product/g biomass

These are illustrative prototype values and are not experimentally
validated parameters.

### Fed-batch assumptions

1. The reactor is well mixed.
2. Feed enters continuously at a constant rate.
3. Feed contains substrate but no biomass or product.
4. Reactor volume increases according to the feed rate.
5. Growth is substrate-limited according to Monod kinetics.
6. Product formation is growth-associated.
7. No oxygen limitation is included yet.
8. No temperature or pH effects are included yet.
9. No biomass death or maintenance metabolism is included yet.
10. The feed rate remains constant during the simulation.