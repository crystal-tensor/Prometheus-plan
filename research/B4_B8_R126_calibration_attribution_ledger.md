# B4/B8 R126 Calibration Attribution Ledger

## Summary

- Target: `T-B4-002aa/T-B8-003ae/T-B10-009s`
- Upstream target: `T-B4-002z/T-B8-003ad/T-B10-009r`
- Method: `b4_b8_r126_calibration_attribution_ledger_v0`
- Status: `historical_snapshot_failure_attribution_boundary`
- R125 source rows consumed: `480`
- Snapshot/task attribution rows: `6`
- Bundle strata: `60`
- Block strata: `30`
- Candidate budget: `8192` shots
- Lowest candidate task pass rate: `0.0000`
- Highest candidate task pass rate: `1.0000`
- Mitigation tested: `False`
- New credit delta: `0`

- `FakeOslo` / `private_bundle_ghz_n6`: candidate pass `69/80` (`0.8625`), mean/max bundle error `0.3477/0.8220`, CX count `11`, readout/cx/combined exposure `0.0782/0.0871/0.1585`.
- `FakeOslo` / `private_bundle_graph_n6`: candidate pass `80/80` (`1.0000`), mean/max bundle error `0.1438/0.2683`, CX count `8`, readout/cx/combined exposure `0.0782/0.0627/0.1360`.
- `FakeJakartaV2` / `private_bundle_ghz_n6`: candidate pass `64/80` (`0.8000`), mean/max bundle error `0.4333/1.2670`, CX count `11`, readout/cx/combined exposure `0.1553/0.0846/0.2267`.
- `FakeJakartaV2` / `private_bundle_graph_n6`: candidate pass `80/80` (`1.0000`), mean/max bundle error `0.2400/0.3573`, CX count `8`, readout/cx/combined exposure `0.1553/0.0711/0.2154`.
- `FakeLagosV2` / `private_bundle_ghz_n6`: candidate pass `1/80` (`0.0125`), mean/max bundle error `1.0127/1.7119`, CX count `11`, readout/cx/combined exposure `0.6702/0.1781/0.7290`.
- `FakeLagosV2` / `private_bundle_graph_n6`: candidate pass `0/80` (`0.0000`), mean/max bundle error `0.9154/1.0428`, CX count `8`, readout/cx/combined exposure `0.6702/0.1197/0.7097`.

R126 does not tune or rerun the failed holdout. It decomposes the already fixed
R125 rows by historical snapshot, task, hidden-bundle choice, seed block,
physical readout exposure, and routed CX exposure. Correlations use only six
snapshot/task rows and are descriptive diagnostics, not causal estimates.

## Mitigation Priority

1. Pre-register physical-qubit subset selection using snapshot properties only.
2. Separate routing-only and readout-only ablations on new disjoint seeds.
3. Fit readout mitigation on calibration rows disjoint from evaluation rows.
4. Preserve the hidden bundle and A1-A5 rules in the next holdout.
5. Keep current provider and hardware transcript evidence as separate gates.

## Requirements

- `P1` PASS: the complete R125 result is hash-bound and consumed
- `P2` PASS: all six snapshot/task combinations have attribution rows
- `P3` PASS: all representative QASM 3 circuits parse and preserve measurement order
- `P4` PASS: all historical snapshot hashes remain bound
- `P5` PASS: bundle-choice strata cover every source trial
- `P6` PASS: seed-block strata cover every source trial
- `P7` PASS: readout and CX exposure proxies are finite and bounded
- `P8` PASS: small-sample correlations are explicitly descriptive only
- `P9` PASS: mitigation packets are proposed without reusing holdout for acceptance
- `P10` PASS: no hardware, soundness, advantage, BQP, or new credit is claimed

## Claim Boundary

Supported: row-level attribution of the fixed R125 historical-snapshot failure.
Not supported: a mitigation win, causal noise decomposition, current calibration,
provider access, hardware execution, protocol soundness, quantum advantage, BQP
separation, or B10 credit.
