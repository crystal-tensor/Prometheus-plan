# B2 Calibrated Evidence Contract Gate v0.1

Status: **calibrated_evidence_contract_open_missing_hardware_data**

## Summary

- Method: b2_calibrated_evidence_contract_gate_v0
- Model status: calibration_transfer_blockers_decomposed_for_data_prs
- Source guardrail method: b2_calibration_transfer_guardrail_gate_v0
- Source missing gates: C4, C5, C6
- Source challenge count / trace count: 3 / 576
- Observation profiles / profile rows: 3 / 9
- Total profile shots / holdout shots: 1728 / 864
- Best profile: conservative_hardware_like_leakage
- Best-profile model flag events: 415
- Stress-profile model flag events: 727
- Best-profile holdout baseline / injected / delta: 16 / 16 / 0
- Contract requirements passed / failed: 5 / 3
- Failed contract requirement ids: K4, K5, K6
- Contract packets: B2-C4-calibrated-flag-data, B2-C5-hardware-trace-replay, B2-C6-holdout-improvement
- Data contract ready for PRs: True
- Calibration transfer ready: False
- Production decoder ready: False
- Threshold claim supported: False
- Validation errors: []

## Contract Requirements

| gate | passed | label | PR packet | acceptance rule |
|---|---:|---|---|---|
| K1 | True | Source guardrail is a valid negative calibration-transfer boundary | source-audit | The source guardrail must stay valid and fail only C4/C5/C6. |
| K2 | True | Replayable per-shot trace schema remains available | trace-schema | Keep at least the current three-challenge / 576-trace replay shape. |
| K3 | True | PR packets exist for every failed calibration-transfer gate | packet-index | Every failed blocker must map to a concrete PR packet. |
| K4 | False | Calibrated flag-data packet has been satisfied | B2-C4-calibrated-flag-data | Submit calibrated leakage/erasure flag observations with confusion metadata. |
| K5 | False | Real hardware trace-replay packet has been satisfied | B2-C5-hardware-trace-replay | Submit real or independently calibrated hardware traces replayed by the same decoder. |
| K6 | False | Holdout improvement packet has been satisfied | B2-C6-holdout-improvement | Show strictly fewer holdout logical failures under calibrated injection. |
| K7 | True | Holdout non-regression remains preserved | holdout-nonregression | Keep non-regression true after C4/C5 data are introduced. |
| K8 | True | Forbidden production, threshold, hardware, and advantage claims remain absent | claim-boundary | Do not promote B2 until K4-K6 pass under replayable evidence. |

## PR Packets

### B2-C4-calibrated-flag-data

- Blocks gate: K4
- Owner role: hardware_data_or_calibration_agent
- Acceptance rule: calibrated_flag_data_used must become true without changing the per-shot decoder interface or claiming hardware advantage.
- Required artifacts:
  - per-shot detector bitstrings using the existing B2 trace schema
  - per-shot observable bitstrings or logical labels
  - detector-tick-indexed leakage/erasure/flag events
  - calibrated flag confusion matrix with provenance
  - calibration date, backend family, noise slice, and shot count metadata

### B2-C5-hardware-trace-replay

- Blocks gate: K5
- Owner role: hardware_trace_replay_agent
- Acceptance rule: real_hardware_trace_used must become true and replay must produce the same summary fields as the current guardrail.
- Required artifacts:
  - independent real or provider-calibrated trace rows
  - same decoder replay command used for synthetic B2 traces
  - source-to-result trace hash ledger
  - explicit separation between calibration, model-selection, and holdout slices

### B2-C6-holdout-improvement

- Blocks gate: K6
- Owner role: decoder_baseline_adversary_agent
- Acceptance rule: best_profile_holdout_injected_failures must be strictly lower than the current baseline 16 while introduced failures remain zero.
- Required artifacts:
  - strict holdout baseline logical failure count
  - strict holdout injected logical failure count
  - all-challenge non-regression table
  - runtime and changed-prediction audit
  - negative-control profile where flags are shuffled or withheld

## Claim Boundary

- calibrated_evidence_contract_built: True
- calibration_transfer_ready: False
- production_decoder_claimed: False
- threshold_claimed: False
- new_code_claimed: False
- hardware_result_claimed: False
- calibrated_device_claimed: False
- quantum_advantage_claimed: False
- what_is_supported: B2 now has explicit PR packets for the three blockers that prevent calibration transfer: calibrated flag data, real or independently calibrated hardware traces, and strict holdout improvement with non-regression.
- what_is_not_supported: No new calibrated flag data, real hardware trace, holdout improvement, production decoder, threshold, or low-overhead QEC claim is established by this contract gate.

## Next Gate

A future B2 PR must satisfy K4-K6 together: calibrated flag data,
real or independently calibrated hardware trace replay, and strictly
lower holdout logical failures with non-regression preserved. Until
then, B2 remains a disciplined negative boundary rather than a
low-overhead QEC claim.
