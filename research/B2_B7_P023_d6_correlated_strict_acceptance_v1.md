# B2/B7/#023 Distance-6 Correlated-Decoder Strict Acceptance v1

As of 2026-11-20. Scope is exactly #021/B7, #022/B2, and #023.

## Heuristic question

Can two-pass correlation-aware matching make the unchanged 71-active-qubit candidate keep both X and Z below the strict 1% logical-failure ceiling for 1,000 rounds?

## Verdict: PHYSICAL-MEMORY GATE PASSED

| basis | seed | failures/shots | observed pL | strict CP upper | target | strict pass | cost |
|---|---:|---:|---:|---:|---:|---|---:|
| X | 500821869213481396 | 539/102400 | 0.00526367 | 0.00879527 | 0.01 | True | 71,000 |
| Z | 7444983191663564330 | 443/102400 | 0.00432617 | 0.00758689 | 0.01 | True | 71,000 |

Both bases strict-pass: **True**. Conditional resource score: **1.366197183**. Accepted physical-memory score: **1.366197183**. Physical-memory gate passed: **True**.

## Freeze integrity

The candidate was publicly frozen at commit `45a5323a8727fe8e90aab8e5109600a69a9f2940` and Discussion #325 before the salt was revealed. Raw circuits, coordinate-canonical circuits, DEMs, 71-qubit cost, noise model, decoder, horizon, and thresholds all match the no-outcome packet.

## Claim boundary

This passes only the physical-memory candidate gate. Full B2 remains closed pending decoder-latency pricing, model-mismatch robustness, and implementation constraints; it also does not establish scalable #023 memory, a hardware result, or B7 credit.

Formal checks: **30/30**. Run ID: `b0e92bf5afec57fa1e189284d1194890a664bbb47bef8d9f20f3bf60342e1543`.

## Next gate

Price decoder latency, test model mismatch and correlated-noise stress, declare a decoder deadline, and obtain direct million-round X/Z evidence before full B2, #023, or B7 credit.
