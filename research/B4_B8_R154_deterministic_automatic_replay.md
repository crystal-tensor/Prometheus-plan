# B4/B8 R154 Deterministic Automatic Replay

- Preregistered verdict: **ACCEPT**
- Automatic QASM matches: `96 / 96`
- Arm-count matches: `288 / 288`
- Scientific-row matches: `96 / 96`
- Backend-target / fixed-route matches: `3 / 3` / `6 / 6`
- R153 acceptance-decision matches: `10 / 10`
- Stored R153 core-row matches under serial controls: `96 / 96`
- Total replay mismatches: `0`
- Separate process instances: `true`
- Serial environment / simulator options: `true` / `true`
- Conditions passed / failed: `10` / `0`
- New hidden seeds / new credit: `0` / `0`

## Acceptance Conditions

- A1 PASS: contract, protocol, R153 result, seeds, routes, and sources remain exact; value `True`, threshold `True`.
- A2 PASS: two separate processes each execute 96 rows and 288 circuits; value `[96, 96, 288, 288, True]`, threshold `[96, 96, 288, 288, True]`.
- A3 PASS: automatic OpenQASM 3 hashes; value `96`, threshold `96`.
- A4 PASS: fixed repaired and denominator route hashes; value `6`, threshold `6`.
- A5 PASS: canonical arm-count hashes; value `288`, threshold `288`.
- A6 PASS: canonical scientific-row hashes; value `96`, threshold `96`.
- A7 PASS: backend-target descriptor hashes; value `3`, threshold `3`.
- A8 PASS: serial environment and simulator options; value `[True, True]`, threshold `[True, True]`.
- A9 PASS: R153 decisions reproduce and total mismatch count is zero; value `[10, 0]`, threshold `[10, 0]`.
- A10 PASS: new evidence and forbidden claims remain false; value `0`, threshold `0`.

## Claim Boundary

An ACCEPT closes only the serial-control replacement replay gate. It does not
prove that the original R153 default-parallel path is deterministic and adds no
new hidden statistical evidence. It does not support causal repair, temporal or
real-device transfer, hardware performance, general route-generation
advantage, quantum advantage, BQP separation, solved B4/B8/B10, or new credit.
