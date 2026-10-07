# ScaleUp AI — Document Intelligence v2

## Purpose

Document Intelligence v2 separates document observation from process interpretation.

The pipeline is:

`PDF -> page text -> document sections -> candidate claims -> reviewable evidence -> ProcessState`

Only explicitly labelled PDF facts are promoted automatically into ProcessState. General scientific prose and keyword occurrences remain candidate observations until semantic review is implemented.

## Why this matters

A scientific paper may mention an organism, reactor, parameter, or scale-up method without that item being the identity or operating condition of the process under analysis. Treating every occurrence as a fact creates false ProcessState records.

The current implementation therefore exposes:

- page count and text coverage;
- coarse document sections;
- candidate scientific claims with page and section;
- extraction warnings;
- explicitly labelled facts that can safely enter the existing conservative parser.

## Candidate claim status

`candidate` means "observed by a transparent rule and ready for review". It does not mean "validated process fact".

The next semantic extraction layer can promote reviewed claims while retaining their source page and excerpt.
