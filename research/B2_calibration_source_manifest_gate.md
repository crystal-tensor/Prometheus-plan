# B2 Calibration Source Manifest Gate

Status: `calibration_source_manifest_open_missing_artifact`

## Summary

- Method: `b2_calibration_source_manifest_gate_v0`
- Manifest: `B2-T5-calibration-source-manifest`
- Downstream packet: `B2-T5-calibrated-flag-observation-rows`
- Manifest hash: `5e832922d1e2671a5ac0cc549e300d56e597210d66c97d5ef0f7e76242c6e46a`
- Requirements passed/failed: `6` / `3`
- Failed requirement IDs: `['P6', 'P7', 'P8']`
- Required key / production key / evidence file count: `11` / `7` / `8`
- Challenge count / source traces / holdout profile shots: `3` / `576` / `864`
- Submitted manifest exists: `False`
- Accepted priority trace rows: `0`
- B7 dependency credit allowed: `False`
- validation_error_count: `0`

## Manifest Packet

- Submission path: `results/B2_calibration_source_manifest_submissions/B2-T5-calibration-source-manifest.json`

Required evidence files:

- calibration_source_manifest
- backend_or_dataset_access_note
- acquisition_window_source
- detector_trace_hash_manifest
- flag_event_schema_note
- confusion_matrix_or_labeling_plan
- holdout_partition_manifest
- replay_command_and_claim_boundary

Acceptance predicates:

- manifest_id equals B2-T5-calibration-source-manifest
- downstream_packet_id equals B2-T5-calibrated-flag-observation-rows
- calibration source type, backend/dataset name, acquisition window, detector trace hashes, flag schema hash, holdout partition hash, and replay command hash are present
- manifest preserves the 3-challenge / 576-trace / 864 holdout profile-shot shape or declares a reviewed replacement denominator
- source evidence files are present and hash-bound
- claim_boundary forbids production decoder, threshold, calibrated-device, hardware-result, new-code, quantum-advantage, and B7 credit claims

## Requirement Results

- P1 [PASS]: Priority calibrated-trace packet remains valid and blocked only on P6/P7/P8
- P2 [PASS]: Source manifest is bound to the calibrated flag observation row packet
- P3 [PASS]: Manifest packet carries locked schema and evidence file classes
- P4 [PASS]: Existing B2 trace denominator shape is preserved
- P5 [PASS]: B7 dependency credit remains blocked before calibrated source evidence
- P6 [FAIL]: Calibration source manifest artifact has been submitted
- P7 [FAIL]: Submitted manifest satisfies the locked source schema
- P8 [FAIL]: Submitted manifest is source-backed, downstream-bound, and replay-bound
- P9 [PASS]: Forbidden decoder, threshold, hardware, advantage, and B7-credit claims remain false

## Claim Boundary

- Supported: The B2 calibrated-trace route now has a concrete source-manifest packet that must be accepted before calibrated flag observation rows or B7 dependency credit can be considered.
- Not supported: No calibration source manifest or calibrated trace row has been submitted or accepted; no production decoder, threshold, hardware result, calibrated-device result, new-code result, quantum advantage, or B7 resource credit is supported.
- Next gate: Submit B2-T5-calibration-source-manifest with calibration source type, backend/dataset name, acquisition window, detector trace hashes, flag schema hash, holdout partition hash, replay command hash, and claim boundary.
- production_decoder_claimed: False
- threshold_claimed: False
- hardware_result_claimed: False
- calibrated_device_claimed: False
- quantum_advantage_claimed: False
- b7_dependency_credit_allowed: False

## Validation

- validation_error_count: 0
