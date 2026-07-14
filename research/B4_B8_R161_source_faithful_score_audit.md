# B4/B8 R161 Source-Faithful VF2 Score Audit

- Status: `source_faithful_score_audit_complete`
- Classification: `source_f64_consistent_but_exact_rational_gap_remains`
- Profiles / processes / cases / replays: `4` / `16` / `33` / `1056`
- Mapping rows per profile/case: `5040`
- R160 exact-oracle failures: `224`
- Source-faithful exact-oracle failures: `224`
- R160 failures that are source-order binary64 minima: `224`
- Source-order binary64 minimum / nonminimum rows: `1024` / `32`
- Requirements passed/failed: `10` / `0`
- Payload hash: `3308aebe50b022110d24d59de00f92af91fa2e00df56266b427f9dd5a5b31fcc`

## Research Question

Does the R160 rejected mapping survive when the oracle uses the same `neg_log_fidelity` transform and binary64 score path documented in Qiskit's VF2 implementation?

## Result

The source-faithful rational oracle still rejects the same 224 R160 replay rows. The rejection is therefore not removed by replacing raw ErrorMap errors with the source's `-log1p(-error)` score transform. However, every one of those 224 rows is a minimum under the reconstructed source-order binary64 fold. The current evidence separates two claims: the mapping is consistent with the implementation's floating-point comparison path, but it is not the exact rational minimizer of the transformed terms.

This is a numerical diagnostic boundary. It does not prove that the implementation is wrong, because the exact rational oracle and the implementation intentionally use different arithmetic domains.

## R160 Failure Rows

| Profile | Case | R160 failures | Source-exact failures | Source-f64 minimum rows |
|---|---|---:|---:|---:|
| `ascending_f64` | `edge_0_1_m001ulp` | 8 | 8 | 8 |
| `ascending_f64` | `edge_0_1_m008ulp` | 8 | 8 | 8 |
| `ascending_f64` | `edge_1_0_p001ulp` | 8 | 8 | 8 |
| `ascending_f64` | `edge_1_0_p008ulp` | 8 | 8 | 8 |
| `ascending_f64` | `edge_1_2_m001ulp` | 8 | 8 | 8 |
| `ascending_f64` | `edge_2_1_p001ulp` | 8 | 8 | 8 |
| `ascending_f64` | `edge_2_1_p008ulp` | 8 | 8 | 8 |
| `descending_f64` | `edge_0_1_m001ulp` | 8 | 8 | 8 |
| `descending_f64` | `edge_0_1_m008ulp` | 8 | 8 | 8 |
| `descending_f64` | `edge_1_0_p001ulp` | 8 | 8 | 8 |
| `descending_f64` | `edge_1_0_p008ulp` | 8 | 8 | 8 |
| `descending_f64` | `edge_1_2_m001ulp` | 8 | 8 | 8 |
| `descending_f64` | `edge_2_1_p001ulp` | 8 | 8 | 8 |
| `descending_f64` | `edge_2_1_p008ulp` | 8 | 8 | 8 |
| `exact_binary_fraction` | `edge_0_1_m001ulp` | 8 | 8 | 8 |
| `exact_binary_fraction` | `edge_0_1_m008ulp` | 8 | 8 | 8 |
| `exact_binary_fraction` | `edge_1_0_p001ulp` | 8 | 8 | 8 |
| `exact_binary_fraction` | `edge_1_0_p008ulp` | 8 | 8 | 8 |
| `exact_binary_fraction` | `edge_1_2_m001ulp` | 8 | 8 | 8 |
| `exact_binary_fraction` | `edge_2_1_p001ulp` | 8 | 8 | 8 |
| `exact_binary_fraction` | `edge_2_1_p008ulp` | 8 | 8 | 8 |
| `math_fsum` | `edge_0_1_m001ulp` | 8 | 8 | 8 |
| `math_fsum` | `edge_0_1_m008ulp` | 8 | 8 | 8 |
| `math_fsum` | `edge_1_0_p001ulp` | 8 | 8 | 8 |
| `math_fsum` | `edge_1_0_p008ulp` | 8 | 8 | 8 |
| `math_fsum` | `edge_1_2_m001ulp` | 8 | 8 | 8 |
| `math_fsum` | `edge_2_1_p001ulp` | 8 | 8 | 8 |
| `math_fsum` | `edge_2_1_p008ulp` | 8 | 8 | 8 |

## Source-F64 Boundary

The reconstructed source fold has 32 nonminimum rows, all on `edge_1_2_m008ulp`; each is exactly one `2.7755575615628914e-17` score unit above the reconstructed minimum. This residual is retained as a model-order diagnostic and is not promoted to a causal explanation.

| Profile | Case | Nonminimum rows | Maximum delta |
|---|---|---:|---:|
| `ascending_f64` | `edge_1_2_m008ulp` | 8 | 2.7755575615628914e-17 |
| `descending_f64` | `edge_1_2_m008ulp` | 8 | 2.7755575615628914e-17 |
| `exact_binary_fraction` | `edge_1_2_m008ulp` | 8 | 2.7755575615628914e-17 |
| `math_fsum` | `edge_1_2_m008ulp` | 8 | 2.7755575615628914e-17 |

## Next Gate

Instrument the source score-combination path on the frozen R157 input, retaining each partial score, restriction comparison, candidate mapping, and first divergence from a compensated/exact shadow score. The next gate must distinguish candidate enumeration order from arithmetic loss before proposing a numerical remedy.

## Claim Boundary

a source fix, causal compiler explanation, general numerical theorem, cross-platform determinism, hardware relevance, route advantage, quantum advantage, BQP separation, solved B4/B8/B10, or new credit.
