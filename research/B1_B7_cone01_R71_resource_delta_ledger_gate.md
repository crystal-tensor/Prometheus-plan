# B1/B7 Cone01 R71 Resource Delta Ledger Boundary

- Method: `b1_b7_cone01_r71_resource_delta_ledger_gate_v0`
- Status: `cone01_r71_structural_cnot_gain_resource_regression_boundary`
- Upstream: `T-B1-004ft/T-B7-015c`

## Result

- Requirements: `8/8`
- Structural CNOT delta: `6`
- Logical T-count delta (source minus candidate): `-590`
- Logical T-depth delta (source minus candidate): `-54`
- Operation-count delta (source minus candidate): `-240`
- Source/candidate logical T ledger: `6245 -> 6835`
- Source/candidate logical T depth: `964 -> 1018`
- Accepted occurrence removal / proxy-T reduction: `0` / `0`
- B7 credit: `0`

## Interpretation

The R70 candidate is semantically replayable and removes six structural CNOTs, but it adds arbitrary and exact non-Clifford rotation work. Under the pinned FT proxy ledger, the candidate moves from 6245 to 6835 logical T units and from 964 to 1018 logical T-depth units. This is a negative resource boundary, not a solution claim.

## Next Gate

A future accepted route must preserve semantic replay while reducing the full-circuit FT ledger, or must provide a stronger exact absorption/decomposition certificate that removes the added rotation burden. CNOT-only improvement is insufficient for R67/B7 promotion.

## Claim Boundary

- R71 does not accept an exit route, occurrence removal, proxy-T reduction, reroute, O3 closure, or B7 credit.
- The FT synthesis ledger is a transparent proxy, not a physical layout or calibrated hardware result.
