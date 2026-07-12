# B4/B8 R142 Seed-Robust LCB Mapping Holdout

## Verdict

- Preregistered verdict: ACCEPT
- Contract SHA-256: 60d62422c35b4f9b2f3339faefc7512c81c3f8049a1ce7291dacb2c6853ba4b6
- Lagos R142-auto mean / wins: +0.02063963 / 7 of 8
- Lagos R142-R140 mean: +0.01290316
- Portfolio R142-auto mean / bootstrap lower: +0.00908706 / +0.00669395
- Portfolio R142-R140 mean: +0.00260598
- Groups above -0.01 versus R140: 12 / 12
- Three-arm rows / executions / shots: 96 / 288 / 1179648
- Conditions passed / failed: 10 / 0
- Phase replay: 4 / 4
- New credit delta: 0

R142 and R140 circuits are frozen before the hidden seed. Each row creates a
fresh automatic compilation and uses one shared simulator seed across all
three arms. The result therefore tests whether lower-confidence-bound design
selection transfers to a disjoint challenge block.

## Acceptance Conditions

- A1 PASS: design and selected-QASM bindings remain exact; value True, threshold True.
- A2 PASS: all groups contain eight complete three-arm rows; value [96, 12], threshold [96, 12].
- A3 PASS: Lagos R142-auto mean is nonnegative; value 0.020639625973707568, threshold >= 0.
- A4 PASS: Lagos R142 wins at least half against automatic; value 7, threshold >= 4.
- A5 PASS: Lagos R142 materially improves over R140; value 0.012903163880568516, threshold >= 0.005.
- A6 PASS: portfolio R142-auto bootstrap lower bound; value 0.006693946708449767, threshold >= -0.005.
- A7 PASS: portfolio R142-R140 mean noninferiority; value 0.002605983648935379, threshold >= -0.002.
- A8 PASS: cross-group improvement avoids broad regressions; value 12, threshold >= 11.
- A9 PASS: disclosed execution and shot budget matches contract; value [288, 1179648], threshold [288, 1179648].
- A10 PASS: production, hardware, soundness, advantage, BQP, and credit claims remain false; value 0, threshold 0.

## Group Evidence

- FakeJakartaV2::dense_validation_complete_ising_n6: R142-auto +0.01383112, R142-R140 +0.00258226, wins vs auto 6/8.
- FakeJakartaV2::dense_validation_inverse_qft_n6: R142-auto +0.00004109, R142-R140 +0.00009539, wins vs auto 3/8.
- FakeJakartaV2::dense_validation_scrambled_qft_n6: R142-auto +0.00024582, R142-R140 -0.00005463, wins vs auto 6/8.
- FakeJakartaV2::dense_validation_xy_network_n6: R142-auto +0.02784007, R142-R140 +0.00000000, wins vs auto 8/8.
- FakeLagosV2::dense_validation_complete_ising_n6: R142-auto +0.02063963, R142-R140 +0.01290316, wins vs auto 7/8.
- FakeLagosV2::dense_validation_inverse_qft_n6: R142-auto +0.00019567, R142-R140 +0.00003044, wins vs auto 6/8.
- FakeLagosV2::dense_validation_scrambled_qft_n6: R142-auto +0.00040591, R142-R140 -0.00053457, wins vs auto 6/8.
- FakeLagosV2::dense_validation_xy_network_n6: R142-auto +0.01019242, R142-R140 +0.00000000, wins vs auto 7/8.
- FakeOslo::dense_validation_complete_ising_n6: R142-auto +0.00873580, R142-R140 +0.00266623, wins vs auto 8/8.
- FakeOslo::dense_validation_inverse_qft_n6: R142-auto -0.00021378, R142-R140 -0.00050434, wins vs auto 3/8.
- FakeOslo::dense_validation_scrambled_qft_n6: R142-auto +0.00005070, R142-R140 +0.00011769, wins vs auto 4/8.
- FakeOslo::dense_validation_xy_network_n6: R142-auto +0.02708027, R142-R140 +0.01397017, wins vs auto 8/8.

## Requirements

- P1 PASS: public contract and discussion precede challenge generation
- P2 PASS: all twelve R142 artifact bindings remain exact
- P3 PASS: secret commitment precedes rows and reveal follows complete rows
- P4 PASS: all twelve groups contain eight complete three-arm rows
- P5 PASS: 288 executions and 1,179,648 shots match the contract
- P6 PASS: each three-arm row shares one simulator seed
- P7 PASS: both portfolio bootstraps use 10,000 resamples
- P8 PASS: the verdict follows unchanged A1-A10 gates
- P9 PASS: all four phase artifacts replay in a fresh process
- P10 PASS: production, hardware, soundness, advantage, BQP, and credit remain excluded

## Claim Boundary

Supported: one preregistered synthetic hidden-seed verdict for the R142 LCB
mapping portfolio. Not supported: efficient production selection, current
calibration, real hardware, mitigation, independent custody, protocol
soundness, quantum advantage, BQP separation, solved B4/B8/B10, or new credit.
