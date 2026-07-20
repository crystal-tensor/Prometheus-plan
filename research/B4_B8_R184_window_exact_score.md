# B4/B8/B10 R184 Windowed Exact-Score Experiment

- Status: `window_exact_score_complete_independent_oracle_pending`
- Result payload hash: `5b9d5e7f21ffaefb681a2115268242fcecb2d488411817083d278c8fa1f53022`
- Requirements: `11/12` passed; P10 awaits the independent oracle

## Three-Arm Measurement

R184 completed `468` same-process BigUint/prefix/window triplets across `13` isolated workers and `13` cells. All three timing arms plus the separate window probe preserve the expected mapping on `468/468` triplets.

## Frozen Classifications

- H1: `all_timing_and_probe_mappings_exact`; mapping integrity `True`.
- H2: `compact_path_observed_without_fallback`; maximum compact limbs `2`, object size `40` bytes, fallback transitions `0`, wide combines `0`.
- H3: `window_materially_faster_than_prefix_reference`; paired window/prefix median ratio `0.771535` against the frozen `0.90` threshold.
- H4: `window_competitive_with_biguint`; paired window/BigUint median ratio `0.814726` against the frozen `1.00` threshold; all-order coverage `True`.

## Claim Boundary

P10 remains pending until the stdlib-only oracle independently recomputes every artifact hash, mapping outcome, counter boundary, paired ratio, workload count, and frozen classification. This experiment does not establish a full-domain performance theorem, production Qiskit remedy, hardware behavior, quantum advantage, BQP separation, a solved frontier, or new credit.
