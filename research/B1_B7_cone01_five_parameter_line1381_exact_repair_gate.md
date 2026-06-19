# B1/B7 Cone_01 Five-Parameter Line-1381 Exact Repair Gate

Status: `cone01_five_parameter_line1381_exact_packet_repair_not_ledger_accepted`

This artifact consumes T-B1-004ak and searches exactly five freed local-U3 parameters for the one remaining unresolved reduced-CNOT packet, line 1381, stopping at the first exact repair.

## Summary

- Target candidate line: `1381`
- Total five-parameter combinations: `8568`
- Candidates searched until first exact: `5795`
- Five-parameter exact packets: `1`
- Total exact packets after this gate: `3` / `3`
- Remaining unresolved packets: `0`
- Best 4-param residual: `2.997767950994e-02`
- Best 5-param residual: `6.513934436931e-13`
- Five-parameter exact repair off-grid parameters: `5`
- Partial CNOT reduction if accepted: `9`
- Accepted occurrence/proxy-T reduction: `0` / `0`
- Validation errors: `0`

## Packet Row

| Candidate line | Replacement CX | 4-param residual | First exact 5-param residual | Exact 5-param pass | Exact indices | Accepted rewrite |
|---:|---:|---:|---:|---|---|---|
| 1381 | 2 | 2.997768e-02 | 6.513934e-13 | True | [3, 4, 9, 16, 17] | False |

## Claim Boundary

Line 1381 now has a bounded packet-level exact repair after freeing five local-U3 parameters. Together with the earlier line-1378 and line-268 repairs, the reduced-CNOT packet set is 3/3 repaired at packet level. This still is not a symbolic exact decomposition, not a full-circuit replay certificate, and not a B7 occurrence/proxy-T saving because the local-U3 resource burden is not accepted.

## Next Required Gate

The next route must convert the three packet repairs into symbolic full-circuit replay certificates, price or eliminate the off-grid local-U3 parameters, and propagate only accepted occurrence removals into the B7 ledger.
