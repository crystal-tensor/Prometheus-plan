# B1/B7 Cone_01 Carrier Blocker CNOT Parity Gate

Status: `cone01_carrier_blocker_parity_negative_gate`

This artifact consumes T-B1-004aa/T-B1-004ab and checks whether the blocked source-aligned carrier stacks can be cleared by cheap CNOT parity or adjacent duplicate-CNOT cancellation.

## Summary

- Parity candidates: `3`
- CNOT-only parity identity candidates: `1`
- Odd CNOT parity candidates: `2`
- Repeated same-edge blocker pairs: `11`
- Clean adjacent CNOT cancel pairs: `0`
- Target single-qubit ops between repeated pairs: `18`
- CNOT-only parity identity but interleaved candidates: `1`
- Parity clearance gate passed: `False`
- Accepted occurrence/proxy-T reduction: `0` / `0`
- Validation errors: `0`

## Candidate Rows

| Pattern | Candidate line | Edge counts | CNOT-only parity identity | Clean cancel pairs | Rejection |
|---|---:|---|---:|---:|---|
| flat_pattern_01 | 1378 | `{'4-8': 4}` | True | 0 | cnot-only parity is even but repeated blockers are separated by target-qubit operations |
| flat_pattern_01 | 1381 | `{'4-8': 5}` | False | 0 | blocker CNOT parity has odd edge counts |
| flat_pattern_01 | 268 | `{'10-14': 1, '2-14': 5}` | False | 0 | blocker CNOT parity has odd edge counts |

## Claim Boundary

This is a negative cheap-clearance gate. It does not prove that no semantic CNOT-stack rewrite exists. It only rejects the cheap route where repeated blocker CNOTs can be removed by parity or adjacent duplicate cancellation without handling the intervening target-qubit operations.
