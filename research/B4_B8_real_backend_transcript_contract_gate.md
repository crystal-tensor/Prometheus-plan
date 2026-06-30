# B4/B8 Real-Backend Transcript Contract Gate v0.1

Status: **real_backend_transcript_contract_open_missing_hardware_evidence**

## Summary

- Method: b4_b8_real_backend_transcript_contract_gate_v0
- Model status: readiness_blockers_decomposed_for_backend_transcript_prs
- Source readiness method: b4_b8_real_backend_transcript_readiness_gate_v0
- Source missing readiness gates: R5, R6, R7, R8, R9
- Source transcript / train / holdout / eval rows: 720 / 560 / 160 / 640
- Backend-calibrated Aer circuit count: 5760
- Private-safe / leakage-blind / full-leak fitted acceptance: 0.0625 / 0.35 / 1.0
- Contract requirements passed / failed: 5 / 5
- Failed contract requirement ids: K5, K6, K7, K8, K9
- Contract packets: B4B8-R5-real-backend-properties, B4B8-R6-hardware-execution, B4B8-R7-leakage-separated-real-fitting, B4B8-R8-leakage-blind-no-leak-margin, B4B8-R9-full-leakage-containment
- Real backend transcript rows: 0
- Real backend transcript readiness: False
- Validation errors: []

## Contract Requirements

| gate | passed | label | PR packet | acceptance rule |
|---|---:|---|---|---|
| K1 | True | Source readiness gate is valid and fails only R5-R9 | source-audit | The source readiness gate must stay valid and fail only R5-R9. |
| K2 | True | Synthetic transcript and fitted-spoofer denominators remain available | synthetic-control-denominator | Preserve the synthetic transcript denominator while adding real rows. |
| K3 | True | GenericBackendV2 bridge remains a calibrated simulator denominator | generic-backend-control | Keep this simulated denominator, but do not treat it as real backend evidence. |
| K4 | True | PR packets exist for every failed real-backend readiness gate | packet-index | Every failed readiness gate must map to a concrete PR packet. |
| K5 | False | Real backend properties packet has been satisfied | B4B8-R5-real-backend-properties | Attach real backend properties with provenance and layout mapping. |
| K6 | False | Hardware execution packet has been satisfied | B4B8-R6-hardware-execution | Submit hardware or independent execution transcript rows. |
| K7 | False | Leakage-separated real fitting packet has been satisfied | B4B8-R7-leakage-separated-real-fitting | Train and hold out leakage-separated spoofers on real transcript rows. |
| K8 | False | Leakage-blind no-leak margin packet has been satisfied | B4B8-R8-leakage-blind-no-leak-margin | Keep leakage-blind no-leak fitted acceptance <= 0.10. |
| K9 | False | Full-private-material leakage packet has been satisfied | B4B8-R9-full-leakage-containment | Bound full-private-material leakage or move it outside the claim boundary. |
| K10 | True | Forbidden advantage and soundness claims remain absent | claim-boundary | Do not promote B4/B8 until K5-K9 pass under replayable evidence. |

## PR Packets

### B4B8-R5-real-backend-properties

- Blocks gate: K5
- Owner role: backend_calibration_agent
- Acceptance rule: real_backend_properties_used must become true while preserving the current B4/B8 verifier-private transcript fields.
- Required artifacts:
  - backend properties from a real device snapshot or provider export
  - per-qubit and per-edge timing/error/readout metadata
  - calibration timestamp, backend identifier, and provider provenance
  - mapping from exported properties into the verifier circuit layout

### B4B8-R6-hardware-execution

- Blocks gate: K6
- Owner role: hardware_execution_agent
- Acceptance rule: hardware_execution_performed must become true and the transcript schema must replay through the current fitted-spoofer evaluator.
- Required artifacts:
  - hardware or independently supplied execution transcript rows
  - circuit id, shot id, refresh mode, leakage profile, and predicate outcome columns
  - raw-to-processed transcript hash ledger
  - explicit no-refresh, challenge-refresh, and refresh-plus-rotation coverage

### B4B8-R7-leakage-separated-real-fitting

- Blocks gate: K7
- Owner role: spoofer_baseline_agent
- Acceptance rule: leakage_separated_real_training_performed must become true and real_backend_transcript_rows must be positive.
- Required artifacts:
  - leakage-separated train/holdout split over real transcript rows
  - private-safe, leakage-blind, and leakage-aware fitted families
  - fitted evaluation rows with the same 560/160 discipline or justified larger split
  - negative-control splits that prevent private-material leakage from contaminating no-leak training

### B4B8-R8-leakage-blind-no-leak-margin

- Blocks gate: K8
- Owner role: adversary_margin_agent
- Acceptance rule: leakage_blind_max_no_leak_fitted_acceptance must fall from 0.35 to <= 0.10.
- Required artifacts:
  - leakage-blind no-leak fitted acceptance table
  - same private-safe no-leak denominator table
  - diagnostic proving no-leak acceptance stays below 0.10
  - predicate redesign notes if leakage-blind fitting remains unsafe

### B4B8-R9-full-leakage-containment

- Blocks gate: K9
- Owner role: protocol_boundary_agent
- Acceptance rule: full-private-material leakage acceptance must be <= 0.25 or the claim boundary must explicitly exclude that leakage regime.
- Required artifacts:
  - full-private-material leakage acceptance table
  - explicit claim boundary excluding full leakage or a cryptographic protection layer
  - challenge-material redesign evidence if full leakage remains in scope
  - bounded leakage model with verifier-private material still hidden

## Claim Boundary

- real_backend_transcript_contract_built: True
- real_backend_transcript_readiness: False
- protocol_soundness_proved: False
- cryptographic_soundness_proved: False
- sampling_hardness_proved: False
- quantum_advantage_claimed: False
- bqp_separation_claimed: False
- hardware_execution_performed: False
- real_backend_properties_used: False
- what_is_supported: B4/B8 now has five explicit PR packets for real backend properties, hardware execution transcripts, leakage-separated real fitting, leakage-blind no-leak margin, and full-leakage containment.
- what_is_not_supported: No real backend transcript readiness, protocol soundness, sampling hardness, quantum advantage, or BQP separation is established.

## Next Gate

A future B4/B8 PR must satisfy K5-K9 together: real backend
properties, hardware or independently supplied transcripts,
leakage-separated fitting, leakage-blind no-leak acceptance below
0.10, and full-leakage containment. Until then this remains a
real-backend handoff contract, not protocol soundness or advantage.
