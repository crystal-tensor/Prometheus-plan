# B2 Calibrated Trace Intake Template Gate

Status: **calibrated_trace_intake_template_open_missing_rows**

## Summary

- Method: `b2_calibrated_trace_intake_template_gate_v0`
- Model status: `calibrated_trace_schema_and_holdout_packets_built_no_calibrated_rows`
- Intake requirements passed/failed: 5 / 3
- Failed intake requirement IDs: ['T5', 'T6', 'T7']
- Contract blockers: ['K4', 'K5', 'K6']
- Trace-scout blockers: ['S5', 'S6', 'S7']
- Challenge count / source traces: 3 / 576
- Holdout profile shots: 864
- Required row keys / production-required keys: 21 / 10
- Template table hash: `f69b48097c5c42df7a00ede62f98ded12127a1f32b8274dc3f0a4d1c6cbf8f61`
- Calibrated flag rows / real hardware rows / strict improvement rows: 0 / 0 / 0

## Intake Packets

| Packet | Blocks contract | Blocks scout | Owner | Submitted rows | Accepted rows | Ready |
|---|---|---|---|---:|---:|---|
| B2-T5-calibrated-flag-observation-rows | K4 | S5 | hardware_data_or_calibration_agent | 0 | 0 | False |
| B2-T6-real-or-independent-trace-replay | K5 | S6 | hardware_trace_replay_agent | 0 | 0 | False |
| B2-T7-strict-holdout-improvement | K6 | S7 | decoder_baseline_adversary_agent | 0 | 0 | False |

## Trace Row Schema

trace_id, challenge_id, challenge_trace_hash, backend_or_calibration_source, backend_properties_hash, shot_index, detector_bitstring_hash, observable_bit, calibrated_flag_events_hash, flag_confusion_matrix_hash, leakage_rate_per_tick, false_positive_rate_per_tick, decoder_profile, baseline_prediction, injected_prediction, logical_label, holdout_partition, decoder_runtime_seconds, raw_trace_artifact_sha256, postprocess_script_sha256, claim_boundary

## Requirement Results

- T1 [PASS]: Calibrated evidence contract is open on K4-K6
- T2 [PASS]: Trace scout is open on S5-S7 and preserves synthetic-only boundaries
- T3 [PASS]: Three calibrated-trace intake packets map one-to-one to blockers
- T4 [PASS]: Trace row schema is explicit and hashable
- T5 [FAIL]: Submitted calibrated trace rows are present
- T6 [FAIL]: Accepted calibrated trace rows cover all packets
- T7 [FAIL]: Calibration retest is ready
- T8 [PASS]: Forbidden production, threshold, hardware, and advantage claims remain false

## Claim Boundary

- Supported: The open B2 calibration blockers K4/S5, K5/S6, and K6/S7 are converted into hashable calibrated-trace intake packets with explicit row keys.
- Not supported: No calibrated rows are submitted or accepted, no calibration retest is ready, and there is no production decoder, threshold, hardware, new-code, or quantum-advantage claim.
- Next gate: Submit calibrated flag rows, real or independently calibrated trace replay rows, and strict holdout-improvement evidence while preserving the 3-challenge / 576-trace shape.
- production_decoder_claimed: False
- threshold_claimed: False
- hardware_result_claimed: False
- quantum_advantage_claimed: False

## Validation

- validation_error_count: 0
