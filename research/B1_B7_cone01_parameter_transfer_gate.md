# B1/B7 Cone_01 Parameter-Transfer Obligation Gate

Status: `cone01_parameter_transfer_obligation_gate`

This artifact checks a prerequisite for any broader cone_01 rewrite. The previous gates showed that direct deletion, phase replacement, and same-envelope Euler reabsorption do not produce exact windows. This gate asks whether the original `RY(theta)` occurrences carry nonzero continuous unitary sensitivity and whether enough angles are already exact-grid angles.

It is a guardrail only. It is not a rewrite certificate, not a KAK lower bound, not a B7 resource saving, and not a physical-layout claim.

## Summary

- Candidate windows: `35`
- Required exact windows for the B7 target: `30`
- Nonzero parameter-sensitivity windows: `35`
- Near pi/4-grid windows: `0`
- Distinct canonical theta values: `4`
- Largest repeated theta group: `16`
- Repeated theta occurrences: `35`
- Deletion without a parameter carrier clears B7 target: `False`
- Validation errors: `0`

## Top Theta Groups

| canonical theta | occurrences | nearest pi/4 grid | min distance |
|---:|---:|---|---:|
| 0.420540811611 | 16 | -7*pi/4 | 0.364857 |
| 0.364857351786 | 10 | -8*pi/4 | 0.364857 |
| 0.99803486463 | 6 | -7*pi/4 | 0.212637 |
| 2.813468447841 | 3 | -4*pi/4 | 0.328124 |

## Interpretation

Every checked cone_01 candidate window has nonzero projective sensitivity to its `RY(theta)` parameter. Therefore a future occurrence-removing rewrite cannot simply delete theta from the local model. It must either move theta into another counted parameter, prove enough exact special-angle identities, or provide certified parameter sharing that actually reduces the arbitrary-rotation ledger.

The current evidence does not support any B7 ledger change.
