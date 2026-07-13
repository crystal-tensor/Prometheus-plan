# B4/B8 R147 Target-Descriptor Adaptation Holdout

- Preregistered verdict: REJECT
- Adaptation groups / trial rows: `12` / `96`
- Three-arm executions / shots: `288` / `589824`
- Portfolio adapted-automatic mean / bootstrap lower: `-0.00133967` / `-0.00375896`
- Portfolio adapted-target mean / bootstrap lower: `-0.00945567` / `-0.01233164`
- Groups above -0.02 versus target: `9 / 12`
- Severe rows below -0.05 versus target: `2`
- Minimum target-snapshot mean versus target: `-0.01482360`
- Lagos dense-XY mean / severe rows: `-0.01496745` / `0`
- Semantic passes: `24 / 24`
- Conditions passed / failed: `6` / `4`
- New credit delta: `0`

## Target Snapshot Evidence

- `FakeJakartaV2`: adapted-target `-0.01074622`, adapted-auto `-0.00143075` over `32` rows.
- `FakeLagosV2`: adapted-target `-0.01482360`, adapted-auto `-0.00742697` over `32` rows.
- `FakeOslo`: adapted-target `-0.00279720`, adapted-auto `+0.00483870` over `32` rows.

## Acceptance Conditions

- A1 PASS: protocol, selector, route identities, and source bindings remain exact; value True, threshold True.
- A2 PASS: adaptation groups, rows, and executions; value [12, 96, 288], threshold [12, 96, 288].
- A3 PASS: all adapted and target routes retain semantic fidelity; value [24, 0.9999999999999973], threshold [24, 0.9999999999].
- A4 PASS: portfolio adapted versus automatic noninferiority; value [-0.0013396737855319804, -0.0037589604826970776], threshold [-0.005, -0.01].
- A5 FAIL: portfolio adapted versus target-specific noninferiority; value [-0.009455671490667228, -0.012331639895526514], threshold [-0.005, -0.01].
- A6 FAIL: groups above negative 0.02 versus target; value 9, threshold 11.
- A7 FAIL: severe row regressions below negative 0.05; value 2, threshold 0.
- A8 FAIL: each-target and Lagos dense-XY guards; value [-0.014823600146504386, -0.014967446962026586, 0], threshold [-0.01, -0.02, 0].
- A9 PASS: commitment, hidden rows, reveal, and transcript; value True, threshold True.
- A10 PASS: forbidden claims and credit remain false; value 0, threshold 0.

## Claim Boundary

Supported only if accepted: one preregistered synthetic target-descriptor
adaptation verdict across three fake-backend snapshots. Not supported:
temporal same-device transfer, cross-machine transfer, provider access, real
hardware, mitigation, soundness, quantum advantage, BQP separation, solved
B4/B8/B10, or new credit.
