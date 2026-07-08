# B1/B7 Cone01 R40 O3-F4 C2 Single-Row Witness Scaffold Gate

- Target: `T-B1-004ep/T-B7-013y`
- Upstream target: `T-B1-004eo/T-B7-013x`
- Method: `b1_b7_cone01_r40_o3_f4_c2_single_row_witness_scaffold_gate_v0`
- Status: `cone01_r40_o3_f4_c2_single_row_witness_scaffold_partial_rejected`
- Fixture hash: `b9c02595fface2f8c1f51b4f627ad893bfb9c88a5fac92c9966e6f31ecb38fea`
- Evaluation hash: `1d6e5ce62e04b2c1bfd5532b5acff3684a075f3faec4303cee89be6a5a10518b`

## Result

R40 passes 8/8 requirements by adding one witness schema/verifier scaffold while keeping C2 rejected.

## Rejection Surface

- Materialized rows passed: `8`
- Source-provenance rows passed: `1`
- Witness-schema rows passed: `1`
- Witness-schema failures: `7`
- Source-backed rows passed: `0`
- Source-backed flag failures: `8`
- C2 accepted: `False`

## Requirement Results

- `S1` PASS: R39 source-provenance gate is validation-clean with one provenance row
- `S2` PASS: R40 emits witness schema and dry-run verifier files for one row
- `S3` PASS: The enriched row keeps source provenance intact
- `S4` PASS: All materialized C2 files remain hash-valid
- `S5` PASS: R40 does not claim source-backed replay or same-unitary acceptance
- `S6` PASS: R40 keeps C2/O3/reroute/B7 zero-credit boundaries
- `S7` PASS: R40 claims no C3-C7 or ledger progress
- `S8` PASS: R40 output is hash-bound

## Claim Boundary

- Supported: R40 adds a hash-verifiable witness schema and dry-run verifier scaffold for one C2 row, reducing witness-schema failures from 8 to 7 while preserving the R39 source-provenance packet.
- Not supported: R40 does not turn the dry-run verifier into a real same-unitary certificate, does not mark the row source-backed, does not accept C2, does not close O3, and does not permit reroute, B7 credit, STV credit, or resource-saving claims.
- Next gate: Turn the dry-run schema scaffold into a real same-unitary verifier for O3-F4-C01, then replace smoke flags with source-backed replay flags and repeat provenance/witness packets for the remaining rows.

- validation_error_count: `0`
