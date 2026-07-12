# B4/B8 R142 Seed-Robust LCB Mapping Design

## Design Result

- R141 candidates read: `1536`
- Unique-QASM shortlist: `96` across `12` groups
- Noisy design executions / shots: `1728` / `3538944`
- Groups with positive selected lower confidence bound: `8 / 12`
- Selections changed from R140 exact: `10`
- Lagos selected mapping: `[5, 3, 6, 4, 1, 0]`
- Lagos mean / LCB / wins: `+0.01062521` / `+0.00523438` / `12 of 16`
- R141 holdout rows read during selection: `0`
- Selected OpenQASM 3 replay: `12 / 12`
- New credit delta: `0`

R142 first uses the frozen R141 sample-sketch score to retain the eight best
unique QASM candidates per group. It then evaluates those fixed candidates and
a same-seed automatic compilation on sixteen disjoint design seeds at 2,048
shots. Selection maximizes `mean_delta - 1.96 * standard_error`, with no fitted
coefficient and no access to R141 holdout rows.

This is an intentionally expensive design denominator. It tests whether
lower-tail pressure changes the mapping choice before a fresh hidden holdout;
it is not yet an efficient production mapper.

## Group Evidence

- `FakeJakartaV2` / `dense_validation_complete_ising_n6`: selected mapping `[3, 1, 5, 2, 0, 6]`, mean/LCB vs automatic `+0.01226384` / `+0.00712580`, wins `12 / 16`, changed from R140 `True`.
- `FakeJakartaV2` / `dense_validation_inverse_qft_n6`: selected mapping `[0, 2, 3, 5, 1, 6]`, mean/LCB vs automatic `+0.00059462` / `-0.00013972`, wins `9 / 16`, changed from R140 `True`.
- `FakeJakartaV2` / `dense_validation_scrambled_qft_n6`: selected mapping `[5, 3, 1, 6, 2, 0]`, mean/LCB vs automatic `-0.00004777` / `-0.00054492`, wins `5 / 16`, changed from R140 `True`.
- `FakeJakartaV2` / `dense_validation_xy_network_n6`: selected mapping `[0, 1, 3, 2, 5, 6]`, mean/LCB vs automatic `+0.02931102` / `+0.02566568`, wins `16 / 16`, changed from R140 `False`.
- `FakeLagosV2` / `dense_validation_complete_ising_n6`: selected mapping `[5, 3, 6, 4, 1, 0]`, mean/LCB vs automatic `+0.01062521` / `+0.00523438`, wins `12 / 16`, changed from R140 `True`.
- `FakeLagosV2` / `dense_validation_inverse_qft_n6`: selected mapping `[4, 5, 0, 2, 3, 1]`, mean/LCB vs automatic `-0.00000232` / `-0.00070608`, wins `8 / 16`, changed from R140 `True`.
- `FakeLagosV2` / `dense_validation_scrambled_qft_n6`: selected mapping `[5, 1, 0, 4, 3, 2]`, mean/LCB vs automatic `+0.00157168` / `+0.00043371`, wins `12 / 16`, changed from R140 `True`.
- `FakeLagosV2` / `dense_validation_xy_network_n6`: selected mapping `[6, 4, 5, 3, 1, 0]`, mean/LCB vs automatic `+0.00786415` / `+0.00258159`, wins `12 / 16`, changed from R140 `False`.
- `FakeOslo` / `dense_validation_complete_ising_n6`: selected mapping `[3, 1, 5, 0, 2, 4]`, mean/LCB vs automatic `+0.01059568` / `+0.00722640`, wins `13 / 16`, changed from R140 `True`.
- `FakeOslo` / `dense_validation_inverse_qft_n6`: selected mapping `[2, 1, 4, 6, 3, 5]`, mean/LCB vs automatic `+0.00051652` / `+0.00001822`, wins `11 / 16`, changed from R140 `True`.
- `FakeOslo` / `dense_validation_scrambled_qft_n6`: selected mapping `[5, 2, 1, 4, 0, 3]`, mean/LCB vs automatic `+0.00019288` / `-0.00021002`, wins `10 / 16`, changed from R140 `True`.
- `FakeOslo` / `dense_validation_xy_network_n6`: selected mapping `[0, 2, 1, 3, 5, 4]`, mean/LCB vs automatic `+0.03001417` / `+0.02592042`, wins `16 / 16`, changed from R140 `True`.

## Requirements

- `R1` PASS: all 1,536 R141 design candidates are available before shortlisting
- `R2` PASS: each group has eight unique-QASM shortlist candidates
- `R3` PASS: sixteen fixed design seeds and 2,048 shots are disclosed
- `R4` PASS: 1,728 executions and 3,538,944 shots are fully disclosed
- `R5` PASS: Lagos selected lower confidence bound is positive
- `R6` PASS: Lagos selected route wins at least twelve of sixteen design rows
- `R7` PASS: all shortlisted circuits retain exact semantic fidelity
- `R8` PASS: all twelve selected OpenQASM 3 files replay
- `R9` PASS: R141 hidden holdout rows remain unread and no hidden R142 holdout runs
- `R10` PASS: production efficiency, hardware, advantage, BQP, and credit claims remain false

## Claim Boundary

Supported: a frozen portfolio of lower-confidence-bound mapping choices from a
disjoint synthetic design block. Not supported: hidden-seed acceptance,
efficient production selection, current calibration, real hardware,
mitigation, soundness, quantum advantage, BQP separation, solved B4/B8/B10, or
new credit.
