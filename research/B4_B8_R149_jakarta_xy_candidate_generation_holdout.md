# B4/B8 R149 Jakarta Dense-XY Candidate-Generation Holdout

- Preregistered verdict: ACCEPT
- Groups / trial rows: `12` / `96`
- Three-arm executions / shots: `296` / `606208`
- Portfolio repaired-automatic mean / bootstrap lower: `+0.00360133` / `+0.00142312`
- Portfolio repaired-target mean / bootstrap lower: `-0.00391072` / `-0.00542965`
- Groups above -0.02 versus target: `12 / 12`
- Severe rows below -0.05 versus target: `0`
- Minimum target-snapshot mean: `-0.00636744`
- Replacement repaired-target / repaired-R148 means: `-0.00565709` / `+0.02424579`
- Replacement minimum / severe rows: `-0.01900856` / `0`
- Semantic passes: `24 / 24`
- Conditions passed / failed: `10` / `0`
- New credit delta: `0`

## Target Snapshot Evidence

- `FakeJakartaV2`: repaired-target `-0.00197268`, repaired-auto `+0.00787351` over `32` rows.
- `FakeLagosV2`: repaired-target `-0.00636744`, repaired-auto `-0.00017209` over `32` rows.
- `FakeOslo`: repaired-target `-0.00339202`, repaired-auto `+0.00310258` over `32` rows.

## Jakarta Dense-XY Replacement

- `FakeJakartaV2::dense_validation_xy_network_n6`: repaired-target mean `-0.00565709`, minimum `-0.01900856`, severe rows `0`.

## Acceptance Conditions

- A1 PASS: protocol, selector, route identities, and source bindings remain exact; value True, threshold True.
- A2 PASS: groups, rows, executions, and replacement-only diagnostic arm; value [12, 96, 296, 8], threshold [12, 96, 296, 8].
- A3 PASS: all repaired and target routes retain semantic fidelity; value [24, 0.9999999999999973], threshold [24, 0.9999999999].
- A4 PASS: portfolio repaired versus automatic noninferiority; value [0.003601332369730727, 0.0014231207208738118], threshold [-0.005, -0.01].
- A5 PASS: portfolio repaired versus target-specific noninferiority; value [-0.00391071609690194, -0.0054296525369598335], threshold [-0.005, -0.01].
- A6 PASS: groups above negative 0.02 versus target; value 12, threshold 12.
- A7 PASS: severe row regressions below negative 0.05; value 0, threshold 0.
- A8 PASS: each-target and Jakarta dense-XY replacement guards; value [-0.006367441656638435, -0.005657094116238631, 0.0242457889817988, 0], threshold [-0.01, -0.02, 0.01, 0].
- A9 PASS: commitment, hidden rows, reveal, and transcript; value True, threshold True.
- A10 PASS: forbidden claims and credit remain false; value 0, threshold 0.

## Claim Boundary

Supported only if accepted: one preregistered finite six-qubit synthetic
generated-route portfolio verdict. Not supported: general route-generation
advantage, temporal same-device transfer, cross-machine transfer, provider
access, real hardware, mitigation, soundness, quantum advantage, BQP
separation, solved B4/B8/B10, or new credit.
