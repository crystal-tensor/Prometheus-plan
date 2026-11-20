# B2/B7/#023 Distance-6 Strict Acceptance v1

As of 2026-11-20. Scope is exactly #021/B7, #022/B2, and #023.

## Heuristic question

Can the publicly frozen 71-active-qubit candidate keep both X and Z below the strict 1% logical-failure ceiling for 1,000 rounds?

## Verdict: REJECTED

| basis | seed | failures/shots | observed pL | strict CP upper | target | strict pass | cost |
|---|---:|---:|---:|---:|---:|---|---:|
| X | 5755652369797857841 | 1354/102400 | 0.01322266 | 0.01844350 | 0.01 | False | 71,000 |
| Z | 5575061453250627055 | 1282/102400 | 0.01251953 | 0.01761768 | 0.01 | False | 71,000 |

Both bases strict-pass: **False**. Conditional resource score: **1.366197183**. Accepted score: **0.000000000**. Candidate accepted: **False**.

## Freeze integrity

The candidate was publicly frozen at commit `569d61572e3fd8e40fd6152dcdc032af7999845a` and Discussion #323 before the salt was revealed. Raw circuits, coordinate-canonical circuits, DEMs, 71-qubit cost, noise model, decoder, horizon, and thresholds all match the no-outcome packet.

## Claim boundary

The candidate fails the frozen acceptance contract and earns score zero. It does not establish B2 improvement, scalable #023 memory, a hardware result, or B7 resource credit.

Formal checks: **27/27**. Run ID: `0608457c4db51035111974eb371533e8c2d5f8216e92cf5e0651745b7465cd50`.

## Next gate

Reject distance 6 under the frozen contract; preserve the zero score and preregister a different <=77-active-qubit code, schedule, or decoder route before sampling.
