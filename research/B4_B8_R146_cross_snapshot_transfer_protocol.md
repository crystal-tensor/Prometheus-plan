# B4/B8 R146 Cross-Backend Snapshot Transfer Protocol

- Directional snapshot pairs: `6`
- Dense validation tasks: `4`
- Transfer groups / hidden rows: `24` / `192`
- Three-arm executions / total shots: `576` / `1179648`
- Arms: source-transfer, target-specific, automatic
- Portfolio transfer-target mean / bootstrap floors: `-0.005` / `-0.01`
- Groups above -0.02 versus target-specific: at least `20 / 24`
- Severe regressions below -0.05: at most `0`
- Each-target mean transfer-target floor: `-0.01`
- Challenge executed: `false`

Every R143 winner is transferred in both directions to the other two fake
backend snapshots. The source mapping, route policy, and realization seed are
carried unchanged but recompiled on the target. The target-specific R143 route
and a hidden-seed automatic layout form the two denominators.

This protocol tests synthetic cross-backend snapshot transfer only. It does not
represent temporal calibration drift on one device, another machine, provider
access, hardware execution, advantage, BQP separation, or new credit.
