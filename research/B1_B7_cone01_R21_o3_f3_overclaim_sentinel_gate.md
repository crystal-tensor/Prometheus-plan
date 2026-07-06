# B1/B7 Cone01 R21 O3-F3 Overclaim Sentinel Gate

- Target: `T-B1-004dw/T-B7-013f`
- Upstream target: `T-B1-004dv/T-B7-013e`
- Method: `b1_b7_cone01_r21_o3_f3_overclaim_sentinel_gate_v0`
- Status: `cone01_r21_o3_f3_overclaim_sentinel_rejected`
- Candidate: `NL-C02`
- Family: `O3-F3`
- Sentinel hash: `6683b2869f18c0b4fd2b1aefaef3de77598345b827cc9aecd77e549b74d9ee3f`
- Overclaim fixture hash: `0bb930b6c825d3814ec987ccb69d1034e652fffb2f2b0790297d150800a45906`
- Preflight hash: `666a44a18dcab905e259b5697a6dea261499880e79495d6cf0f552f12e2d5745`

## Result

The R21 overclaim sentinel gate passes 9/9 requirements. It emits a field-complete but invalid O3-F3 fixture and confirms the preflight rejects it.

## Sentinel Fixture

- Fixture path: `results/B1_B7_cone01_o3_f3_symbolic_lu_submissions/B1-B7-cone01-O3-F3-symbolic-lu.overclaim-sentinel.json`
- All required fields present: `True`
- Fixture rejected: `True`
- Failed gates: `['A2', 'A4', 'A7', 'A8']`

## Why It Fails

- `A2` fails because no source-unitary preservation certificate is supplied.
- `A4` fails because the lattice relation is marked `numerical_only`.
- `A7` fails because no machine-check command or expected replay output is supplied.
- `A8` fails because the fixture directly overclaims `checked_negative_lemma_present`, `reroute_allowed`, and `o3_closed`.

## Preflight Result

- Passed gates: `['A1', 'A3', 'A5', 'A6']`
- Failed gates: `['A2', 'A4', 'A7', 'A8']`
- Missing required fields: `[]`
- Accepted: `False`

## Requirement Results

- `L1` PASS: R20 intake is validation-clean and ready
- `L2` PASS: Overclaim fixture carries all fourteen R19 required fields
- `L3` PASS: Overclaim fixture is bound to O3-F3 and the source registry
- `L4` PASS: Semantic overclaim is present in the fixture
- `L5` PASS: Preflight rejects the overclaim fixture on the expected semantic gates
- `L6` PASS: Rejection is semantic rather than missing-field only
- `L7` PASS: R21 does not silently close O3, accept O3-F3, or allow reroute
- `L8` PASS: R21 preserves zero B7/resource credit claims
- `L9` PASS: Sentinel packet is internally hash-bound

## Claim Boundary

- Supported: R21 emits a field-complete but invalid O3-F3 overclaim fixture and proves the preflight rejects it.
- Not supported: R21 does not submit or accept a valid O3-F3 artifact, does not close O3, and does not permit R5 reroute. No R1 solution, occurrence removal, proxy-T reduction, B7 credit, resource saving, or impossibility theorem is supported.
- Next gate: Either harden the preflight further, or replace the red-team fixture with a real O3-F3 symbolic artifact that passes all gates.

This sentinel gate does not claim resource saving, occurrence removal, proxy-T reduction, B7 ledger improvement, FT resource credit, a checked impossibility theorem, an R5 reroute, or a solved B1/B7 problem.

## Validation

- validation_error_count: `0`
