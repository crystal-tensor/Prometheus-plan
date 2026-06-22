# B1/B7 cone_01 Multi-Input Statevector Replay Gate

## Summary

- Method: `b1_b7_cone01_multi_input_statevector_replay_gate_v0`
- Status: `cone01_multi_input_statevector_replay_pressure_passed_not_symbolic_certificate`
- Source QASM: `results/b1_native_t_resource_optimizer/qasmbench_medium_exact/gcm_h6.qasm`
- Candidate QASM: `results/B1_B7_cone01_qasm2_candidate_rewrite_gate/gcm_h6_line268_line1381_candidate.qasm`
- Qubits / statevector dimension: `19` / `524288`
- Input cases: `8` total; `6` computational-basis and `2` deterministic product-state inputs
- Source / candidate CNOT count / delta: `795` / `789` / `6`
- Multi-input replay passed: `True`
- Failed input cases: `0`
- Min state fidelity / max infidelity: `0.9999999999999547` / `4.529709940470639e-14`
- Max global-phase-aligned amplitude delta: `1.392888964263601e-13`
- Max probability delta: `1.8214596497756474e-15`
- Accepted full-circuit patch / replay / occurrence / proxy-T reduction: `0` / `0` / `0` / `0`
- Validation errors: `0`

## Input Cases

| Case | Kind | Fidelity | Max probability delta | Passed |
|---|---|---:|---:|---|
| `zero` | `computational_basis` | `0.9999999999999551` | `5.551115123125783e-16` | `True` |
| `x_q0` | `computational_basis` | `0.9999999999999551` | `5.551115123125783e-16` | `True` |
| `x_q4` | `computational_basis` | `0.9999999999999547` | `4.996003610813204e-16` | `True` |
| `x_q14` | `computational_basis` | `0.9999999999999589` | `4.996003610813204e-16` | `True` |
| `x_q4_q14` | `computational_basis` | `0.9999999999999583` | `7.771561172376096e-16` | `True` |
| `x_q0_q4_q14` | `computational_basis` | `0.9999999999999583` | `7.771561172376096e-16` | `True` |
| `product_seed_17` | `deterministic_product_state` | `0.9999999999999667` | `8.370040771588094e-16` | `True` |
| `product_seed_29` | `deterministic_product_state` | `0.9999999999999594` | `1.8214596497756474e-15` | `True` |

## Claim Boundary

The T-B1-004av QASM2 candidate matches the source circuit across a deterministic sampled-input statevector replay pressure suite.

Unsupported claims:

- This is not a symbolic unitary-equivalence proof for arbitrary input states.
- This is not an exhaustive input-space replay certificate.
- This is not an accepted B7 occurrence-removing certificate.
- This does not recover the dropped line-1378 overlap delta.
- This does not price or eliminate the remaining line-1381 off-grid local-U3 parameters.

## Interpretation

This is a stronger pressure gate than the default-input replay probe: the candidate matches the source across a small deterministic input suite. It is still sampled evidence, not a symbolic arbitrary-input proof, and it still cannot enter the B7 resource ledger until occurrence, local-U3 pricing, and full certificate obligations are satisfied.
