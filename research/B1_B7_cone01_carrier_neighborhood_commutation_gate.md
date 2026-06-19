# B1/B7 Cone_01 Carrier Neighborhood Commutation Gate

Status: `cone01_carrier_neighborhood_commutation_negative_gate`

This artifact consumes T-B1-004x and checks whether same-target carrier inventory matches are local enough to motivate an absorption certificate.

## Summary

- Pattern groups / covered occurrences: `3` / `11`
- Same-target inventory-match patterns: `2` / `3`
- Radius 4 / 8 / 16 candidate patterns: `0` / `1` / `1`
- Blocker-free radius-16 candidate patterns: `1`
- Patterns without radius-16 candidate: `flat_pattern_02, flat_pattern_03`
- Accepted occurrence/proxy-T reduction: `0` / `0`
- Validation errors: `0`

## Rows

| Pattern | Occurrences | Same-target matches | Nearest distance | Radius 16 | Blocker-free radius 16 | Accepted reduction |
|---|---:|---:|---:|---|---|---:|
| flat_pattern_01 | 8 | 32 | 8 | True | True | 0 |
| flat_pattern_02 | 2 | 0 | None | False | False | 0 |
| flat_pattern_03 | 1 | 2 | 99 | False | False | 0 |

## Claim Boundary

- Nearby same-target inventory matches are search hints only.
- The gate does not prove adjacency, commutation, or semantic replay.
- Only `flat_pattern_01` has a radius-16 same-target neighborhood candidate.
- No neighborhood absorption certificate or B7 ledger improvement is claimed.
