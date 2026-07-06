# B1/B7 Cone01 R16 NL-C02 Clifford-Frame Invariance Lemma Gate

- Target: `T-B1-004dr/T-B7-013a`
- Method: `b1_b7_cone01_r16_nlc02_clifford_frame_invariance_lemma_gate_v0`
- Status: `cone01_r16_nlc02_clifford_frame_invariance_sublemma_closed_o3_still_open`
- Candidate: `NL-C02`
- Lemma hash: `190b5f8547ccfff539c2c9dba7e7fd19ed8791729d06d0937146430cea8cf904`
- Proof-table hash: `e144ebe2e305f11b7ea5a65fd75e845ee3f4bdcdf978b5cec6b4952ee2faba12`

## Result

The R16 Clifford-frame invariance lemma gate passes 10/10 requirements. It closes the Clifford-frame affine sublemma used by R15, but O3 remains open.

## Invariance Statement

For G(x)=s*x+k*pi/2+2*pi*m with s in {-1,1}, k in Z, m in Z, distance from G(x) to the pi/4 lattice equals distance from x to the pi/4 lattice.

## Proof Sketch

- pi/2 is 2*(pi/4), so k*pi/2 shifts by an integer number of pi/4 lattice units.
- 2*pi is 8*(pi/4), so period shifts also preserve the pi/4 lattice.
- The sign flip maps the pi/4 lattice to itself and preserves absolute distance.
- Therefore the finite R15 Clifford-frame affine family cannot turn a non-grid parameter into a pi/4-grid parameter.

## Scope

- Parameters: `[3, 4, 9, 16, 17]`
- Signs: `[-1, 1]`
- Clifford-frame shifts in pi/2 units: `[-4, -3, -2, -1, 0, 1, 2, 3, 4]`
- Period shifts: `[-2, -1, 0, 1, 2]`
- Invariant probe count: `450`
- Proof rows: `5`
- Accepted escape count: `0`
- Grid tolerance: `1e-08`
- Error range: `0.14252750651545298` to `0.36211079657423184`
- Max invariance error delta: `2.6645352591003757e-15`

## Decision

- Clifford-frame invariance sublemma closed: `True`
- O3 closed: `False`
- Remaining open obligations: `['O1', 'O3']`
- Checked negative lemma present: `False`
- Reroute allowed: `False`

## Requirement Results

- `G1` PASS: R15 source screen is validation-clean and contains the expected 450 probes
- `G2` PASS: Exact-decomposition source remains validation-clean with five off-grid parameters
- `G3` PASS: Lemma covers the R15 canonical parameter domain
- `G4` PASS: Finite verification covers the same R15 Clifford-frame affine family
- `G5` PASS: Distance to the pi/4 lattice is invariant across the declared family
- `G6` PASS: No member of the closed Clifford-frame affine sublemma reaches the pi/4 grid
- `G7` PASS: R16 preserves the R15 error envelope
- `G8` PASS: Lemma is hash-bound to R15 and exact-decomposition sources
- `G9` PASS: Sublemma closure does not close full O3 or upgrade NL-C02
- `G10` PASS: Lemma preserves zero resource and B7 credit claims

## Claim Boundary

- Supported: R16 proves the declared Clifford-frame affine family preserves distance to the pi/4 lattice over the R13-bound five-parameter domain, so the R15 450-probe negative result is promoted to a closed sublemma.
- Not supported: R16 does not prove arbitrary local-unitary reparameterization invariance and does not close full O3. NL-C02 is still not a checked negative lemma. No R5 reroute, R1 solution, occurrence removal, proxy-T reduction, B7 credit, resource saving, or impossibility theorem is supported.
- Next gate: Expand O3 beyond Clifford-frame affine invariance to a general local-unitary equivalence argument, or close O1 optimizer completeness; alternatively falsify the sublemma by finding an in-family transform that changes pi/4 lattice distance.

This lemma gate does not claim resource saving, occurrence removal, proxy-T reduction, B7 ledger improvement, FT resource credit, a checked impossibility theorem, an R5 reroute, or a solved B1/B7 problem.

## Validation

- validation_error_count: `0`
