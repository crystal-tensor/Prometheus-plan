# B1/B7 Cone01 R75 Exact One-CNOT Grid Enumeration Gate

- Method: `b1_b7_cone01_r75_exact_one_cnot_grid_enumeration_gate_v0`
- Status: `cone01_r75_line1378_exact_one_cnot_grid_candidate_boundary`
- Requirements: `8/8`
- Raw right-layer parameterizations per orientation: `262144`
- Unique right-layer global-phase classes: `43264`
- Exact matches by packet: `[384, 0, 0]`
- Source minus best exact rotation cost: `[2, None, None]`
- CNOT reduction by packet: `[3, 0, 0]`
- Accepted occurrence removal / proxy-T reduction: `0` / `0`
- B7 credit: `0`

## Interpretation

The complete one-CNOT pi/4-grid enumeration finds a local exact candidate for line 1378. Its best local grid cost is 3 against source cost 5, with a three-CNOT local reduction. Lines 1381 and 268 have no exact one-CNOT grid match in the same declared class. The line-1378 result is now a concrete candidate for source-aligned full-circuit replay, not yet an accepted B7 saving.

## Claim Boundary

- Complete only for the declared one-CNOT pi/4-grid pair-class scaffold.
- No full-circuit rewrite, semantic replay certificate, occurrence removal, proxy-T reduction, reroute, or B7 credit is accepted.

## Best Line-1378 Candidate

- CNOT sequence: `01`
- Left pair values: `[4, 0, 4, 2, 1, 5]`
- Right pair values: `[4, 0, 6, 2, 1, 6]`
- Residual norm: `9.048319093514786e-13`
- Grid rotation cost: `3`
