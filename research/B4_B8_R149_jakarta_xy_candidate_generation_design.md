# B4/B8 R149 Jakarta Dense-XY Candidate Generation Design

- Enumerated / excluded / eligible mappings: `5040` / `3` / `5037`
- Shortlist mappings / compiled candidates: `12` / `48`
- Selection / diagnostic / total executions: `264` / `32` / `296`
- Total design shots: `606208`
- Selected candidate: `m5-6-1-0-3-2__selected_o3_default__s14902`
- Selected mapping / policy / seed: `[5, 6, 1, 0, 3, 2]` / `selected_o3_default` / `14902`
- Selected mean / 95% LCB: `0.62361052` / `0.61764480`
- Diagnostic selected-target / selected-R148-foreign means: `-0.00115322` / `+0.02465309`
- Copies target R143 / foreign R148 mapping: `false` / `false`
- R148 hidden rows read: `0`
- Holdout executed: `false`

## Successive Halving

- Round `1`: `48` to `12`, leader `m5-6-0-3-2-1__selected_o3_default__s14901`, LCB `0.60464619`.
- Round `2`: `12` to `3`, leader `m5-6-1-0-3-2__selected_o3_default__s14902`, LCB `0.61671755`.
- Round `3`: `3` to `1`, leader `m5-6-1-0-3-2__selected_o3_default__s14902`, LCB `0.61764480`.

The design excludes the target-specific R143 mapping and both foreign R148
mappings before enumerating candidates. Three public-calibration views create
a 12-mapping shortlist; two policies and two realization seeds create 48 new
compiled routes. Fixed public design seeds reduce them 48 to 12 to 3 to 1 by
fidelity LCB. Only after selection, 32 diagnostic executions compare the
winner with target-specific R143 and R148 foreign routes; these diagnostics do
not alter selection. No R148 hidden row is loaded.

This design does not establish a holdout repair, general route-generation
advantage, temporal or cross-machine transfer, real hardware, mitigation,
soundness, quantum advantage, BQP separation, a solved frontier, or new credit.
