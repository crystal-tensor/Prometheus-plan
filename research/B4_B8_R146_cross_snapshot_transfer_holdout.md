# B4/B8 R146 Cross-Backend Snapshot Transfer Holdout

- Preregistered verdict: REJECT
- Transfer groups / trial rows: `24` / `192`
- Three-arm executions / shots: `576` / `1179648`
- Portfolio transfer-automatic mean / bootstrap lower: `-0.00293528` / `-0.00539244`
- Portfolio transfer-target mean / bootstrap lower: `-0.01145921` / `-0.01410930`
- Groups above -0.02 versus target: `19 / 24`
- Severe rows below -0.05 versus target: `9`
- Minimum target-snapshot mean versus target: `-0.01799629`
- Semantic passes: `48 / 48`
- Conditions passed / failed: `6 / 4`
- New credit delta: `0`

## Target Snapshot Evidence

- `FakeJakartaV2`: transfer-target `-0.00885060`, transfer-auto `+0.00094685` over `64` rows.
- `FakeLagosV2`: transfer-target `-0.01799629`, transfer-auto `-0.01156231` over `64` rows.
- `FakeOslo`: transfer-target `-0.00753074`, transfer-auto `+0.00180963` over `64` rows.

## Acceptance Conditions

- A1 PASS: protocol and source bindings remain exact; value True, threshold True.
- A2 PASS: transfer groups, rows, and executions; value [24, 192, 576], threshold [24, 192, 576].
- A3 PASS: all transferred and target routes retain semantic fidelity; value [48, 0.9999999999999971], threshold [48, 0.9999999999].
- A4 PASS: portfolio transfer versus automatic noninferiority; value [-0.0029352762347639345, -0.005392437521615902], threshold [-0.005, -0.01].
- A5 FAIL: portfolio transfer versus target-specific noninferiority; value [-0.011459211718280767, -0.014109302241723028], threshold [-0.005, -0.01].
- A6 FAIL: groups above negative 0.02 versus target; value 19, threshold 20.
- A7 FAIL: severe row regressions below negative 0.05; value 9, threshold 0.
- A8 FAIL: each target snapshot mean transfer-target; value -0.01799629482163365, threshold -0.01.
- A9 PASS: commitment, hidden rows, reveal, and transcript replay; value True, threshold True.
- A10 PASS: forbidden claims and credit remain false; value 0, threshold 0.

## Claim Boundary

Supported only if accepted: one preregistered synthetic all-direction transfer
verdict across three fake-backend snapshots. Not supported: temporal same-device
calibration drift, cross-machine transfer, provider access, real hardware,
mitigation, soundness, quantum advantage, BQP separation, solved B4/B8/B10, or
new credit.
