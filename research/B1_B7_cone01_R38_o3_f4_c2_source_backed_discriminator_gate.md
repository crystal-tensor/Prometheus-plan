# B1/B7 Cone01 R38 O3-F4 C2 Source-Backed Discriminator Gate

- Target: `T-B1-004en/T-B7-013w`
- Upstream target: `T-B1-004em/T-B7-013v`
- Method: `b1_b7_cone01_r38_o3_f4_c2_source_backed_discriminator_gate_v0`
- Status: `cone01_r38_o3_f4_c2_source_backed_discriminator_rejects_smoke`
- Replacement contract hash: `906da61aa3c205ebefe1caf001e3e2b86aeb74abcf89d1bbc6441f8c1137186f`
- Discriminator hash: `e23f694cdb37f985e30b15ead907bbf4772db2260398c773c7e5e3777d00c852`

## Result

R38 passes 8/8 requirements by proving that all 8 R37 materialized rows are still non-source-backed smoke rows.

## Rejection Surface

- Materialized rows passed: `8`
- Source-backed rows passed: `0`
- Smoke-only rows: `8`
- Source-backed flag failures: `8`
- Source provenance failures: `8`
- Witness schema failures: `8`
- Binding mismatch count: `0`
- C2 accepted: `False`

## Requirement Results

- `S1` PASS: R37 source gate is validation-clean and all rows are materialized
- `S2` PASS: R38 emits a source-backed replacement contract
- `S3` PASS: Current R37 fixture remains fully materialized under R38
- `S4` PASS: R38 rejects every current row as non-source-backed smoke
- `S5` PASS: Source-backed provenance and witness requirements are enforced
- `S6` PASS: Existing provenance binding still recomputes for smoke rows
- `S7` PASS: R38 preserves zero-credit B1/B7 boundaries
- `S8` PASS: R38 claims no C3-C7 or B7 ledger progress

## Claim Boundary

- Supported: R38 defines and runs the source-backed C2 discriminator. It proves the current all-row materialized R37 fixture is still rejected because every row is smoke-only and lacks source-backed provenance plus same-unitary witness schema/verifier evidence.
- Not supported: R38 does not accept C2, does not replace any smoke row with real source-backed replay, does not close O3, and does not permit reroute, B7 credit, STV credit, or resource-saving claims.
- Next gate: Submit at least one row that satisfies the source-backed replacement contract, then scale to all 8 rows before C3-C7.

- validation_error_count: `0`
