# B4/B8 R132 Topology-Constrained Route Policy

## Result

- Training compilations: `240`
- Validation compilations: `180`
- Selected global policy: `selected_o3_lookahead`
- Validation groups with one route-exposure class: `6` / `6`
- Validation groups with one exact QASM hash: `6` / `6`
- Frozen constrained-QASM replay matches: `60` / `60`
- Groups non-regressing in mean exposure vs selected default: `6` / `6`
- Groups non-regressing at the lower tail vs selected default: `6` / `6`
- Groups robust over automatic default: `3` / `6`
- Stability gate passed: `True`
- Verifier acceptance performed: `False`
- New credit delta: `0`

## Validation Evidence

- `FakeJakartaV2` / `private_bundle_ghz_n6`: constrained classes/QASM hashes `1/1`; mean gain vs selected/default `+0.019742/-0.002336`; lower-tail gain vs selected `+0.014149`; default wins/ties/losses `2/0/8`; exact seed invariant `True`.
- `FakeJakartaV2` / `private_bundle_graph_n6`: constrained classes/QASM hashes `1/1`; mean gain vs selected/default `+0.012595/+0.008060`; lower-tail gain vs selected `+0.000000`; default wins/ties/losses `5/5/0`; exact seed invariant `True`.
- `FakeLagosV2` / `private_bundle_ghz_n6`: constrained classes/QASM hashes `1/1`; mean gain vs selected/default `+0.010478/+0.005644`; lower-tail gain vs selected `+0.010478`; default wins/ties/losses `5/4/1`; exact seed invariant `True`.
- `FakeLagosV2` / `private_bundle_graph_n6`: constrained classes/QASM hashes `1/1`; mean gain vs selected/default `+0.000000/+0.004280`; lower-tail gain vs selected `+0.000000`; default wins/ties/losses `5/5/0`; exact seed invariant `True`.
- `FakeOslo` / `private_bundle_ghz_n6`: constrained classes/QASM hashes `1/1`; mean gain vs selected/default `+0.000000/+0.000501`; lower-tail gain vs selected `+0.000000`; default wins/ties/losses `5/0/5`; exact seed invariant `True`.
- `FakeOslo` / `private_bundle_graph_n6`: constrained classes/QASM hashes `1/1`; mean gain vs selected/default `+0.000000/+0.006861`; lower-tail gain vs selected `+0.000000`; default wins/ties/losses `5/5/0`; exact seed invariant `True`.

The selected policy is chosen once, globally, from the fresh R132 training block.
The policy fixes each workload's upstream R130 topology mapping and constrains the
router to Qiskit's `lookahead` method. The disjoint validation block is not read
during selection. Exact QASM invariance is tested both across ten validation
seeds and by replaying frozen files in a fresh process.

## Requirements

- `P1` PASS: R130 and R131 sources are hash-bound and required
- `P2` PASS: fresh training and validation seeds are disjoint from R130/R131
- `P3` PASS: global policy is selected only from the training ledger
- `P4` PASS: all six validation groups use one route-exposure class
- `P5` PASS: all six validation groups use one exact QASM hash across seeds
- `P6` PASS: all 60 frozen constrained circuits match in a fresh process
- `P7` PASS: mean and lower-tail exposure do not regress against selected default
- `P8` PASS: training, validation, and frozen-artifact ledgers are complete
- `P9` PASS: verifier acceptance, mitigation, calibration, and hardware remain excluded
- `P10` PASS: no soundness, advantage, BQP, or new credit is claimed

## Claim Boundary

Supported: a fresh-seed compiler result showing whether a fixed topology mapping
plus a globally selected routing policy removes the R131 route-family instability
without regressing the selected-layout exposure proxy. Not supported: verifier
holdout acceptance, causal hardware performance, current calibration, readout
mitigation, protocol soundness, quantum advantage, BQP separation, or new B10 credit.
