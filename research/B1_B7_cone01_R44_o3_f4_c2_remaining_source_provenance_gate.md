# B1/B7 Cone01 R44 O3-F4 C2 Remaining Source-Provenance Gate

- Target: `T-B1-004et/T-B7-014c`
- Upstream target: `T-B1-004es/T-B7-014b`
- Method: `b1_b7_cone01_r44_o3_f4_c2_remaining_source_provenance_gate_v0`
- Status: `cone01_r44_o3_f4_c2_remaining_source_provenance_bound_rejected`
- Fixture hash: `23009a587461b2eb2ecae0e22e178aaa2935505efdc1010d6d76a2018a2bb98e`
- Evaluation hash: `5bca1cbfcfe354876962402673c4c8eb125fd4de472a7cedd71dfa9a09c386f9`

## Result

R44 passes 8/8 requirements by binding source provenance for the 7 rows that lacked it while keeping C2 rejected.

## Rejection Surface

- Newly bound rows: `7`
- Source-provenance rows passed: `8`
- Witness-schema rows passed: `1`
- Witness-preflight rows passed: `1`
- Unitary-distance rows passed: `8`
- Source-backed rows passed: `0`
- Source-backed flag failures: `8`
- C2 accepted: `False`

## Requirement Results

- `S1` PASS: R43 all-row unitary-distance smoke gate is validation-clean
- `S2` PASS: R44 binds source provenance for all 8 rows
- `S3` PASS: R44 preserves the current witness-schema and preflight blockers
- `S4` PASS: All materialized and unitary-distance files remain hash-valid
- `S5` PASS: R44 does not claim source-backed replay or same-unitary acceptance
- `S6` PASS: R44 keeps C2/O3/reroute/B7 zero-credit boundaries
- `S7` PASS: R44 claims no C3-C7 or ledger progress
- `S8` PASS: R44 output is hash-bound

## Claim Boundary

- Supported: R44 adds hash-bound source dataset, source trace, and replay-environment files for the 7 rows that lacked provenance after R43.
- Not supported: R44 does not provide witness schemas or executable preflights for those 7 rows, does not mark any row source-backed, does not accept C2, does not close O3, and does not permit reroute, B7 credit, STV credit, or resource-saving claims.
- Next gate: Add witness schemas and executable preflights for O3-F4-C02 through O3-F4-C08, then rerun the source-backed discriminator before C3-C7.

- validation_error_count: `0`
