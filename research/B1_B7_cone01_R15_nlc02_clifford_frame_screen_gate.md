# B1/B7 Cone01 R15 NL-C02 Clifford-Frame Affine Screen Gate

- Target: `T-B1-004dq/T-B7-012z`
- Method: `b1_b7_cone01_r15_nlc02_clifford_frame_screen_gate_v0`
- Status: `cone01_r15_nlc02_clifford_frame_screen_passed_o3_still_open`
- Candidate: `NL-C02`
- Screen hash: `88601f447749cf6b599520ee49403bba9fec173e97ecb3229a88deeca3fe3617`
- Probe-table hash: `9e90dc4037d158db0768c8c3e75757fb96ff7e34fe1e83072434d337f61d765e`

## Result

The R15 Clifford-frame affine screen passes 10/10 requirements. It finds no Clifford-frame pi/4-grid escape, but O3 remains open.

## Screen Scope

- Parameters: `[3, 4, 9, 16, 17]`
- Signs: `[-1, 1]`
- Clifford-frame shifts in pi/2 units: `[-4, -3, -2, -1, 0, 1, 2, 3, 4]`
- Period shifts: `[-2, -1, 0, 1, 2]`
- Probe count: `450`
- Accepted escape count: `0`
- Grid tolerance: `1e-08`
- Error range: `0.14252750651545298` to `0.36211079657423184`

## Decision

- Clifford-frame escape found: `False`
- O3 closed: `False`
- Remaining open obligations: `['O1', 'O3']`
- Checked negative lemma present: `False`
- Reroute allowed: `False`

## Requirement Results

- `F1` PASS: R14 source screen is validation-clean and still leaves O3 open
- `F2` PASS: Exact-decomposition source remains validation-clean with five off-grid parameters
- `F3` PASS: Screen covers the R14 canonical parameter domain
- `F4` PASS: Screen covers both signs, nine Clifford-frame shifts, and five period shifts
- `F5` PASS: All 450 Clifford-frame affine probes are present
- `F6` PASS: No Clifford-frame affine probe reaches the pi/4 grid tolerance
- `F7` PASS: Every parameter has a best-screen row recorded
- `F8` PASS: Screen is hash-bound to R14 and exact-decomposition sources
- `F9` PASS: Screen does not close O3 or upgrade NL-C02
- `F10` PASS: Screen preserves zero resource and B7 credit claims

## Claim Boundary

- Supported: R15 finds no pi/4-grid escape in the declared Clifford-frame affine screen over the R13-bound five-parameter domain.
- Not supported: R15 does not prove general parameterization invariance and does not close O3. NL-C02 is still not a checked negative lemma. No R5 reroute, R1 solution, occurrence removal, proxy-T reduction, B7 credit, resource saving, or impossibility theorem is supported.
- Next gate: Expand O3 to arbitrary local-unitary equivalence or close O1 optimizer completeness; or falsify R15 with a valid equivalent Clifford-frame escape that reaches the pi/4 grid.

This screen gate does not claim resource saving, occurrence removal, proxy-T reduction, B7 ledger improvement, FT resource credit, a checked impossibility theorem, an R5 reroute, or a solved B1/B7 problem.

## Validation

- validation_error_count: `0`
