# B4/B8/B10 R184 Windowed Exact-Score Protocol

- Status: `preregistered_design_unopened`
- Protocol payload hash: `6282eebdfa41ff94dfbe4eed4b61fc2030f02bec5eea6bb360b9fa27c890a999`
- Design contract payload hash: `e0c226bf419da94dc9e5afa3a249eabd085505c6b5328b7a2b3af1a8f6a4d108`
- Scientific execution: unopened

## Heuristic Question

R183 removed 62.6724% of initialized limb writes yet reached only a 0.984288x paired median ratio. Can an exact score become materially faster by carrying only a four-limb exponent window, while falling back losslessly to BigUint whenever the exact span is wider?

## Frozen Three-Arm Pairing

The matrix contains `468` same-process BigUint/prefix/window triplets: each of `13` cells runs `36` triplets. All six arm orders appear `6` times per cell, so scheduler position is balanced before any timing is observed.

## Decision Boundary

The window must preserve every expected mapping, stay at four compact limbs or fewer, remain at 64 bytes or fewer, and avoid fallback on the frozen workload. A median window/prefix ratio at or below 0.90 supports a representation-level speed gain; a median window/BigUint ratio at or below 1.00 establishes competitiveness with the exact dynamic denominator.

## Claim Boundary

This is a preregistered classical compiler representation experiment. It is not an upstream Qiskit patch, a full-domain performance theorem, production remedy, hardware result, quantum advantage, BQP separation, solved B4/B8/B10 frontier, or new credit.
