# B1/B7 Cone_01 Shared-Theta Replay Verifier Scaffold

Status: `cone01_shared_theta_replay_verifier_scaffold`

This artifact replay-checks the shared-theta object proposals against the source QASM and the parameter-transfer theta groups. It verifies coverage and line-level theta consistency. It does not verify an occurrence-removing semantic rewrite and does not count any B7 resource reduction.

## Summary

- Candidate windows: `35`
- Shared synthesis objects: `4`
- Replay-verified objects: `4`
- Replayed occurrences: `35`
- Coverage matches parameter-transfer groups: `True`
- Duplicate line count: `0`
- Missing QASM line count: `0`
- Line theta mismatch count: `0`
- Object group mismatch count: `0`
- Shared-theta replay gate passed: `True`
- Semantic rewrite verified: `False`
- Occurrence-ledger removed occurrences: `0`
- Cost model accepted: `False`
- Validation errors: `0`

## Object Replay Rows

| object | theta | covered lines | expected lines | replay verified | theta mismatches |
|---|---:|---:|---:|---|---:|
| `cone01_shared_theta_01` | `0.420540811611` | 16 | 16 | `True` | 0 |
| `cone01_shared_theta_02` | `0.364857351786` | 10 | 10 | `True` | 0 |
| `cone01_shared_theta_03` | `0.99803486463` | 6 | 6 | `True` | 0 |
| `cone01_shared_theta_04` | `2.813468447841` | 3 | 3 | `True` | 0 |

## Interpretation

The shared-theta proposals now have replayable line-level evidence. This is useful CM-03 scaffolding, but it is intentionally weaker than a semantic rewrite certificate. The next hard gates are physical layout/routing, factory-amortization evidence, shared-error budgeting, independent baseline pressure, and a refreshed B7 ledger.
