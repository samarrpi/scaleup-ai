# Phase 2/3 refinement

This version makes the engineering scale-up basis automatic for geometry while preserving manual engineering overrides.

## Automatic calculations
- Laboratory vessel geometry from working volume + H/T assumption.
- Target vessel geometry from target working volume + H/T assumption.
- Laboratory/target impeller diameter from D/T assumption when measured values are unavailable.
- Target agitation from laboratory agitation and the selected mixing basis when laboratory rpm is supplied.
- Target gas flow from laboratory gas flow and constant-vvm basis when laboratory gas flow is supplied.
- Phase 2 engineering calculations recalculate automatically from the current inputs.

## Manual / measured data
The application does not invent:
- laboratory agitation speed
- power number (Np)
- kLa
- oxygen saturation / dissolved oxygen
- heat-transfer coefficient, area, driving force or duty

These remain user/equipment inputs where required.

## Provenance
The UI explicitly distinguishes calculated geometry from measured equipment data and identifies user-supplied engineering data.

## Phase 3
Phase 3 consumes the Phase 2 results and can mark reactor geometry as screened under the declared geometric-similarity basis when both lab and target geometry are available.


## Current extension — oxygen demand / transfer integration

Phase 2 now connects the scientific biomass trajectory to the oxygen-transfer calculation when a process-specific specific oxygen uptake rate is supplied:

- `OUR = qO2 × X`
- peak volumetric OUR is taken from the simulated biomass trajectory
- target volumetric OUR is screened on a concentration-preserving scale-up basis
- target total oxygen uptake at peak = peak OUR × target working volume
- when target OTR is available, the model reports `OTR / OUR`, `OTR − OUR`, and `Xcrit = OTR/qO2`
- the result is explicitly a screening capacity check, not a dissolved-oxygen dynamic model or final equipment approval

The model deliberately does not infer qO2 from the existing Monod parameters. qO2 must be measured or justified for the process because oxygen uptake depends on metabolic state and process conditions.

## Phase 3 thermal integration — completed

The engineering layer now connects oxygen-demand calculations to a first-pass thermal balance.

### Added
- Process-specific heat-release basis: `heat_release_kJ_per_gO2`.
- Peak metabolic heat generation from the existing OUR calculation:
  - `Q_met = OUR_total × heat_release / 3.6`.
- Optional additional target heat load.
- Calculated total thermal duty when no manual total duty is supplied.
- Manual total heat duty remains available as an explicit override for the capacity comparison.
- Heat-removal capacity remains `Q = U × A × ΔT`.
- Heat-removal margin and capacity/duty ratio.
- Thermal critical biomass concentration when sufficient information is available.
- Phase 3 assessment now distinguishes calculated-duty-without-capacity from a fully evaluated heat-transfer check.
- Streamlit UI displays the thermal generation and removal calculations and their provenance.

### Engineering basis
The model deliberately does not assume a universal metabolic heat-release constant. The heat-release basis must be measured, justified, or supplied from an appropriate process/literature basis. The existing E. coli model has no intrinsic energy/enthalpy balance, so this thermal layer is a post-processing engineering screen rather than a replacement for a validated bioreactor energy balance.

### Current integrated chain
`Scientific biomass trajectory → qO2 → OUR → OTR comparison + metabolic heat generation → heat-removal capacity → Phase 3 assessment`

### Validation
- Full automated test suite: **46 passed**.
- Python compilation checks passed for the modified engineering, assessment, and Streamlit modules.
