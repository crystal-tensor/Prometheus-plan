# B4/B8 R158 VF2 Accelerator-Boundary Protocol

- Qiskit source commit: `0fd015a22b84c9082173597a5d2304dc0aaec08c`
- Installed accelerator SHA-256: `a299d48f8d174481d389b30f1fd240a845144922f32ef918925b17243fc5f007`
- Input QASM SHA-256: `ce216610e995b4c8b4bd9de6547ac6069961e1eb8881997aa05e0068ea16ab98`
- Profiles / OS processes / direct replays: `4` / `4` / `256`
- Shared tied score: `0.45894321220828727`
- Simulation executions / shots: `0` / `0`
- Contract SHA-256: `c8ac00cb607174fa6d200c942810548f0b48e5efedf5a8bd119c56c230cfb8f8`
- Execution started: `false`

## Frozen Boundary Matrix

R158 keeps the R157 input, Target, score, and VF2 configuration fixed while removing four reconstruction layers in stages. The final profile calls the Rust accelerator repeatedly with one shared DAG, Target, configuration object, and externally constructed ErrorMap. If that profile still varies, the observation boundary moves inside per-call Rust VF2 graph/state/scoring construction, but no particular hash, iterator, floating-point, or retention mechanism is yet proved.

All 256 rows must be retained. Collapse, continued variation, another mapping, and no solution are admissible. The unopened protocol does not claim candidate-order instrumentation, a lower-level mechanism, a confirmed Qiskit bug, general compiler determinism, hardware relevance, advantage, BQP separation, solved-frontier status, or new credit.
