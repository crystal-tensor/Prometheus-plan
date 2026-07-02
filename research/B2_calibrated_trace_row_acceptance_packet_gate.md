# B2 Calibrated Trace Row Acceptance Packet Gate

Status: `calibrated_trace_row_acceptance_packet_open_missing_artifact`

## Summary

- Method: `b2_calibrated_trace_row_acceptance_packet_gate_v0`
- Acceptance packet: `B2-T5-calibrated-trace-row-acceptance-packet`
- Trace packet: `B2-T5-calibrated-flag-observation-rows`
- Replay-validation manifest: `B2-T5-calibrated-trace-row-replay-validation-manifest`
- Replay-validation manifest hash: `206df5ca2c1a7e5d7aa8a8f140abeb9b8f1bfb80bf7eaaa2de70fb5033dd4137`
- Priority packet hash: `abec5e9114f6a6dcdc4d2b0bf7cc580c22fc6d8007fc68bdc2b1e9c7aae9378d`
- Acceptance packet hash: `3cf42ae6e29cf23f20120a5d48db83efa510db007f24ec9b62fc9660ef8420c3`
- Requirements passed/failed: `6` / `3`
- Failed requirement IDs: `['P6', 'P7', 'P8']`
- Required key / production key / evidence file count: `24` / `16` / `15`
- Challenge count / source traces / holdout profile shots: `3` / `576` / `864`
- Submitted acceptance packet exists: `False`
- Accepted priority trace rows: `0`
- B7 dependency credit allowed: `False`
- validation_error_count: `0`

## Acceptance Packet

- Submission path: `research/submissions/B2-T5-calibrated-trace-row-acceptance-packet.json`
- Packet hash: `3cf42ae6e29cf23f20120a5d48db83efa510db007f24ec9b62fc9660ef8420c3`

Required evidence files:

- accepted_replay_validation_manifest
- priority_trace_row_packet
- row_batch_manifest
- detector_trace_manifest
- decoder_profile_manifest
- confusion_matrix_table
- posterior_likelihood_table
- baseline_prediction_table
- injected_prediction_table
- holdout_partition_manifest
- holdout_nonregression_table
- all_challenge_coverage_table
- calibrated_row_acceptance_ledger
- b7_zero_credit_boundary_note
- claim_boundary_note

Acceptance predicates:

- acceptance_packet_id equals B2-T5-calibrated-trace-row-acceptance-packet
- trace, calibration-source, provenance, and replay-validation IDs match source gates
- calibration, provenance, replay-validation, and priority-packet hashes match source gates
- row batch, detector trace, decoder profile, confusion, posterior, prediction, holdout, and coverage artifacts are hash-bound
- accepted_trace_row_count is positive only after all-challenge non-regression passes
- B7 dependency credit remains zero until accepted calibrated rows and independent all-challenge evidence exist
- claim_boundary forbids production-decoder, threshold, hardware-result, calibrated-device, quantum-advantage, and B7 resource-credit claims

## Requirement Results

- P1 [PASS]: Replay-validation manifest gate remains valid and blocked only on P6/P7/P8
- P2 [PASS]: Priority trace packet remains fixed and source-shaped
- P3 [PASS]: Acceptance packet carries locked row acceptance schema and evidence classes
- P4 [PASS]: Existing calibrated trace scope is preserved
- P5 [PASS]: B7 dependency credit remains blocked before accepted calibrated trace rows
- P6 [FAIL]: Calibrated trace row acceptance packet has been submitted
- P7 [FAIL]: Submitted acceptance packet satisfies the locked calibrated-trace row schema
- P8 [FAIL]: Submitted acceptance packet is source-backed, manifest-bound, row-valid, B7-boundary-bound, and claim-boundary-bound
- P9 [PASS]: Forbidden decoder, threshold, hardware, advantage, and B7-credit claims remain false

## Claim Boundary

- Supported: The B2/B7 calibrated-trace path now has a row acceptance packet that binds the replay-validation manifest, priority packet hash, row batch, detector traces, decoder profiles, holdout non-regression, all-challenge coverage, and B7 zero-credit boundary.
- Not supported: No calibrated trace row acceptance packet or calibrated row artifact has been submitted or accepted; no production decoder, threshold, hardware result, calibrated-device result, quantum advantage, or B7 resource credit is supported.
- Next gate: Submit B2-T5-calibrated-trace-row-acceptance-packet with accepted replay manifest hash, source-backed row batch replay, all-challenge non-regression, calibrated row acceptance ledger, B7 zero-credit boundary, and claim boundary.
- production_decoder_claimed: False
- threshold_claimed: False
- hardware_result_claimed: False
- calibrated_device_claimed: False
- quantum_advantage_claimed: False
- b7_dependency_credit_allowed: False

## Validation

- validation_error_count: 0
