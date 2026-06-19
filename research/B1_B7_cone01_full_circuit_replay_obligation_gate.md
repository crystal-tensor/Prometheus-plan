# B1/B7 cone_01 Full-Circuit Replay Obligation Gate

## Summary

- Method: `b1_b7_cone01_full_circuit_replay_obligation_gate_v0`
- Status: `cone01_full_circuit_replay_obligations_not_satisfied`
- Packet count / bounded exact repairs: `3` / `3`
- Resource-clean packets / unpriced off-grid packets: `2` / `1`
- Symbolic exactness / full-circuit replay events / QASM patches: `0` / `0` / `0`
- Occurrence lift / B7 ledger acceptance: `0` / `0`
- Candidate CNOT reduction if accepted: `9`
- Accepted replay / occurrence / proxy-T reduction: `0` / `0` / `0`
- Validation errors: `0`

## Packet Obligations

| Line | Repair gate | CNOT delta | Off-grid params | Blocking obligations | Accepted replay |
|---|---:|---:|---:|---:|---:|
| 1378 | T-B1-004ai | 3 | 0 | 5 | False |
| 268 | T-B1-004aj | 3 | 0 | 5 | False |
| 1381 | T-B1-004al | 3 | 5 | 7 | False |

## Claim Boundary

The current cone_01 packet route has bounded exact repairs but has not satisfied the symbolic/full-circuit replay obligations required for B7 ledger acceptance.

Unsupported claims:

- No full-circuit replay certificate is accepted.
- No source-to-replacement QASM patch is accepted.
- No occurrence class has been lifted to the 30-occurrence B7 target.
- No B7 occurrence or proxy-T reduction is accepted.

## Interpretation

The repaired packets are stronger than the raw reduced-CNOT candidates, but they remain bounded-packet evidence only. Lines 1378 and 268 still need symbolic exactness, a replay event, a replacement QASM patch, and an occurrence-class lift. Line 1381 carries those obligations plus an unpriced five-parameter off-grid resource burden already rejected by simple exact decomposition, bounded context absorption, four-rotation context search, and cheap commutation-corridor movement.
