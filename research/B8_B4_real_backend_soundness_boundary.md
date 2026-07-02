# B8/B4 Real-Backend Soundness Boundary

Status: `b8_b4_real_backend_soundness_boundary_synced`

## Summary

- Method: `b8_b4_real_backend_soundness_boundary_v0`
- Boundary: `B8-B4-real-backend-soundness-boundary`
- Boundary hash: `83164aa6bca39fbb553738e94d6f8afdf79aaadd7eebda533cab97df1502fc1d`
- Source acceptance packet: `B4B8-M6-real-backend-transcript-row-acceptance-packet`
- Source acceptance packet hash: `d12e99b601c261d198a9ecdde701c7bf8298eb27b25c1620761db5593d4e4c67`
- Transcript packet: `B4B8-M6-real-backend-transcript-rows`
- Replay-validation manifest: `B4B8-M6-real-backend-transcript-replay-validation-manifest`
- Requirements passed/failed: `7` / `0`
- Failed requirement IDs: `[]`
- Source failed acceptance IDs: `['P6', 'P7', 'P8']`
- Holdout rows / no-leak budget / full-leak budget: `160` / `16` / `40`
- Real-backend rows / accepted transcript rows: `0` / `0`
- B8 protocol / sampling / B10-T2 credit allowed: `False` / `False` / `False`
- validation_error_count: `0`

## Required Downstream Evidence Before B8 Soundness Credit

- submitted B4B8-M6-real-backend-transcript-row-acceptance-packet
- source-backed backend properties, circuit, job, counts, and postprocess replay
- accepted real-backend transcript rows over the locked 160-row holdout
- leakage-blind no-leak margin retest with accepts <= 16/160
- full-leak containment or explicit exclusion with accepts <= 40/160 when included
- spoofer replay against leakage-separated fitted or generative attackers
- B10 zero-credit boundary upgraded only after transcript rows are accepted
- claim boundary forbidding protocol soundness, cryptographic soundness, sampling hardness, quantum advantage, and BQP separation before acceptance

## Requirement Results

- S1 [PASS]: Source B4/B8 real-backend transcript row acceptance gate is present and current
- S2 [PASS]: Source acceptance gate remains blocked on missing submitted packet evidence
- S3 [PASS]: B8 real-backend verifier denominator scope is preserved
- S4 [PASS]: No real-backend transcript row has been accepted
- S5 [PASS]: B8/B4/B10 soundness, hardness, advantage, and BQP credits remain disabled
- S6 [PASS]: Forbidden protocol, hardness, advantage, and BQP claims remain absent
- S7 [PASS]: Boundary records downstream evidence required before B8 soundness credit

## Claim Boundary

- Supported: B8 is synchronized to the B4/B8 real-backend transcript row acceptance packet as a zero-credit protocol-soundness boundary.
- Not supported: No real-backend transcript row, protocol soundness, cryptographic soundness, sampling hardness, quantum advantage, BQP separation, or B10-T2 credit is supported.
- Next gate: Submit and accept the real-backend transcript row acceptance packet with source-backed backend properties, counts, postprocess replay, no-leak and full-leak margin retests, spoofer replay, B10 boundary, and claim boundary.
- b8_protocol_soundness_credit_allowed: False
- b8_sampling_hardness_credit_allowed: False
- b10_t2_credit_allowed: False

## Validation

- validation_error_count: 0
