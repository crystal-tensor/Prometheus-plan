# B4/B8 R119 Private Signed Observable Bundle

## Summary

- Target: `T-B4-002t/T-B8-003x/T-B10-009l`
- Upstream target: `T-B4-002s/T-B8-003w/T-B10-009k`
- Method: `b4_b8_r119_private_observable_bundle_gate_v0`
- Status: `private_signed_observable_bundle_scoped_positive_not_soundness`
- Model status: `late_bound_signed_bundle_rejects_four_spoofer_families_on_two_entangled_tasks`
- Entangled tasks: `2`
- Trials per task/adversary: `60`
- Shots per trial: `4096`
- Bundle size: `3` (one hidden negative target plus two positive targets)
- Minimum honest completeness: `0.85`
- Maximum adversary soundness: `0.03333333333333333`
- Adversaries at or below 0.05 soundness: `8`

R119 tests the repair suggested by R118. The verifier samples all randomized
measurement data before selecting a late-bound private bundle. Each bundle
contains one randomly selected negative-expectation correlation, a fixed
cross-half positive correlation, and one additional positive correlation. On
the two ideal six-qubit entangled tasks,
the honest sampler remains above the diagnostic floor and four spoofer families
are rejected in this scoped experiment.

This is a local positive route, not protocol soundness. The target family is
small, ideal, and simulator-generated; no hardware, calibrated backend,
cryptographic, sampling-hardness, quantum-advantage, or BQP claim follows.

## Requirements

- `P1` PASS: R118 diagnostic boundary is consumed
- `P2` PASS: two entangled state-preparation circuits are materialized
- `P3` PASS: bundle selection occurs after measurement data collection
- `P4` PASS: every bundle contains one negative and two positive targets including a cross-half anchor
- `P5` PASS: honest completeness stays above the 0.80 floor
- `P6` PASS: all four tested spoofer families stay at or below 0.05
- `P7` PASS: target selection and per-task adversary rows are materialized
- `P8` PASS: R119 remains scoped to ideal simulator data
- `P9` PASS: B4/B8/B10 soundness and BQP credit remain unclaimed
- `P10` PASS: next cross-device and noise gate is explicit

## Claim Boundary

Supported: late-bound signed observable bundles reject the tested uniform,
marginal, public-all-plus, and leaked-half spoofers on two ideal entangled
six-qubit tasks while preserving the recorded honest-completeness floor. Not
supported: general protocol soundness, arbitrary quantum states, hardware
execution, calibrated noise, cryptographic soundness, sampling hardness,
quantum advantage, BQP separation, or full-distribution verification.
