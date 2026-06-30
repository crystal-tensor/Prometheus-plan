# B4/B8 Verifier-Private Challenge Protocol Gate

- Gate: T-B4-002b / T-B8-003f
- Method: `b4_b8_verifier_private_challenge_protocol_v0`
- Status: `formal_verifier_private_challenge_protocol_not_hardware`
- Protocol: `commit_challenge_response_verify`
- Protocol rows: 36
- Predicate bits: 4
- Gates passed: 8 / 8

## Result

This gate upgrades the previous analytic verifier-private predicate pressure into an explicit commit-challenge-response-verify protocol model over the same 36 B4/B8 challenge rows.

| Metric | Value |
| --- | ---: |
| honest completeness | 1.0 |
| no-leak adversary acceptance | 0.0625 |
| no-leak soundness | 0.9375 |
| public support-only acceptance | 0.5 |
| one-bit leakage acceptance | 0.125 |
| three-bit leakage acceptance | 0.5 |
| full private-material leakage acceptance | 1.0 |

## Leakage Cascade

- `no_leak`: acceptance 0.0625 (adversary has no private access).
- `support_only`: acceptance 0.5 (adversary knows public circuit structure).
- `one_bit_leak`: acceptance 0.125 (one of four private bits leaks).
- `three_bit_leak`: acceptance 0.5 (three of four private bits leak).
- `full_leak`: acceptance 1.0 (all predicate bits known).

## Acceptance Gates

- `G1_commitment`: True
- `G2_challenge_private`: True
- `G3_honest_completeness`: True
- `G4_no_leak_soundness`: True
- `G5_one_leak_doubles`: True
- `G6_three_leak_elevated`: True
- `G7_full_leak_breaks`: True
- `G8_support_above_no_leak`: True

## Claim Boundary

- This is a formal protocol simulation and analytic leakage model.
- It is not hardware execution.
- It is not a cryptographic proof.
- It is not a sampling-hardness proof.
- It is not a quantum-advantage or BQP-separation claim.
- Next gate: run the protocol against Qiskit Aer/noise-modeled transcripts, real backend properties, or hardware randomized-measurement execution.
