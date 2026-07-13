# B4/B8 R156 Transpiler Variant Capture

- Diagnostic completion: **ACCEPT**
- Processes / compilations: `32` / `32`
- Callback traces / rows: `32` / `1600`
- Trace-row range: `50` - `50`
- Final variants: `2`
- Known R155 variants reproduced: `true`
- Unknown variants: `0`
- Pass-sequence variants: `1`
- Simulation executions / shots: `0` / `0`
- Conditions passed / failed: `10` / `0`
- New hidden seeds / new credit: `0` / `0`

## Final Variants

- `56eb5fac162b05c918164e4850b71c0665fa139c5b3c81646d2d8d7f5119d658`: 20 processes; known R155 variant `true`; size/depth `305` / `133`.
- `fc4ab12a8f5204895c93d1320899e6b4f64f489b87adccbc7a16d7fa79a8d1f1`: 12 processes; known R155 variant `true`; size/depth `307` / `133`.

## First Observed Divergence

- Circuit: `{'count': 18, 'pass_name': 'ApplyLayout', 'pass_module': 'qiskit.transpiler.passes.layout.apply_layout', 'left_circuit_qasm_sha256': '7ab7215f90a084f0bba8bfb68d8d243c74033a5b20e705a982183fb81b61cc7e', 'right_circuit_qasm_sha256': '151a8f5c248f04fe69b4350016c4ff506485b0a97a0bf92f85441907111cff0d'}`
- Bounded property set: `{'count': 17, 'pass_name': 'VF2PostLayout', 'pass_module': 'qiskit.transpiler.passes.layout.vf2_post_layout', 'left_property_set_summary_sha256': 'b5e3ce17fe0ee5ec654083f1177896762aaa93140afe1422c3635971e4b7f033', 'right_property_set_summary_sha256': '236b30a06b09ae25f71a9f334a562a155dc1ee3dfc4a4a76fe797caf33d5eda5'}`
- All pass sequences identical: `true`
- All variant-pair sequences aligned: `true`

The only bounded property-set key that differs at callback count 17 is
`post_layout`. In the 20-process class, logical qubits 4, 5, and 6 map to
physical qubits 0, 1, and 2. In the 12-process class, logical qubits 4 and 6
exchange the endpoint assignment and map to physical qubits 2 and 0, while
logical qubit 5 remains on physical qubit 1. The input circuit hash remains
identical through `VF2PostLayout`; `ApplyLayout` is the first callback whose
circuit hash differs.

## Final-Circuit Difference

Both variants have depth `133` and `63` CX gates. The 20-process class has
`305` operations and `132` RZ gates; the 12-process class has `307` operations
and `134` RZ gates. The structured final-circuit comparison retains `26` diff
hunks. These are consequences correlated with the alternate `post_layout`
assignment, not proof of the lower-level source of the alternate assignment.

## Acceptance Conditions

- A1 PASS: contract, protocol, R155 evidence, and sources remain exact; value `True`, threshold `True`.
- A2 PASS: 32 distinct post-preregistration processes compile once; value `[32, 32, 32, 32]`, threshold `[32, 32, 32, 32]`.
- A3 PASS: all traces, final QASM files, environments, and identities are complete; value `[32, 32, True, True]`, threshold `[32, 32, True, True]`.
- A4 PASS: all callback rows preserve the frozen fields; value `True`, threshold `True`.
- A5 PASS: all final hashes are retained and classified; value `32`, threshold `32`.
- A6 PASS: pass sequences and aligned hashes are compared; value `[1, 1]`, threshold `[1, 1]`.
- A7 PASS: multiple variants receive a structured gate-level diff; value `True`, threshold `True`.
- A8 PASS: first observed divergence is emitted when identifiable; value `True`, threshold `True`.
- A9 PASS: all process artifacts and aggregate bindings are complete; value `32`, threshold `32`.
- A10 PASS: new seeds, selection, routes, sampling, mechanism, and forbidden claims remain false; value `0`, threshold `0`.

## Claim Boundary

R156 localizes the first observed divergence in complete callback traces for one
public seeded compilation row. A named pass at the first divergent callback is
an observation boundary, not proof that the pass is the lower-level mechanism
or that Qiskit has a confirmed bug. The result makes no hidden-evidence,
simulation-performance, hardware, transfer, route-advantage, quantum-advantage,
BQP, solved-frontier, or research-credit claim.
