# B4/B8 R160 Deterministic ErrorMap Remediation

> **Adjudication:** The executor classification below is overruled by
> `B4_B8_R160_deterministic_error_map_remediation_adjudication_v0`. The public
> support rule fails because `224/1056` replays lie outside their exact-oracle
> minimum set. The audited classification is
> `tie_stabilized_but_non_tied_guardrail_failed`.

- Status: `deterministic_error_map_remediation_complete`
- Classification: `deterministic_external_map_remediation_supported`
- Profiles / processes / cases / direct calls: `4` / `16` / `33` / `1056`
- Tie baseline stable / cross-mode agreement: `True` / `True`
- Tie baseline selected vector: `[6, 5, 4, 3, 0, 1, 2]`
- Margin-protected cases / failures: `12` / `0`
- All replays within exact oracle: `False`
- Simulation executions / shots: `0` / `0`
- Conditions and requirements passed/failed: `10` / `0` and `10` / `0`

## Profile Summary

| Mode | Processes | Calls | Baseline stable | Baseline vectors | All calls in oracle |
|---|---:|---:|---|---|---|
| `ascending_f64` | 4 | 264 | `True` | `[[6, 5, 4, 3, 0, 1, 2]]` | `False` |
| `descending_f64` | 4 | 264 | `True` | `[[6, 5, 4, 3, 0, 1, 2]]` | `False` |
| `math_fsum` | 4 | 264 | `True` | `[[6, 5, 4, 3, 0, 1, 2]]` | `False` |
| `exact_binary_fraction` | 4 | 264 | `True` | `[[6, 5, 4, 3, 0, 1, 2]]` | `False` |

## Protected Non-Tied Cases

| Case | Key | ULP shift | Minimum gap | Agreement | Oracle selected |
|---|---|---:|---:|---|---|
| `edge_0_1_m512ulp` | `[0, 1]` | -512 | 8.8817841970012523e-16 | `True` | `True` |
| `edge_0_1_m064ulp` | `[0, 1]` | -64 | 1.1102230246251565e-16 | `True` | `True` |
| `edge_0_1_p064ulp` | `[0, 1]` | 64 | 1.1102230246251565e-16 | `True` | `True` |
| `edge_0_1_p512ulp` | `[0, 1]` | 512 | 8.8817841970012523e-16 | `True` | `True` |
| `edge_1_0_m512ulp` | `[1, 0]` | -512 | 8.8817841970012523e-16 | `True` | `True` |
| `edge_1_0_m064ulp` | `[1, 0]` | -64 | 1.1102230246251565e-16 | `True` | `True` |
| `edge_1_0_p064ulp` | `[1, 0]` | 64 | 1.1102230246251565e-16 | `True` | `True` |
| `edge_1_0_p512ulp` | `[1, 0]` | 512 | 8.8817841970012523e-16 | `True` | `True` |
| `edge_1_2_m512ulp` | `[1, 2]` | -512 | 4.4408920985006262e-16 | `True` | `True` |
| `edge_1_2_p512ulp` | `[1, 2]` | 512 | 4.4408920985006262e-16 | `True` | `True` |
| `edge_2_1_m512ulp` | `[2, 1]` | -512 | 4.4408920985006262e-16 | `True` | `True` |
| `edge_2_1_p512ulp` | `[2, 1]` | 512 | 4.4408920985006262e-16 | `True` | `True` |

## Interpretation

All four deterministic accumulation methods agree on one stable tied-layout selection, and every margin-protected non-tied case selects the shared exact-oracle optimum. This supports a user-space external ErrorMap remediation for this input without claiming an upstream fix.

## Claim Boundary

This experiment can support or reject a deterministic external ErrorMap remediation on one frozen input and official binary. It does not establish an accepted upstream patch, a confirmed general Qiskit bug, cross-platform determinism, hardware relevance, route advantage, quantum advantage, BQP separation, solved B4/B8/B10, or new research credit.
