# B2/B7/#023 explicit 9-bit reweight adjudication v1

## Decision

Accepted classification: `fresh_holdout_explicit_reweight_semantic_regression`.

The producer emitted `nine_bit_explicit_reweight_semantic_pass_hardware_write_path_absent`, but that label is rejected. Its `semantic_pass` implementation omitted the frozen all-window equality clause.

## What passed

All 2,048 final candidate frames equal the high-precision online and full-block references. Every commit and final residual count is zero. All base and implied stored weights are even and fit unsigned nine-bit storage.

## What failed

X has `12` syndrome and `24` output mismatches among `167936` windows. Z has `17` syndrome and `34` output mismatches. The frozen protocol requires zero in all four cells, so the semantic veto fails.

## Claim boundary and next gate

The 9-bit representation is not admitted for the strict window-exact route. No Micro Blossom dynamic-write RTL, cycle, FPGA, p99, full B2, scalable #023, or B7 credit is supported. A wider-grid candidate may be selected only as a disclosed post-outcome diagnostic and must face a new public freeze and new seeds.

Independent audit checks: `19/19`. Audit ID: `574d65b08272f2a185f33d2497b891002be3e1a1904d6ab960731afd09f6bed4`.
