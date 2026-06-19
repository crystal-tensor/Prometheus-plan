# B1/B7 Cone_01 Four-Parameter Line-1381 Repair Pressure Gate

Status: `cone01_four_parameter_line1381_pressure_no_exact_repair`

This artifact consumes T-B1-004aj and exhaustively frees exactly four local-U3 parameters for the one remaining unresolved reduced-CNOT packet, line 1381.

## Summary

- Target candidate line: `1381`
- Four-parameter candidates searched: `3060`
- Four-parameter exact packets: `0`
- Total exact packets after this gate: `2` / `3`
- Remaining unresolved packets: `1`
- Best 3-param residual: `4.986517766677e-02`
- Best 4-param residual: `2.997767950994e-02`
- Residual improvement: `1.988749815683e-02`
- Partial CNOT reduction if accepted: `6`
- Accepted occurrence/proxy-T reduction: `0` / `0`
- Validation errors: `0`

## Packet Row

| Candidate line | Replacement CX | 3-param residual | Best 4-param residual | Exact 4-param pass | Best indices | Accepted rewrite |
|---:|---:|---:|---:|---|---|---|
| 1381 | 2 | 4.986518e-02 | 2.997768e-02 | False | [5, 9, 10, 15] | False |

## Claim Boundary

Line 1381 improves under exactly-four-parameter pressure but still does not pass the exact residual gate. The project remains at 2/3 bounded packet repairs, with no symbolic exact decomposition, no full-circuit replay certificate, and no B7 occurrence/proxy-T saving.

## Next Required Gate

The next route must either broaden beyond four freed local-U3 parameters, change the two-CNOT scaffold, prove a scoped obstruction for this scaffold family, or abandon this reduced-CNOT route for a ledger-reducing construction.
