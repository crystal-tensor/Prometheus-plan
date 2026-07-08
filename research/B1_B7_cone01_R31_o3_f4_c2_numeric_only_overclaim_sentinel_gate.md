# B1/B7 Cone01 R31 O3-F4 C2 Numeric-Only Overclaim Sentinel

- Target: `T-B1-004eg/T-B7-013p`
- Upstream target: `T-B1-004ef/T-B7-013o`
- Method: `b1_b7_cone01_r31_o3_f4_c2_numeric_only_overclaim_sentinel_gate_v0`
- Status: `cone01_r31_o3_f4_c2_numeric_only_fixture_rejected`
- Fixture hash: `78a33f7e7bcbad0f3f5dce8d172d997eb7cde9a43a2b979abd9d852971544e07`
- Fixture row-table hash: `395f5ced2eef95baf0864ecbe15e2b592874c11dda0bb10af356fb3cd335b5b5`
- Preflight hash: `978f9ffe9d72a438c4701c659381eb4e818758448bb13f3b097e7d4b17625256`

## Result

R31 passes 8/8 requirements by rejecting a numeric-only C2 fixture that passes the tolerance surface but lacks valid witness and hash provenance.

## Sentinel Outcome

- Row count: `8`
- Numeric replay error count: `8`
- Tolerance pass count: `8`
- Max observed replay error: `8e-10`
- Invalid hash cell count: `32`
- Surface pass: `True`
- Evidence pass: `False`
- C2 accepted: `False`

## Requirement Results

- `S1` PASS: R30 source is validation-clean and template hash matches
- `S2` PASS: Numeric-only fixture covers all 8 C2 rows with required fields
- `S3` PASS: Numeric-only fixture passes the numeric tolerance surface
- `S4` PASS: Numeric tolerance alone is rejected without witness and hash provenance
- `S5` PASS: Fixture keeps C2, O3, reroute, and B7 credit unaccepted
- `S6` PASS: Fixture and preflight are hash-bound
- `S7` PASS: R31 does not claim C3-C7 progress
- `S8` PASS: Sentinel preserves the R30 challenge-row identity

## Claim Boundary

- Supported: R31 proves numeric replay errors under tolerance are not enough for C2 acceptance without valid same-unitary witness hashes, source/candidate circuit hashes, replay command provenance, and stdout hashes.
- Not supported: R31 does not accept C2, does not complete the certificate triad, does not close O3, and does not permit reroute, B7 credit, STV credit, or resource-saving claims.
- Next gate: Replace the numeric-only fixture placeholders with valid sha256 witness/circuit/stdout hashes and a real replay command while keeping all 8 numeric replay errors <= 1e-08.

- validation_error_count: `0`
