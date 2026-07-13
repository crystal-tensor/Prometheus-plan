# B4/B8 R154 Deterministic Automatic Replay Protocol

- Process passes / rows per pass: `2` / `96`
- Executions / total shots: `576` / `1179648`
- Required automatic QASM / counts / row hash matches: `96` / `288` / `96`
- Required backend-target / fixed-route matches: `3` / `6`
- New hidden seeds / selection / route changes: `0` / `false` / `false`
- Serial Aer options: `{"max_parallel_experiments": 1, "max_parallel_shots": 1, "max_parallel_threads": 1}`
- Python / Qiskit / Aer / runtime: `3.12.6` / `2.4.1` / `0.17.2` / `0.46.1`
- Contract SHA-256: `1ef1f7bec268f84a863bc46b786f4a2c3d92e4be93318ba1a399c4e582a17162`
- Execution started: `false`

R154 reuses the public R153 seed rows. A reference pass and a replay pass must
run in separate operating-system processes. Every automatic circuit is exported
as OpenQASM 3 and hashed; every arm count vector, scientific row, backend target,
and fixed route is independently hashed. Any mismatch rejects the gate.

This protocol creates no new hidden statistical evidence and does not close the
R153 replay caveat before execution. It does not support hardware performance,
temporal or real-device transfer, general route-generation advantage, quantum
advantage, BQP separation, a solved frontier, or new credit.
