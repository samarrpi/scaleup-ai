# Process Graph v2

## Purpose

The Process Graph is an inspectable representation of the process topology, not a decorative flowchart. It exposes typed nodes, explicit relationships, provenance and evidence without inventing unreported material or causal relationships.

## Current behaviour

- `operation` nodes are created only from an explicitly labelled operation sequence such as `Operations:` or `Process steps:`.
- `precedes` relationships represent sequence information only.
- Node and relationship evidence points back to the source record held in `ProcessState`.
- Process-level parameters are displayed as context but are not assigned to individual operations unless the source explicitly provides that stage association.
- Missing, ambiguous and contradictory information remains in the Uncertainty layer.

## UI improvements

The Graph tab now contains:

1. topology metrics;
2. a graph legend explaining node and relation semantics;
3. an inspectable topology diagram;
4. a node inspector;
5. connected relationship explanations;
6. node-level evidence inspection;
7. uncertainty linked to node evidence;
8. process-level conditions;
9. a relationship audit table; and
10. an explicit statement of what the graph does not claim.

## Next graph evolution

Future document ingestion can add page-aware evidence, material-state nodes and source-supported `produces` / `consumes` / `transfers_to` relationships. Those should only be materialized when supported by the source and validated extraction pipeline.
