# B4/B8 R163 Comparison-Policy Shadow Audit

- Status: `comparison_policy_shadow_complete`
- Classification: `comparison_policies_agree_on_reconstructable_events`
- Profiles / replays: `3` / `256`
- Source compare events / reconstructable events: `6912` / `1180`
- Disagreements against source: `{'source_f64': 0, 'compensated_fsum': 0, 'exact_binary64_leaf': 0, 'tie_aware_1ulp': 0}`
- Payload hash: `ffaad9e8741693671d8f4e1edac130a9c3b1a7c1cadf8e45544f04b6943d344a`

## Research Question

Can a fixed arithmetic and tie policy change a retained VF2 comparison decision before any route or mapping is rerun?

## Method

R163 reads only the hash-bound R162 worker artifacts. It reconstructs compare operands when their source leaf expressions and source-order fold are uniquely recoverable. It then compares four policies: source-order binary64, `math.fsum`, exact rational sums of the retained binary64 leaves, and an explicit 1-ULP tie-aware rule. No Qiskit call, candidate selection, route change, simulation, or shot is performed.

## Result

The audit retained `1180` of `6912` compare events. Disagreements against the source are `{'source_f64': 0, 'compensated_fsum': 0, 'exact_binary64_leaf': 0, 'tie_aware_1ulp': 0}` for source, compensated, exact-binary64, and tie-aware policies respectively. The result is a comparison-level diagnostic only; it does not prove that any mapping would change under a production rerun.

## Profile Summary

| Profile | Replays | Source compares | Reconstructable | Source vs fsum | Source vs exact | Source vs tie-aware | Tie-aware ties |
|---|---:|---:|---:|---:|---:|---:|---:|
| `ascending_sorted_order` | 64 | 1728 | 0 | 0 | 0 | 0 | 0 |
| `descending_sorted_order` | 64 | 1728 | 0 | 0 | 0 | 0 | 0 |
| `native_hashset_order` | 128 | 3456 | 1180 | 0 | 0 | 0 | 24 |

## Claim Boundary

This audit does not establish a confirmed Qiskit bug, a numerical fix, a changed mapping, cross-platform determinism, hardware relevance, route advantage, quantum advantage, BQP separation, solved B4/B8/B10, or new credit. The 1-ULP rule is a declared shadow policy, not a production recommendation.
