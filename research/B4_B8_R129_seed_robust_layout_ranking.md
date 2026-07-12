# B4/B8 R129 Seed-Robust Layout Ranking

## Result

- Training seeds: `8`
- Unseen validation seeds: `10`
- Candidate training compilations: `480`
- Total same-condition compilations: `708`
- Selectors changed from R128: `1` / `6`
- Groups with positive unseen mean delta: `4` / `6`
- Groups with positive unseen lower-20% delta: `1` / `6`
- Groups winning at least 8/10 unseen seeds: `1` / `6`
- Robust unseen-seed gate passed: `False`
- Acceptance holdout executed: `False`
- New credit delta: `0`

## Per-Group Evidence

- `FakeJakartaV2` / `private_bundle_ghz_n6`: robust static rank `5` mapping `[1, 5, 2, 0, 3, 6]`; train lower-20%/wins `-0.0159` / `2/8`; unseen lower-20%/mean/wins `-0.0153` / `-0.0074` / `3/10`; R128 unseen mean/wins `-0.0090` / `3/10`; selector changed `True`.
- `FakeJakartaV2` / `private_bundle_graph_n6`: robust static rank `2` mapping `[2, 1, 0, 3, 5, 6]`; train lower-20%/wins `-0.0000` / `5/8`; unseen lower-20%/mean/wins `-0.0000` / `0.0022` / `6/10`; R128 unseen mean/wins `0.0022` / `6/10`; selector changed `False`.
- `FakeLagosV2` / `private_bundle_ghz_n6`: robust static rank `1` mapping `[3, 0, 1, 4, 5, 6]`; train lower-20%/wins `-0.0075` / `1/8`; unseen lower-20%/mean/wins `-0.0075` / `0.0095` / `2/10`; R128 unseen mean/wins `0.0095` / `2/10`; selector changed `False`.
- `FakeLagosV2` / `private_bundle_graph_n6`: robust static rank `1` mapping `[6, 5, 4, 3, 1, 0]`; train lower-20%/wins `0.0029` / `8/8`; unseen lower-20%/mean/wins `0.0057` / `0.0064` / `10/10`; R128 unseen mean/wins `0.0064` / `10/10`; selector changed `False`.
- `FakeOslo` / `private_bundle_ghz_n6`: robust static rank `9` mapping `[3, 5, 4, 0, 1, 2]`; train lower-20%/wins `-0.0032` / `3/8`; unseen lower-20%/mean/wins `-0.0032` / `-0.0007` / `5/10`; R128 unseen mean/wins `-0.0007` / `5/10`; selector changed `False`.
- `FakeOslo` / `private_bundle_graph_n6`: robust static rank `2` mapping `[0, 1, 2, 3, 5, 4]`; train lower-20%/wins `0.0000` / `5/8`; unseen lower-20%/mean/wins `0.0000` / `0.0024` / `6/10`; R128 unseen mean/wins `0.0024` / `6/10`; selector changed `False`.

The selector is fit only on eight declared training seeds. It maximizes the
20th-percentile paired exposure gain over automatic layout, then training wins,
mean gain, candidate worst exposure, mean CX count, static rank, and mapping.
Ten disjoint validation seeds are compiled only after selection. The R128
mean selector is replayed on the same validation seeds as a frozen reference.

## Gate

Every group must have positive unseen mean and lower-20% exposure deltas and
win at least eight of ten unseen seeds. This is a compiler-design validation
gate, not the R125 verifier acceptance holdout. Passing it would authorize a
separate preregistration step; it would not itself create B4, B8, or B10 credit.

## Requirements

- `P1` PASS: R127 and R128 sources are hash-bound before R129 selection
- `P2` PASS: training and unseen validation transpiler seeds are disjoint
- `P3` PASS: all 60 retained candidates are trained on all eight training seeds
- `P4` PASS: selection uses lower-tail paired gain before mean exposure
- `P5` PASS: ten unseen seeds are evaluated for selected, default, and R128 layouts
- `P6` PASS: all 60 selected validation QASM artifacts preserve measurement order
- `P7` PASS: the robust unseen-seed gate is evaluated on all six groups
- `P8` PASS: R125 acceptance rows, verifier holdout, and mitigation remain excluded
- `P9` PASS: historical snapshots remain separate from current and hardware evidence
- `P10` PASS: no soundness, advantage, BQP, or new credit is claimed

## Claim Boundary

Supported: a deterministic train/validation test of lower-tail transpiler-seed
layout ranking over the 60 predeclared R127 candidates. Not supported: verifier
holdout performance, readout mitigation, current calibration, provider access,
hardware execution, protocol soundness, quantum advantage, BQP separation, or
new B10 credit.
