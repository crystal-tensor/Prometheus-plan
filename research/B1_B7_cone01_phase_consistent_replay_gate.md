# B1/B7 cone_01 Phase-Consistent Replay Gate

## Summary

- Method: `b1_b7_cone01_phase_consistent_replay_gate_v0`
- Status: `cone01_phase_consistent_sampled_replay_passed_not_symbolic_certificate`
- Source QASM: `results/b1_native_t_resource_optimizer/qasmbench_medium_exact/gcm_h6.qasm`
- Candidate QASM: `results/B1_B7_cone01_qasm2_candidate_rewrite_gate/gcm_h6_line268_line1381_candidate.qasm`
- Input cases: `8` total; `4` phase anchors and `4` superposition inputs
- Phase-consistent replay passed: `True`
- Overlap phase spread radians: `1.3722356584366935e-13`
- Min overlap magnitude: `0.9999999999999772`
- Min fidelity / max infidelity: `0.9999999999999547` / `4.529709940470639e-14`
- Max amplitude / probability delta: `1.392888964263601e-13` / `1.074140776324839e-14`
- Accepted full-circuit patch / replay / occurrence / proxy-T reduction: `0` / `0` / `0` / `0`
- Validation errors: `0`

## Input Cases

| Case | Kind | Overlap phase | Fidelity | Max probability delta | Passed |
|---|---|---:|---:|---:|---|
| `zero` | `basis_phase_anchor` | `-2.4388324596671658` | `0.9999999999999551` | `5.551115123125783e-16` | `True` |
| `x_q0` | `basis_phase_anchor` | `-2.4388324596671658` | `0.9999999999999551` | `5.551115123125783e-16` | `True` |
| `x_q4` | `basis_phase_anchor` | `-2.438832459667149` | `0.9999999999999547` | `4.996003610813204e-16` | `True` |
| `x_q14` | `basis_phase_anchor` | `-2.438832459667166` | `0.9999999999999589` | `4.996003610813204e-16` | `True` |
| `sup_zero_xq4` | `basis_superposition` | `-2.438832459667139` | `0.9999999999999578` | `1.074140776324839e-14` | `True` |
| `sup_xq0_xq14` | `basis_superposition` | `-2.4388324596671653` | `0.9999999999999576` | `5.551115123125783e-16` | `True` |
| `sup_zero_product17` | `basis_product_superposition` | `-2.4388324596672057` | `1.000000000000147` | `4.182851981449076e-16` | `True` |
| `sup_product17_i_product29` | `product_superposition` | `-2.4388324596672764` | `1.0000000000000022` | `1.4784180824012338e-15` | `True` |

## Claim Boundary

The T-B1-004av QASM2 candidate has phase-consistent sampled replay across selected basis, product, and superposition inputs.

Unsupported claims:

- This is not a symbolic unitary-equivalence proof for arbitrary input states.
- This is not an exhaustive input-space replay certificate.
- This is not an accepted B7 occurrence-removing certificate.
- This does not recover the dropped line-1378 overlap delta.
- This does not price or eliminate the remaining line-1381 off-grid local-U3 parameters.

## Interpretation

This gate reduces the risk that per-input global-phase alignment is hiding an input-dependent phase mismatch. It is still sampled numerical evidence, not symbolic arbitrary-input equivalence, and it still carries zero B7 ledger credit.
