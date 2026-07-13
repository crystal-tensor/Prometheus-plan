# B4/B8 R148 Task-Conditioned Channel-Risk Design

- Groups / foreign candidates: `12` / `24`
- Readout-first / CX-first groups: `6` / `6`
- Selections changed from R147: `4`
- Target-specific routes in selector: `0`
- R147 hidden rows read: `0`
- Fitted weights: `0`
- Candidate semantic passes: `24 / 24`
- Holdout executed: `false`

## Frozen Selections

- `FakeJakartaV2` / `dense_validation_complete_ising_n6`: `readout_first`, selected `FakeOslo`, prior `FakeLagosV2`, changed `true`.
- `FakeJakartaV2` / `dense_validation_inverse_qft_n6`: `cx_first`, selected `FakeOslo`, prior `FakeOslo`, changed `false`.
- `FakeJakartaV2` / `dense_validation_scrambled_qft_n6`: `cx_first`, selected `FakeLagosV2`, prior `FakeLagosV2`, changed `false`.
- `FakeJakartaV2` / `dense_validation_xy_network_n6`: `readout_first`, selected `FakeOslo`, prior `FakeLagosV2`, changed `true`.
- `FakeLagosV2` / `dense_validation_complete_ising_n6`: `readout_first`, selected `FakeJakartaV2`, prior `FakeOslo`, changed `true`.
- `FakeLagosV2` / `dense_validation_inverse_qft_n6`: `cx_first`, selected `FakeOslo`, prior `FakeOslo`, changed `false`.
- `FakeLagosV2` / `dense_validation_scrambled_qft_n6`: `cx_first`, selected `FakeOslo`, prior `FakeOslo`, changed `false`.
- `FakeLagosV2` / `dense_validation_xy_network_n6`: `readout_first`, selected `FakeOslo`, prior `FakeOslo`, changed `false`.
- `FakeOslo` / `dense_validation_complete_ising_n6`: `readout_first`, selected `FakeJakartaV2`, prior `FakeJakartaV2`, changed `false`.
- `FakeOslo` / `dense_validation_inverse_qft_n6`: `cx_first`, selected `FakeLagosV2`, prior `FakeLagosV2`, changed `false`.
- `FakeOslo` / `dense_validation_scrambled_qft_n6`: `cx_first`, selected `FakeJakartaV2`, prior `FakeLagosV2`, changed `true`.
- `FakeOslo` / `dense_validation_xy_network_n6`: `readout_first`, selected `FakeJakartaV2`, prior `FakeJakartaV2`, changed `false`.

## Method Boundary

Uniform ideal outputs are invariant under symmetric bit-flip readout, so their
selector prioritizes compiled CX survival. Nonuniform ideal outputs expose
logical-bit placement to physical readout asymmetry, so their selector
prioritizes exact output-aware readout fidelity and uses CX survival only as a
tie break. The rule has no fitted weight, excludes target-specific routes, and
does not load any R147 hidden row.

This finite six-qubit design does not support scalable exact-output evaluation,
a holdout improvement, temporal or cross-machine transfer, real hardware,
mitigation, soundness, quantum advantage, BQP separation, a solved frontier,
or new credit.
