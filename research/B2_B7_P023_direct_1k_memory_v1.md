# B2/B7/#023 Direct 1,000-Round Logical-Memory Packet v1

Last updated: 2026-11-20

Status: **direct_1000_round_staging_gate_passed_p023_scalable_b2_b7_credit_closed**

## Can direct observation replace the seven-round projection?

Yes, at the 1,000-round staging horizon only. This packet executes `6` frozen Stim/PyMatching configurations across X/Z memory and distances 3/5/7, with 3,838 shots per row. It records `23,028` shots, `23,028,000` shot-rounds, and `1,596,608,000` physical-qubit-rounds.

At the 1% total logical-failure target, `1` distance(s) pass both X and Z by directly observed Wilson upper bounds: `[7]`. At the stricter 0.1% target, `0` distance(s) pass both bases.

## Direct results

| basis | d | rounds | shots | failures | logical pL | Wilson 95% upper | decode μs/shot | trace hash |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| x | 3 | 1000 | 3838 | 769 | 0.200365 | 0.213325 | 20.061 | `698de91b222c8ffb…` |
| x | 5 | 1000 | 3838 | 128 | 0.0333507 | 0.0395141 | 100.533 | `3b86fe9e98e30524…` |
| x | 7 | 1000 | 3838 | 13 | 0.00338718 | 0.00578689 | 240.937 | `01640cc8e02cf00e…` |
| z | 3 | 1000 | 3838 | 736 | 0.191767 | 0.204528 | 18.443 | `449aae01e64f0d84…` |
| z | 5 | 1000 | 3838 | 97 | 0.0252736 | 0.030734 | 93.098 | `f74a9dd6c9ab7e9c…` |
| z | 7 | 1000 | 3838 | 14 | 0.00364773 | 0.0061139 | 255.437 | `fd6991327dbd70e7…` |

## Paired-basis gates

| d | target | X upper | Z upper | X pass | Z pass | paired direct pass |
|---:|---:|---:|---:|---|---|---|
| 3 | 0.01 | 0.213325 | 0.204528 | False | False | False |
| 3 | 0.001 | 0.213325 | 0.204528 | False | False | False |
| 5 | 0.01 | 0.0395141 | 0.030734 | False | False | False |
| 5 | 0.001 | 0.0395141 | 0.030734 | False | False | False |
| 7 | 0.01 | 0.00578689 | 0.0061139 | True | True | True |
| 7 | 0.001 | 0.00578689 | 0.0061139 | False | False | False |

## Source and replay binding

- Run ID: `9c66f24c0dd198d80624805c85f801ec670f0bb5205978ea6c54912fb237c047`
- Protocol SHA-256: `5656abc207e97cc8887414ac6465fb352f167b2e56a1e8a82f4f225c2547f2c8`
- Generator SHA-256: `6d4f49b83e40c0d5f186691081a4af4cc4d18559740dcccd93366cd1d11e6d73`
- Toolchain: Python 3.12.6; Stim 1.16.0; PyMatching 2.4.0; NumPy 2.4.6; Darwin arm64.
- Each row binds canonical circuit text, decomposed detector error model, all ordered bit-packed detector/observable/prediction chunks, and the per-shot failure vector.
- Raw detector traces are not published in this packet. The hashes support exact same-environment rerun comparison but are not a substitute for a public hardware trace dataset.

## What changed—and what did not

The previous seven-round ceiling is removed for the 1,000-round simulator staging gate. This is direct simulator observation, not a stationary projection. It does **not** activate scalable #023 memory: direct one-million-round X/Z evidence and declared drift/correlation stress remain absent. No same-condition candidate-code overhead win is tested, and the calibrated B7 dependency gate remains closed. Therefore B2 low-overhead credit remains false and B7 memory-derived resource credit remains exactly zero.

## Claim boundary

No new-code, threshold, scalable-memory, million-round, hardware, production-decoder, drift-robustness, B2 low-overhead improvement, B7 resource-credit, or quantum-advantage claim is made.

## Next falsifier

Run a source-bound million-round X/Z pilot only for the strongest 1,000-round distance, add declared drift/correlation stress, and keep B2/B7 credit closed until the same-condition candidate and calibrated-evidence gates pass.

Formal checks: `24/24`.
