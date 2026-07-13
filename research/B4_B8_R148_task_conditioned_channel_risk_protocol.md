# B4/B8 R148 Task-Conditioned Channel-Risk Holdout Protocol

- Frozen groups / hidden rows: `12` / `96`
- Three-arm executions / total shots: `288` / `589824`
- Arms: task-conditioned foreign route, target-specific R143, automatic
- Conditioned-target mean / bootstrap floors: `-0.005` / `-0.01`
- Groups above -0.02 versus target: at least `11 / 12`
- Severe rows below -0.05: at most `0`
- Each-target mean floor: `-0.01`
- Each R147 failure-group mean floor / combined severe cap: `-0.02` / `0`
- Challenge executed: `false`

## Required Simultaneous Repairs

- `FakeJakartaV2::dense_validation_complete_ising_n6`
- `FakeJakartaV2::dense_validation_xy_network_n6`
- `FakeLagosV2::dense_validation_complete_ising_n6`

The selector is frozen before challenge. It has no fitted weights: nonuniform
ideal outputs prioritize exact output-aware readout fidelity, while uniform
ideal outputs prioritize CX survival. R147 hidden rows, R147 deltas, and the
target-specific R143 identity are forbidden selector inputs.

This finite six-qubit protocol does not establish scalable exact-output
evaluation, temporal calibration transfer, another machine, real hardware,
mitigation, soundness, quantum advantage, BQP separation, a solved frontier,
or new credit.
