# B4/B8 R156 Transpiler Variant-Capture Protocol

- Frozen row: `FakeNairobiV2` / trial `21`
- Task / transpiler seed: `dense_validation_xy_network_n6` / `105203961`
- Independent processes / compilations: `32` / `32`
- Simulation executions / shots: `0` / `0`
- Expected R155 final-QASM variants: `2`
- Full callback traces and final OpenQASM 3 retained: `true`
- New hidden seeds / selection / route changes: `0` / `false` / `false`
- Contract SHA-256: `04911bf4f81e568b67380990f2a8b3e18fe6ed50930d258fa12cd99996bbaf76`
- Execution started: `false`

## Frozen Diagnostic

R156 runs only the public R155 mismatch row. Each compilation gets a fresh
operating-system process under the same one-thread environment, Qiskit version,
optimization level, target snapshot, and transpiler seed. The callback records
the circuit hash and a bounded property-set summary after every pass, while the
final OpenQASM 3 artifact is retained for structured comparison.

Diagnostic completion does not require two variants. One, two, or more final
hashes must be retained without post-hoc exclusion. A first divergent pass is
an observed localization boundary, not proof that the named pass or its
implementation is the lower-level cause. This unopened protocol makes no
hardware, transfer, route-advantage, quantum-advantage, BQP, solved-frontier,
or research-credit claim.
