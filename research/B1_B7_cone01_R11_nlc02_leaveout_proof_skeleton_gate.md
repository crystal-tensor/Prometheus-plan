# B1/B7 Cone01 R11 NL-C02 Leave-Out Proof-Skeleton Gate

- Target: `T-B1-004dm/T-B7-012v`
- Method: `b1_b7_cone01_r11_nlc02_leaveout_proof_skeleton_gate_v0`
- Status: `cone01_r11_nlc02_leaveout_proof_skeleton_ready_unchecked`
- Candidate: `NL-C02`
- Skeleton hash: `4ec8ffb777d13acefabebfd213a61e0d7e7bc11d904ba227d8bbb6727fc833ab`
- Row-table hash: `0b7b5566197c780ca9e5e6c8d3ac86fe3a157e309c905a0499f23aadeb12b35c`
- R10 registry hash: `c58910245e32ab5738959a711de1e903951a59dc96cfe9ee390b5c514c7fbf54`

## Result

The R11 NL-C02 proof-skeleton gate passes 10/10 requirements. It machine-checks the finite leave-out coverage and creates a falsification harness, but it does not claim a checked negative lemma.

## Machine-Checked Facts

- all 31 nonempty subsets are present
- all 31 rows have exact_pass=false
- all five leave-out gates use the same exact_tolerance
- all five leave-out gates report validation_error_count=0
- the minimum residual norm remains above exact_tolerance

## Coverage

- Covered parameter count: `5`
- Expected / observed nonempty subsets: `31` / `31`
- Leave-out rows / exact passes / exact failures: `31` / `0` / `31`
- Exact tolerance: `1e-08`
- Residual norm range: `0.09892087709180968` to `0.8415210419190079`

## Open Proof Obligations

- `O1` Optimizer completeness boundary: Prove that each leave-out optimization search is complete for the declared parameterization, or explicitly downgrade the lemma to a search-domain lemma.
- `O2` Tolerance-to-exactness bridge: Justify that residual_norm > exact_tolerance excludes exact replay in the accepted arithmetic model.
- `O3` Parameterization invariance: Show that no equivalent reparameterization of the same local unitary falls outside the leave-out table while still clearing Route A.
- `O4` Source-domain binding: Bind the five-parameter domain to the R7/R8/R9 source hashes and rule out accidental drift in line1381 indexing.

## Falsification Harness

- `F1` Find an observed subset row with exact_pass=true. Current pass: `True`
- `F2` Find a missing nonempty subset of the five-parameter domain. Current pass: `True`
- `F3` Find any leave-out gate with validation_error_count > 0. Current pass: `True`
- `F4` Find inconsistent exact_tolerance values across leave-out gates. Current pass: `True`
- `F5` Find residual_norm <= exact_tolerance in any normalized row. Current pass: `True`

## Decision

- Checked negative lemma present: `False`
- Candidate proof skeleton ready: `True`
- Falsification harness ready: `True`
- Reroute allowed: `False`

## Requirement Results

- `S1` PASS: R10 registry contains NL-C02 and remains validation-clean
- `S2` PASS: All five leave-out source gates are validation-clean
- `S3` PASS: The five-parameter domain is stable across leave-out gates
- `S4` PASS: All 31 nonempty leave-out subsets are covered exactly once
- `S5` PASS: All leave-out exact passes remain zero
- `S6` PASS: Exact tolerance is consistent and every residual remains above tolerance
- `S7` PASS: Proof skeleton records all four open obligations
- `S8` PASS: Falsification harness records five executable checks
- `S9` PASS: All source files are hash-bound
- `S10` PASS: Skeleton is not upgraded into a checked lemma or reroute

## Claim Boundary

- Supported: R11 proves the finite leave-out row coverage and creates a falsification harness for NL-C02 under the current search-domain evidence.
- Not supported: R11 is not a checked negative lemma. Optimizer completeness, tolerance-to-exactness, parameterization invariance, and source-domain binding remain open proof obligations. No R5 reroute, R1 solution, occurrence removal, proxy-T reduction, B7 credit, resource saving, or impossibility theorem is supported.
- Next gate: Close O1-O4 or falsify NL-C02 with an exact leave-out pass, missing subset, validation error, tolerance inconsistency, or residual below tolerance.

This proof-skeleton gate does not claim resource saving, occurrence removal, proxy-T reduction, B7 ledger improvement, FT resource credit, a checked impossibility theorem, an R5 reroute, or a solved B1/B7 problem.

## Validation

- validation_error_count: `0`
