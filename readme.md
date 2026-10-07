# ScaleUp AI v0.2

ScaleUp AI converts a biological or chemical process description into a structured, traceable process representation and provides a path from process understanding to scientific models, simulation and engineering scale-up.

## Product workflow

```text
source / process description
  → Understand
  → ProcessState
  → Graph
  → Evidence
  → Uncertainty
  → Model
  → Simulate
  → Scale
  → Export
```

The central design principle is that the process representation should preserve not only parameters, but also relationships, evidence, provenance, uncertainty and missing information.

## Core ProcessState

`schemas/process.py` is the canonical contract. It contains:

- process descriptors
- parameters, objectives and constraints
- typed process nodes and directed relations
- source evidence
- field-to-evidence mappings
- structured uncertainty findings
- experiments, model results and recommendations

### Evidence

Every locally extracted parameter/objective/constraint is linked to an evidence record pointing to the source line in the user-provided description. The schema also supports page-aware evidence for future PDF ingestion.

### Process graph

The graph builder is conservative. It only constructs topology when an explicit operation sequence is supplied, such as:

```text
Operations: Media preparation -> Inoculation -> Fermentation -> Harvest
```

It creates typed operation nodes and `precedes` relations with evidence. It does not infer unsupported topology from a process label alone.

### Uncertainty

Missing, ambiguous and contradictory findings are preserved both in the original lists and as structured `UncertaintyFinding` records.

## Scientific model registry

`agents/scientific/model_registry.py` separates model discovery from model execution.

The first registered model is the existing E. coli fed-batch model. It exposes:

- applicability
- readiness
- execution
- model metadata

The E. coli implementation remains the scientific-model demonstration rather than becoming the definition of ScaleUp AI itself.

## Engineering scale-up

The existing engineering layer remains available under the **Scale** stage and includes:

- volumetric first-pass scale-up
- reactor geometry
- H/T and D/T screening assumptions
- tip speed
- P/V
- Reynolds and Froude diagnostics
- alternative classical scale-up criteria
- aeration/vvm
- kLa/OTR
- OUR from process-specific qO2
- metabolic heat generation
- heat-removal capacity
- Phase 3 integrated engineering assessment

These calculations remain screening tools and do not silently infer unavailable equipment properties.

## Current limitation

The application currently accepts process text rather than performing full page-aware PDF ingestion. The evidence schema is intentionally ready for this next stage; page numbers and excerpts must not be fabricated until a document-ingestion layer exists.

## Setup

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run tests

```powershell
python -m pytest
```

## Run the UI

```powershell
python -m streamlit run app\streamlit_app.py
```

## Run the UI examples

The sidebar contains bundled examples for:

- Clean process
- E. coli fed-batch
- Ambiguous information
- Contradiction
- Missing information
- Messy process

## Validation

The v0.2 process-intelligence milestone currently passes the full automated suite with **51 tests**.

## Document Intelligence v2

The PDF workflow now separates document observation from validated process facts. ScaleUp AI detects coarse sections and transparent candidate scientific claims with page/section context. Candidate claims remain marked `candidate` until a semantic review layer promotes them into the ProcessState. General keyword occurrences are not silently treated as process identity, parameters, or operations.
