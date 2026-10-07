# Document Intelligence v1

ScaleUp AI now accepts an optional text-based PDF as an input source.

## Flow

PDF upload -> page-aware text extraction -> existing conservative ProcessState extraction -> evidence records mapped back to PDF pages -> Graph / Evidence / Uncertainty / Model / Scale.

## What is supported

- PDF page extraction using `pypdf`.
- Page boundaries are preserved during extraction.
- Evidence generated from extracted claims is mapped back to the originating PDF page where the current line-based extractor can locate the claim.
- The uploaded filename is retained as the evidence source.
- Document metadata records page count and extraction mode.

## What is deliberately not claimed

- This is not OCR. Image-only/scanned PDFs require an OCR layer, which is not yet included.
- The current local parser remains conservative and does not infer unsupported scientific facts.
- Page-aware evidence is only as precise as the existing claim locator. A future document parser should attach exact spans and page coordinates directly during extraction.
- Tables, figures, references and multi-column layouts are not yet semantically reconstructed.

## User workflow

1. Upload a text-based scientific PDF.
2. Click **Understand process**.
3. Inspect **Understand** for the structured ProcessState.
4. Inspect **Graph** for source-supported topology.
5. Inspect **Evidence** for page-aware provenance.
6. Inspect **Uncertainty** for missing, ambiguous and contradictory information.
7. Continue to **Model**, **Simulate**, and **Scale** when the extracted ProcessState is sufficiently complete.
