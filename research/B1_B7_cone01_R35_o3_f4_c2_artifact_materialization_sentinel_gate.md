# B1/B7 Cone01 R35 O3-F4 C2 Artifact Materialization Sentinel Gate

- Target: `T-B1-004ek/T-B7-013t`
- Upstream target: `T-B1-004ej/T-B7-013s`
- Method: `b1_b7_cone01_r35_o3_f4_c2_artifact_materialization_sentinel_gate_v0`
- Status: `cone01_r35_o3_f4_c2_artifact_materialization_sentinel_rejected`
- Fixture hash: `df2c6cc13381c1762bd200a2f77ec0302c32bd6cbbc270b840c05c2778cf2c3a`
- Preflight hash: `ab1ec9d5377dd719ccdf31a3c83983167c354db771043ca2aa2aa84de2154122`

## Result

R35 passes 8/8 requirements by building a metadata-clean sentinel fixture and rejecting it because execution artifact files are not materialized.

## Rejection Surface

- Surface rows passed / failed: `8` / `0`
- Materialized rows passed / failed: `0` / `8`
- Missing materialized files: `32`
- Materialized hash mismatches: `0`
- C2 accepted: `False`

## Requirement Results

- `S1` PASS: R34 source verifier is validation-clean and still accepts no C2 row
- `S2` PASS: Sentinel fixture passes the metadata surface before materialization
- `S3` PASS: Materialization check rejects every row with missing execution files
- `S4` PASS: Fixture keeps valid hashes, recomputed bindings, and numeric strict replay errors
- `S5` PASS: R35 blocks metadata-only evidence even when R34 surface requirements pass
- `S6` PASS: Fixture and preflight are hash-bound
- `S7` PASS: R35 preserves zero-credit B1/B7 boundaries
- `S8` PASS: R35 remains scoped to C2 materialization and claims no C3-C7 progress

## Claim Boundary

- Supported: R35 proves that metadata-clean C2 rows are still rejected unless the replay stdout, source circuit, candidate circuit, and witness files are materialized and hash-matched.
- Not supported: R35 does not accept a C2 submission, does not close O3, and does not permit reroute, B7 credit, STV credit, or resource-saving claims.
- Next gate: Submit materialized C2 execution files whose sha256 hashes match the declared row artifacts, then rerun the materialization verifier.

- validation_error_count: `0`
