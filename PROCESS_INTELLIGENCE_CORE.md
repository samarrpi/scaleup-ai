# ScaleUp AI v0.2 — Process Intelligence Core

This milestone restructures ScaleUp AI around the product idea in the project guide:

`Understand → Graph → Evidence → Uncertainty → Model → Simulate → Scale → Export`

## What is now first-class in `ProcessState`

- Process descriptors
- Parameters, objectives and constraints
- Typed process nodes and directed process relations
- Evidence records with source, location, excerpt, status and limitation
- Field-to-evidence mappings
- Structured uncertainty findings
- Existing scientific model results and engineering outputs

## Evidence behaviour

For the current text-input workflow, an extracted claim is linked to the source line in the user-provided description. The evidence schema already supports a PDF page number, so page-aware document ingestion can be added without changing the downstream representation.

The system does not claim that an excerpt proves scientific correctness. It records where the claim came from and preserves limitations.

## Graph behaviour

The current graph builder is deliberately conservative. It only creates an operation topology when the input explicitly provides an operation sequence, for example:

`Operations: Media preparation -> Inoculation -> Fermentation -> Harvest`

The resulting relations are `precedes` relations with source evidence. The system does not invent a process sequence from a bare process name.

## Model layer

`agents/scientific/model_registry.py` provides a model registry. Each registered model exposes:

- applicability
- readiness
- description/domain metadata
- execution function

The E. coli fed-batch model is the first registered model. Its existing scientific and engineering implementation remains unchanged and is consumed through the registry.

## UI flow

The Streamlit application now exposes eight top-level stages:

1. Understand
2. Graph
3. Evidence
4. Uncertainty
5. Model
6. Simulate
7. Scale
8. Export

The existing Phase 2/3 engineering calculations remain under **Scale** rather than being presented as the identity of the whole product.

## Deliberate limitation

The current milestone does not yet implement PDF ingestion or automatic figure/table topology extraction. The schema is prepared for page-aware evidence, but those capabilities should be added as a separate document-ingestion milestone rather than approximated with fabricated page references.
