# B4/B8 R149 Jakarta Dense-XY Generated-Route Portfolio Protocol

- Portfolio groups / hidden rows: `12` / `96`
- Executions / total shots: `296` / `606208`
- Replacement group: `FakeJakartaV2::dense_validation_xy_network_n6`
- Portfolio repaired-target mean / bootstrap floors: `-0.005` / `-0.01`
- Groups above -0.02 versus target: `12 / 12`
- Severe rows below -0.05: at most `0`
- Replacement repaired-target floor: `-0.02`
- Replacement repaired-R148-foreign improvement floor: `0.01`
- Challenge executed: `false`

The R149 generated route replaces only Jakarta dense XY. The other 11 groups
retain the frozen R148 routes, so the challenge can detect collateral portfolio
regression. The residual group additionally replays the old R148 foreign route
under the same row seed and must improve by at least +0.01.

This protocol does not establish a holdout repair, general route-generation
advantage, temporal or cross-machine transfer, real hardware, mitigation,
soundness, quantum advantage, BQP separation, a solved frontier, or new credit.
