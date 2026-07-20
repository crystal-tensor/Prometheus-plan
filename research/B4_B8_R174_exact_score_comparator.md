# B4/B8/B10 R174 Exact-Score Comparator

- Status: `shadow_comparator_matrix_passed`
- Classification: `cross_graph_exact_tie_repair_with_non_tie_preservation`
- Requirements: `10/10`
- Payload hash: `4bc8c0902d8a5f3a41efd61ab9b308765adc0bbbc193687d3fedb070e7bdf7fc`

## Research Question

Can an exact fixed-grid score comparator remove two cross-graph one-ULP false winners without disturbing declared non-ties?

## Result

The shadow comparator validates `576/576` replay rows and `1728/1728` candidate totals. It passes `3456/3456` order tests, each of which requires the first exact minimizer in the presented candidate order.

| Dataset | Rows | Source preserved | Changed to exact | Exact ties |
|---|---:|---:|---:|---:|
| r169_non_tie | 192 | 192 | 0 | 0 |
| r170_path_true_tie | 192 | 0 | 192 | 192 |
| r172_t_tree_true_tie | 192 | 0 | 192 | 192 |

R169 preserves all 192 non-tie selections. R170 and R172 each replace all 192 source one-ULP false winners with the first member of the exact tie. The R160 guardrail passes 4/4 exact ties and 28/28 exact non-ties.

## Mechanism

Every finite binary64 leaf is decoded exactly into an integer multiple of `2^-1074`. Integer addition is associative and order independent, so candidate comparison no longer depends on the reduction tree. Equality uses strict-less-than semantics and therefore preserves the first candidate seen.

## Claim Boundary

This is a replay-backed shadow comparator, not an integrated Qiskit source patch. It does not establish acceptable runtime overhead, route quality beyond the frozen matrix, a confirmed Qiskit bug, hardware relevance, quantum advantage, BQP separation, a solved frontier, or new credit.
