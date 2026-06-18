# B1/B7 cone_01 Restricted Phase-Removal Gate

- Status: `cone01_phase_removal_restricted_negative_gate`
- Workload: `qasmbench_medium_exact/gcm_h6.qasm`
- Target cone: `cone_01`
- Candidate windows: 35
- Required exact windows for B7 one-sided target: 30
- Remove-only exact pass count: 0
- Fixed Z-phase exact pass count: 0
- Continuous RZ exact pass count: 0
- Best continuous-RZ residual: 0.36435162331705345
- Median continuous-RZ residual: 0.41976650460733583
- Best fixed-phase residual: 0.36435162331705345
- Restricted gate clears B7 target: False
- Validation errors: 0

## Interpretation

The simple route fails: deleting the only arbitrary RY in a cone_01 window,
or replacing it with a local Z phase inside the same two-CNOT envelope, does
not produce an exact same-envelope rewrite. This is a restricted numerical
gate, not a global lower bound. T-B1-004 now needs broader two-qubit
synthesis, a KAK/Clifford scaffold, or another certificate-bearing rewrite.

## Claim Boundary

- Rewrite claimed: False
- Resource saving claimed: False
- Semantic certificate claimed: False
- Obstruction theorem claimed: False

## Best Continuous-RZ Attempts

| line | qubit | partner | theta | residual | replacement angle |
|---:|---:|---:|---:|---:|---:|
| 29 | 13 | 14 | 0.36485735178627743 | 0.36435162331705345 | 0.0 |
| 87 | 1 | 14 | 0.36485735178627743 | 0.36435162331705345 | 0.0 |
| 187 | 2 | 14 | 0.36485735178627743 | 0.36435162331705345 | 0.0 |
| 245 | 13 | 14 | 0.36485735178627743 | 0.36435162331705345 | 0.0 |
| 280 | 10 | 14 | 0.36485735178627743 | 0.36435162331705345 | 0.0 |
| 338 | 2 | 14 | 0.36485735178627743 | 0.36435162331705345 | 0.0 |
| 359 | 16 | 14 | 0.36485735178627743 | 0.36435162331705345 | 0.0 |
| 417 | 10 | 14 | 0.36485735178627743 | 0.36435162331705345 | 0.0 |
| 1478 | 8 | 14 | 0.36485735178627743 | 0.36435162331705345 | 0.0 |
| 1536 | 12 | 14 | 0.36485735178627743 | 0.36435162331705345 | 0.0 |
| 94 | 13 | 14 | 0.42054081161117118 | 0.41976650460733583 | 0.0 |
| 252 | 2 | 14 | 0.42054081161117118 | 0.41976650460733583 | 0.0 |
