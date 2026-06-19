# B1/B7 Cone_01 Sparse Local-U3 Repair Gate

Status: `cone01_sparse_local_u3_repair_partial_not_ledger_accepted`

This artifact consumes T-B1-004ah and tests whether direct pi/4 snapping can be repaired by freeing only one or two local-U3 parameters.

## Summary

- Packets checked: `3`
- Sparse repair candidates searched: `420`
- One-parameter exact repairs: `1`
- Two-or-fewer-parameter exact repairs: `1`
- Unresolved packets after sparse search: `2`
- Partial CNOT reduction if accepted: `3`
- Sparse exact repair off-grid parameters: `0`
- Sparse exact repair free-parameter decisions: `1`
- Unrepaired replacement off-grid parameters: `30`
- Accepted occurrence/proxy-T reduction: `0` / `0`
- Validation errors: `0`

## Packet Rows

| Candidate line | Replacement CX | Best 1-param residual | Best 2-param residual | Sparse exact pass | Min exact free params | Accepted rewrite |
|---:|---:|---:|---:|---|---:|---|
| 1378 | 1 | 9.049428e-13 | 9.048318e-13 | True | 1 | False |
| 1381 | 2 | 3.405698e-01 | 2.653547e-01 | False | None | False |
| 268 | 2 | 5.463155e-01 | 3.989908e-01 | False | None | False |

## Claim Boundary

Line 1378 has a bounded packet-level sparse repair after changing one snapped local-U3 grid choice, but the route is still incomplete: the other two packets remain unrepaired even with two free parameters, no symbolic exact decomposition is emitted, no full-circuit rewrite is replayed, and no B7 occurrence/proxy-T saving is accepted.

## Next Required Gate

The next route must either broaden the repair dimension/scaffold for the two unresolved packets, convert the line-1378 sparse repair into a symbolic replayable full-circuit certificate, or abandon this reduced-CNOT scaffold for a different occurrence-removing route.
