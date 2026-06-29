# B1/B7 cone_01 OpenQASM 3 Qiskit-Loader Seeded Product-State Replay Gate

- Method: `b1_b7_cone01_openqasm3_qiskit_loader_seeded_product_replay_gate_v0`
- Status: `cone01_openqasm3_qiskit_loader_seeded_product_replay_passed_without_b7_credit`
- Model status: `qiskit_loader_openqasm3_matches_source_on_seeded_product_states_without_b7_credit`
- Workload: `qasmbench_medium_exact/gcm_h6.qasm`
- Supported claim: The Qiskit-loaded OpenQASM 3 candidate matches the optimized source on a deterministic 16-seed product-state replay suite after final measurements are removed.

## Inputs

- Qiskit-loader phase-consistent gate: `results/B1_B7_cone01_openqasm3_qiskit_loader_phase_consistent_replay_gate_v0.json`
- Qiskit-loader evidence-seal reproduction gate: `results/B1_B7_cone01_openqasm3_qiskit_loader_evidence_seal_reproduction_gate_v0.json`
- OpenQASM 3 candidate: `results/B1_B7_cone01_openqasm3_candidate_export_gate/gcm_h6_line268_line1381_candidate_openqasm3.qasm`

## Loader Evidence

- Qiskit / qiskit-qasm3-import / openqasm3 versions: 2.4.1 / 0.6.0 / 1.0.1
- Qubits / clbits / depth: 19 / 1 / 1483
- Operation counts: {'cx': 789, 'rz': 601, 'u': 487, 'measure': 1}

## Seeded Product-State Replay Evidence

- Input cases: 16 seeded product states
- Product-state axis sequence: ['rx', 'ry', 'rz']
- Product-state seeds: [17, 29, 41, 53, 67, 79, 83, 97, 101, 113, 127, 131, 149, 163, 181, 191]
- Min fidelity / max infidelity: 0.9999999999999389 / 6.106226635438361e-14
- Max amplitude / L2 amplitude / probability delta: 1.3496991625769186e-14 / 2.8917153762798005e-13 / 8.020927672047762e-16
- Failed cases: []
- Accepted Qiskit-loader parse / replay / seeded-product replay artifacts: 1 / 1 / 1
- Accepted occurrence / proxy-T reduction / B7 claim: 0 / 0 / False

## Claim Boundary

- This is deterministic seeded product-state evidence, not arbitrary-input equivalence.
- This is not a symbolic exact full-circuit unitary proof.
- This does not price or eliminate the remaining line-1381 off-grid local-U3 parameters.
- This does not recover the dropped line-1378 overlap delta.
- This does not improve the B7 resource ledger.

## Validation

- Qiskit-loader seeded product-state replay passed: True
- Validation errors: 0
