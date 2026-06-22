# B1/B7 cone_01 Bounded Replacement Patch Gate

## Summary

- Method: `b1_b7_cone01_bounded_replacement_patch_gate_v0`
- Status: `cone01_bounded_replacement_patches_not_composable_full_circuit`
- Bounded OpenQASM 3 patch snippets: `3` / `3`
- Bounded exact-pass snippets: `3`
- Max bounded residual / entry error: `9.049428e-13` / `6.398912e-13`
- Candidate CNOT reduction if accepted: `9`
- Remaining replacement off-grid parameters: `5`
- Overlapping source-window pairs: `1`
- Composable full-circuit patch set available: `False`
- Accepted full-circuit patch / replay / occurrence / proxy-T reduction: `0` / `0` / `0` / `0`
- Validation errors: `0`

## Patch Rows

| Line | Window | Support | CNOT delta | QASM3 lines | Off-grid params | Accepted full-circuit patch |
|---:|---|---|---:|---:|---:|---:|
| 1378 | 1369-1377 | [4, 8] | 3 | 6 | 0 | False |
| 1381 | 1369-1379 | [4, 8] | 3 | 9 | 5 | False |
| 268 | 256-267 | [2, 14] | 3 | 9 | 0 | False |

## Claim Boundary

OpenQASM 3 bounded replacement snippets now exist for all three exact repaired reduced-CNOT packets.

Unsupported claims:

- The snippets are not accepted as a composable full-circuit patch set.
- The snippets are not accepted full-circuit replay certificates.
- The overlapping line-1378 and line-1381 source windows must be resolved before B7 ledger credit.
- No occurrence or proxy-T reduction is accepted.

## Interpretation

This gate converts the prior replay obligation into concrete bounded patch snippets, which is real forward motion. It also exposes why B7 still cannot count a saving: line 1378 and line 1381 patches overlap on source lines 1369-1377, so independent local snippets are not yet a composable full-circuit replacement. The next gate must merge or resynthesize the overlapping patch region and then replay it against the source circuit.
