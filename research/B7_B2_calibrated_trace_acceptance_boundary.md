# B7/B2 Calibrated Trace Acceptance Boundary

Status: `b7_b2_calibrated_trace_acceptance_boundary_synced`

## Summary

- Method: `b7_b2_calibrated_trace_acceptance_boundary_v0`
- Boundary: `B7-B2-calibrated-trace-acceptance-boundary`
- Boundary hash: `b915a35d2e1e7b78440b277d23905b2fd34433350b27ee237ad61b4a2a932828`
- Source acceptance packet: `B2-T5-calibrated-trace-row-acceptance-packet`
- Source acceptance packet hash: `3cf42ae6e29cf23f20120a5d48db83efa510db007f24ec9b62fc9660ef8420c3`
- Trace packet: `B2-T5-calibrated-flag-observation-rows`
- Replay-validation manifest: `B2-T5-calibrated-trace-row-replay-validation-manifest`
- Challenge count / source traces / holdout profile shots: `3` / `576` / `864`
- Requirements passed/failed: `7` / `0`
- Failed requirement IDs: `[]`
- Source failed acceptance IDs: `['P6', 'P7', 'P8']`
- Submitted acceptance packet exists: `False`
- Accepted priority trace rows: `0`
- B7 dependency / FT ledger / resource credit allowed: `False` / `False` / `False`
- B7 credit delta / STV credit / logical-error credit: `0` / `0` / `0`
- validation_error_count: `0`

## Required Downstream Evidence Before B7 Credit

- submitted B2-T5-calibrated-trace-row-acceptance-packet
- source-backed row batch, detector trace, decoder profile, posterior, prediction, and holdout artifacts
- positive accepted_trace_row_count
- all-challenge non-regression proof
- real or independently calibrated trace replay
- strict holdout improvement under the same decoder path
- B7 zero-credit boundary note updated to a nonzero-credit acceptance ledger
- claim boundary that still forbids decoder, threshold, hardware-result, calibrated-device, quantum-advantage, and unpriced FT-resource claims

## Requirement Results

- S1 [PASS]: Source B2 calibrated trace acceptance packet gate is present and current
- S2 [PASS]: Source acceptance gate remains blocked on missing submitted packet evidence
- S3 [PASS]: B2 calibrated trace scope is preserved for the B7 dependency view
- S4 [PASS]: No calibrated rows have been accepted for B7 dependency credit
- S5 [PASS]: B7 FT ledger and resource credit remain explicitly disabled
- S6 [PASS]: Forbidden decoder, threshold, hardware, advantage, and FT-resource claims remain absent
- S7 [PASS]: Boundary records the downstream evidence required before B7 can count credit

## Claim Boundary

- Supported: B7 is now explicitly synchronized to the B2 calibrated trace row acceptance packet as a zero-credit dependency boundary.
- Not supported: No calibrated B2 row, FT ledger improvement, logical error improvement, space-time-volume reduction, hardware result, threshold result, quantum advantage, or B7 resource credit is supported.
- Next gate: Submit and accept the B2 calibrated trace row acceptance packet, then provide source-backed accepted rows, all-challenge non-regression, real or independently calibrated replay, strict holdout improvement, and a nonzero B7 credit ledger before B7 can count dependency credit.
- b7_dependency_credit_allowed: False
- b7_ft_ledger_credit_allowed: False
- b7_resource_credit_allowed: False

## Validation

- validation_error_count: 0
