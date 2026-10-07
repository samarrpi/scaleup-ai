# Phase 2/3 classical mixing scale-up extension

This extension adds a similarity-analysis layer informed by classical stirred-tank scale-up practice, including the treatment of geometric similarity, impeller Reynolds number, Froude number, constant tip speed, and constant power per unit volume.

The application compares alternative scale-up criteria rather than assuming one criterion is universally correct. The selected criterion still controls the editable target agitation basis; the comparison table shows alternative target speeds for engineering review.

Implemented diagnostics:

- Impeller Reynolds number: Re_i = rho N D^2 / mu
- Froude number: Fr = N^2 D / g
- Constant tip speed target speed
- Constant P/V target speed under geometric similarity and turbulent-screening assumptions
- Constant Reynolds-number target speed when viscosity/density data are available
- Constant Froude-number target speed
- Optional dimensionless mixing-time screening using N t_mix = constant
- Predicted target mixing time for the selected target speed when laboratory mixing time is supplied

These are screening calculations, not equipment design or process validation. Power number, kLa, heat-transfer coefficients, and other equipment-specific quantities remain user-supplied unless a documented correlation is explicitly added.
