# B4/B8 R160 Deterministic ErrorMap Remediation Adjudication

- Status: `frozen_support_rule_adjudication_complete`
- Executor classification: `deterministic_external_map_remediation_supported`
- Audited classification: `tie_stabilized_but_non_tied_guardrail_failed`
- Frozen support rule passed: `False`
- Direct replays / exact-oracle pass / fail: `1056` / `832` / `224`
- Failure cases: `7`
- Margin-protected cases / failures: `12` / `0`
- Tie baseline selected vector: `[6, 5, 4, 3, 0, 1, 2]`
- Raw execution integrity passed: `True`
- Post-execution adjudication preregistered: `False`

## Frozen Support Conditions

| Condition | Passed | Meaning |
|---|---|---|
| `S1` | `True` | all four modes select one stable tied vector |
| `S2` | `True` | at least one margin-protected non-tied case exists |
| `S3` | `True` | zero margin-protected failures occur |
| `S4` | `False` | every replay belongs to its exact rational oracle minimizer set |
| `S5` | `True` | all replay, worker, and source payloads validate |

## Exact-Oracle Failures

| Case | Key | ULP shift | Gap | Failing calls | Selected | Exact optimum |
|---|---|---:|---:|---:|---|---|
| `edge_0_1_m001ulp` | `[0, 1]` | -1 | 1.7347234759768071e-18 | 32 | `[[6, 5, 4, 3, 0, 1, 2]]` | `[[6, 5, 4, 3, 2, 1, 0]]` |
| `edge_0_1_m008ulp` | `[0, 1]` | -8 | 1.3877787807814457e-17 | 32 | `[[6, 5, 4, 3, 0, 1, 2]]` | `[[6, 5, 4, 3, 2, 1, 0]]` |
| `edge_1_0_p001ulp` | `[1, 0]` | 1 | 1.7347234759768071e-18 | 32 | `[[6, 5, 4, 3, 0, 1, 2]]` | `[[6, 5, 4, 3, 2, 1, 0]]` |
| `edge_1_0_p008ulp` | `[1, 0]` | 8 | 1.3877787807814457e-17 | 32 | `[[6, 5, 4, 3, 0, 1, 2]]` | `[[6, 5, 4, 3, 2, 1, 0]]` |
| `edge_1_2_m001ulp` | `[1, 2]` | -1 | 8.6736173798840355e-19 | 32 | `[[6, 5, 4, 3, 0, 1, 2]]` | `[[6, 5, 4, 3, 2, 1, 0]]` |
| `edge_2_1_p001ulp` | `[2, 1]` | 1 | 8.6736173798840355e-19 | 32 | `[[6, 5, 4, 3, 0, 1, 2]]` | `[[6, 5, 4, 3, 2, 1, 0]]` |
| `edge_2_1_p008ulp` | `[2, 1]` | 8 | 6.9388939039072284e-18 | 32 | `[[6, 5, 4, 3, 0, 1, 2]]` | `[[6, 5, 4, 3, 2, 1, 0]]` |

## Interpretation

The raw execution is internally valid, but its positive executor classification omitted the public rule requiring every replay to belong to its exact-oracle minimum set. Exactly 224 calls across seven 1-8 ULP near-tie cases deterministically return mapping A while the exact rational oracle prefers mapping B. All twelve cases above the frozen `1e-16` protection margin pass. The evidence therefore supports deterministic tie stabilization and a bounded margin guardrail, but rejects complete remediation under the published support rule.

## Claim Boundary

This post-execution adjudication was not separately preregistered; it applies the already public R160 support rule to immutable artifacts. It does not claim a complete fix, accepted upstream patch, confirmed Qiskit bug, cross-platform theorem, hardware relevance, route advantage, quantum advantage, BQP separation, solved B4/B8/B10, or new research credit.
