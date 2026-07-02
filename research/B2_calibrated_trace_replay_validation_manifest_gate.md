# B2 Calibrated Trace Replay-Validation Manifest Gate

Status: `calibrated_trace_replay_validation_manifest_open_missing_artifact`

## Summary

- Method: `b2_calibrated_trace_replay_validation_manifest_gate_v0`
- Manifest: `B2-T5-calibrated-trace-row-replay-validation-manifest`
- Provenance manifest: `B2-T5-calibrated-trace-row-provenance-manifest`
- Calibration source manifest: `B2-T5-calibration-source-manifest`
- Trace packet: `B2-T5-calibrated-flag-observation-rows`
- Calibration source manifest hash: `5e832922d1e2671a5ac0cc549e300d56e597210d66c97d5ef0f7e76242c6e46a`
- Provenance manifest hash: `05ae214885638ff10adf13fdf017063929d728d00e40ca4ed858b90b0844c208`
- Manifest hash: `206df5ca2c1a7e5d7aa8a8f140abeb9b8f1bfb80bf7eaaa2de70fb5033dd4137`
- Requirements passed/failed: `6` / `3`
- Failed requirement IDs: `['P6', 'P7', 'P8']`
- Required key / production key / evidence file count: `18` / `13` / `13`
- Challenge count / source traces / holdout profile shots: `3` / `576` / `864`
- Submitted manifest exists: `False`
- Accepted priority trace rows: `0`
- B7 dependency credit allowed: `False`
- validation_error_count: `0`

## Replay-Validation Manifest Packet

- Submission path: `results/B2_calibrated_trace_replay_validation_manifest_submissions/B2-T5-calibrated-trace-row-replay-validation-manifest.json`
- Provenance manifest hash: `05ae214885638ff10adf13fdf017063929d728d00e40ca4ed858b90b0844c208`

Required evidence files:

- accepted_calibrated_trace_provenance_manifest
- row_batch_replay_manifest
- detector_trace_replay_manifest
- decoder_profile_replay_manifest
- confusion_matrix_replay_artifact
- posterior_likelihood_replay_table
- baseline_prediction_replay_manifest
- injected_prediction_replay_manifest
- holdout_partition_replay_manifest
- holdout_nonregression_replay_table
- all_challenge_coverage_replay_table
- b7_credit_boundary_note
- claim_boundary_note

Acceptance predicates:

- manifest_id equals B2-T5-calibrated-trace-row-replay-validation-manifest
- provenance_manifest_id equals B2-T5-calibrated-trace-row-provenance-manifest
- calibration_source_manifest_id and trace_packet_id match the source gates
- calibration_source_manifest_hash and provenance_manifest_hash match the accepted source gates
- row batch, detector trace, decoder profile, confusion matrix, posterior likelihood, baseline prediction, injected prediction, and holdout partition replays are hash-bound
- holdout non-regression and all-challenge coverage replay tables are hash-bound
- b7_credit_boundary keeps dependency_credit_allowed false until accepted calibrated rows and all-challenge non-regression exist
- source evidence files are present and replay_hashes bind provenance, calibration source, and trace identifiers
- claim_boundary forbids production decoder, threshold, calibrated-device, hardware-result, new-code, quantum-advantage, and B7 resource-credit claims

## Requirement Results

- P1 [PASS]: Calibrated trace provenance manifest remains valid and blocked only on P6/P7/P8
- P2 [PASS]: Replay manifest is bound to source, provenance, and calibrated trace packet
- P3 [PASS]: Replay manifest packet carries locked replay schema and evidence classes
- P4 [PASS]: Existing calibrated trace denominator shape is preserved
- P5 [PASS]: B7 dependency credit remains blocked before accepted replay-validated rows
- P6 [FAIL]: Calibrated trace replay-validation manifest artifact has been submitted
- P7 [FAIL]: Submitted replay manifest satisfies the locked calibrated-trace replay schema
- P8 [FAIL]: Submitted replay manifest is source-backed, manifest-bound, replay-bound, B7-boundary-bound, and claim-boundary-bound
- P9 [PASS]: Forbidden decoder, threshold, hardware, advantage, and B7-credit claims remain false

## Claim Boundary

- Supported: The B2/B7 calibrated-trace path now has a replay-validation manifest packet that must bind row, detector, decoder, posterior, prediction, holdout, all-challenge, and B7 zero-credit replay evidence before calibrated rows can count.
- Not supported: No calibrated trace replay-validation manifest or calibrated trace row has been submitted or accepted; no production decoder, threshold, hardware result, calibrated-device result, new-code result, quantum advantage, or B7 resource credit is supported.
- Next gate: Submit B2-T5-calibrated-trace-row-replay-validation-manifest with the accepted trace provenance hash, row/detector/decoder replay hashes, holdout non-regression, all-challenge coverage, and explicit B7 zero-credit boundary.
- production_decoder_claimed: False
- threshold_claimed: False
- hardware_result_claimed: False
- calibrated_device_claimed: False
- quantum_advantage_claimed: False
- b7_dependency_credit_allowed: False

## Validation

- validation_error_count: 0
