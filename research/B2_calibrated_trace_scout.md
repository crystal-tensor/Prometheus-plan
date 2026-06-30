# B2 Calibrated Trace Scout v0.1

Status: **calibrated_trace_scout_failed_missing_real_calibration**

## Summary

- Method: `b2_calibrated_trace_scout_v0`
- Model status: `synthetic_trace_and_hardware_like_profiles_mapped_not_calibrated_decoder`
- Requirements passed/failed: 5 / 3
- Failed requirement IDs: S5, S6, S7
- Synthetic trace rows: 576
- Challenge trace hashes: 3
- Synthetic flag events: 482
- Hardware-like profile results: 9
- Holdout profile shots: 864
- Best holdout baseline/injected/delta: 16 / 16 / 0
- Calibrated flag observation rows: 0
- Real hardware trace rows: 0
- Strict holdout improvement rows: 0

## Requirement Results

- S1 [PASS]: Calibrated-evidence contract source remains valid and open on K4-K6
- S2 [PASS]: Per-shot synthetic trace packet is replayable
- S3 [PASS]: Hardware-like model profiles are mapped to challenge rows
- S4 [PASS]: Synthetic flag and hardware-like model pressure are visible
- S5 [FAIL]: Calibrated leakage/flag observation rows are present
- S6 [FAIL]: Real or independently calibrated hardware trace rows are present
- S7 [FAIL]: Strict holdout improvement is demonstrated
- S8 [PASS]: Forbidden claims remain false and synthetic traces are not promoted

## Claim Boundary

- Supported: The existing synthetic trace fixture and hardware-like profile results are now mapped row by row to the B2 calibrated-evidence contract.
- Not supported: This is not calibrated leakage data, not real hardware trace replay, not strict holdout improvement, not a production decoder, not a threshold result, and not a hardware claim.
- Next gate: Submit B2-C4 calibrated flag data, B2-C5 hardware trace replay, and B2-C6 strict holdout improvement without changing the per-shot trace schema.
