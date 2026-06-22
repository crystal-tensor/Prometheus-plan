# B1/B7 cone_01 OpenQASM 3 Composable Patch Lift Gate

- Method: `b1_b7_cone01_openqasm3_composable_patch_lift_gate_v0`
- Status: `cone01_openqasm3_composable_patch_lift_passed_without_b7_resource_credit`
- Model status: `openqasm3_candidate_inherits_composable_patch_certificate_via_structural_roundtrip_without_b7_credit`
- Workload: `qasmbench_medium_exact/gcm_h6.qasm`
- QASM2 candidate: `results/B1_B7_cone01_qasm2_candidate_rewrite_gate/gcm_h6_line268_line1381_candidate.qasm`
- OpenQASM 3 artifact: `results/B1_B7_cone01_openqasm3_candidate_export_gate/gcm_h6_line268_line1381_candidate_openqasm3.qasm`

## Evidence

- Normalized stream match / mismatches / length delta: True / 0 / 0
- Normalized instruction count / SHA-256: 1878 / `7cd50bea1f5a3c191c5735c0891d3f70f8c07a9cfca9d6e93724e6d49cb36343`
- Selected patches / lines / dropped overlap lines: 2 / [268, 1381] / [1378]
- Non-overlap / local-unitary certificates: True / True
- Max selected patch residual / entry error: 6.513210005207597e-13 / 4.525273102184799e-13
- OpenQASM 3 finite-span certificate / subspace: True / 6 of 524288
- OpenQASM 3 linear-span spectral error: 2.7889440543898627e-13
- Source / OpenQASM 3 CNOT count / delta: 795 / 789 / 6

## Claim Boundary

The project-local OpenQASM 3 candidate inherits the selected line-268 and line-1381 composable local-unitary patch certificate because the OpenQASM 2 candidate and OpenQASM 3 artifact normalize to the same instruction stream, and the OpenQASM 3 branch already has a finite-span replay certificate.

Unsupported claims:

- This is not a Qiskit OpenQASM 3 loader parse.
- This is not a symbolic exact full-circuit unitary proof.
- This is not arbitrary-input or full-Hilbert-space coverage.
- This does not recover the dropped line-1378 overlap delta.
- This does not price or eliminate the remaining line-1381 off-grid local-U3 parameters.
- This does not improve the B7 resource ledger.

## Next Gates

- Replace project-local parsing with an independent OpenQASM 3 loader-backed replay.
- Upgrade finite-span evidence toward symbolic or full-space local-unitary proof pressure.
- Price the line-1381 off-grid local-U3 parameters under an honest fault-tolerant ledger before any B7 credit.
