# B4/B8 R120 Private Bundle Noise Replay

## Summary

- Target: `T-B4-002u/T-B8-003y/T-B10-009m`
- Upstream target: `T-B4-002t/T-B8-003x/T-B10-009l`
- Method: `b4_b8_r120_private_bundle_noise_replay_v0`
- Status: `private_signed_observable_bundle_noise_margin_boundary`
- Model status: `r119_bundle_honest_noise_margin_replayed_with_explicit_aer_profiles`
- Tasks: `2` ideal six-qubit entangled tasks
- Trials per profile/task: `20`
- Shots per trial: `1024`
- Bundle size: `3`
- Fixed estimator tolerance: `0.6`
- Profiles above the `0.8` honest floor: `0/4`

Profile results:

- `ideal`: minimum honest completeness `0.75`, maximum bundle error `1.1357421875000002`
- `light`: minimum honest completeness `0.45`, maximum bundle error `1.1357421875000002`
- `moderate`: minimum honest completeness `0.6`, maximum bundle error `1.1357421875000002`
- `stress`: minimum honest completeness `0.55`, maximum bundle error `1.7119140624999998`

R120 replays the R119 private signed bundle under explicit Qiskit Aer
depolarizing and readout-noise profiles at a fixed 1,024-shot budget. The
noise-free profile is retained as a sampling baseline: if it misses the R119
floor, the implementation must not blame hardware noise alone. The R119 ideal
adversary result is carried as a dependency, not silently re-run as a new
soundness proof. No profile is treated as calibrated hardware evidence.

## Requirements

- `P1` PASS: accepted R119 bundle is consumed
- `P2` PASS: four explicit Aer noise profiles are replayed
- `P3` PASS: same three-observable bundle contract is retained
- `P4` PASS: noise-free profile is materialized as the sampling baseline
- `P5` PASS: noise margin is reported per profile rather than averaged away
- `P6` PASS: no noise profile is mislabeled as calibrated hardware evidence
- `P7` PASS: R119 adversary result is carried without a new soundness claim
- `P8` PASS: all profile circuits and rows are materialized
- `P9` PASS: B4/B8/B10 advantage and BQP claims remain false
- `P10` PASS: next gate is independent backend or calibrated transcript

## Claim Boundary

Supported: an explicit simulator noise-margin ledger for the R119 private
bundle. Not supported: calibrated backend evidence, real hardware execution,
general protocol soundness, cryptographic soundness, sampling hardness,
quantum advantage, BQP separation, or full-distribution verification.
