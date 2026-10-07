# ScaleUp AI v0.4 — Integrated Workflow

## Purpose

This release makes the application easier to interpret as one workflow rather than a collection of tabs.

## Source modes

- **Process description** — the editable description is the primary source.
- **Scientific PDF** — the uploaded PDF is the primary source; page-aware text extraction is used.
- **Both — description primary** — the editable process description remains authoritative for the ProcessState, while the PDF is retained as supporting document context. The PDF does not silently overwrite process claims.

## Workflow

Understand → Graph → Evidence → Uncertainty → Model → Simulate → Scale → Export

Each stage now explains its role in plain language in the UI.

## Document handling

PDF ingestion is intentionally conservative. Extractable text and page coverage are retained. Keyword signals are shown as discovery aids only and are not promoted automatically into scientific facts. OCR, table interpretation, figure interpretation, and full semantic document extraction remain future work.

## Export

- Excel: review-oriented tabular export.
- JSON: machine-readable ProcessState plus available model, scale-up, engineering and Phase 3 results.

## Engineering interpretation

The Scale and Phase 3 stages remain screening analyses. They do not certify equipment design, process validation, or scale-up equivalence.
