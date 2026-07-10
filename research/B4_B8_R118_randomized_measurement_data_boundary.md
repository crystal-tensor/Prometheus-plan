# B4/B8 R118 Randomized Measurement-Data Boundary

## Summary

- Target: `T-B4-002s/T-B8-003w/T-B10-009k`
- Upstream target: `T-B4-002r/T-B8-003v/T-B10-009j`
- Method: `b4_b8_r118_randomized_measurement_data_boundary_v0`
- Status: `randomized_measurement_data_spoofer_boundary_not_soundness`
- Model status: `classical_shadow_like_data_exposes_public_and_marginal_spoofer_boundary`
- Tasks: `3` six-qubit state-preparation circuits
- Trials per task/adversary: `60`
- Shots per trial: `1024`
- Hidden target observables: `8`
- Minimum honest completeness: `0.8`
- Maximum adversary soundness: `1.0`
- Adversary rows below 0.05 soundness: `1`

R118 replaces toy parity samples with randomized Pauli-basis measurement data
and a classical-shadow-like estimator. The target observable is selected
after the measurement basis schedule is fixed, so the adversary does not
receive the selected target. Honest data remains usable, but marginal matching
and a public all-plus basis strategy expose a real verifier boundary. This is
a diagnostic negative result: randomized measurement data alone is not yet a
protocol-sound quantum-output verifier.

## Requirements

- `P1` PASS: three randomized-measurement state-preparation circuits are materialized
- `P2` PASS: random Pauli basis schedules are sampled for every trial
- `P3` PASS: hidden target observables are selected after basis schedules
- `P4` PASS: honest completeness remains above the 0.80 diagnostic floor
- `P5` PASS: uniform random spoofer is measured rather than assumed
- `P6` PASS: marginal and public-basis spoofer boundaries are surfaced
- `P7` PASS: the B8 soundness threshold is not overclaimed
- `P8` PASS: all spoofer rows and target expectations are materialized
- `P9` PASS: hardware and advantage claims remain false
- `P10` PASS: the next design gate is explicit

## Claim Boundary

Supported: a reproducible randomized-measurement data experiment that separates
honest completeness from several spoofer behaviors and identifies public/
marginal-spoofing failure modes. Not supported: hardware execution, calibrated
backend evidence, cryptographic soundness, sampling hardness, quantum
advantage, BQP separation, or full-distribution verification.
