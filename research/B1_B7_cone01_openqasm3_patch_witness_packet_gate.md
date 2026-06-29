# B1/B7 cone_01 OpenQASM 3 Patch Witness Packet Gate

- Method: `b1_b7_cone01_openqasm3_patch_witness_packet_gate_v0`
- Status: `cone01_openqasm3_patch_witness_packet_passed_without_b7_resource_credit`
- Model status: `openqasm3_patch_witness_packet_is_reviewable_without_b7_credit`
- Workload: `qasmbench_medium_exact/gcm_h6.qasm`
- Supported claim: The OpenQASM 3 source-map evidence has been reduced into a compact three-row patch witness packet for candidate lines 268, 1378, and 1381. The packet records selected versus dropped-overlap disposition, source windows, OpenQASM 3 line mapping, context hashes, local certificate status, residuals, and resource-boundary counters.

## Inputs

- Source-map gate: `results/B1_B7_cone01_openqasm3_source_map_gate_v0.json`
- Composable patch certificate: `results/B1_B7_cone01_composable_patch_certificate_gate_v0.json`
- OpenQASM 3 patch lift: `results/B1_B7_cone01_openqasm3_composable_patch_lift_gate_v0.json`
- Non-overlap subset gate: `results/B1_B7_cone01_nonoverlap_patch_subset_gate_v0.json`
- Bounded replacement patch gate: `results/B1_B7_cone01_bounded_replacement_patch_gate_v0.json`
- QASM2 / OpenQASM 3 candidates: `results/B1_B7_cone01_qasm2_candidate_rewrite_gate/gcm_h6_line268_line1381_candidate.qasm` / `results/B1_B7_cone01_openqasm3_candidate_export_gate/gcm_h6_line268_line1381_candidate_openqasm3.qasm`

## Packet Summary

- Normalized instruction count / stream hash: 1878 / `7cd50bea1f5a3c191c5735c0891d3f70f8c07a9cfca9d6e93724e6d49cb36343`
- Source-map hash / raw-line drift count: `92a499ea6d549426095fbb0fc878f7033027991621a6d5ea1c03cd25d82e9e1e` / 0
- Witness rows / selected / dropped-overlap: 3 / 2 / 1
- Witness candidate lines: [268, 1378, 1381]
- Witness instruction indices: [263, 1372, 1375]
- Witness packet hash: `e0d2e63f3f2c16be685baef3360ff68d5765db549c5e17e655a6e74c6fb82dc8`
- Selected CNOT delta / lost overlap delta: 6 / 3
- Max witness residual / entry error: 9.049428032408627e-13 / 6.398911863522162e-13
- Accepted occurrence / proxy-T reduction / B7 claim: 0 / 0 / False

## Witness Rows

| Line | Disposition | Instruction | Operation | Window | Support | Repair | CNOT delta | Off-grid local U3 | Residual | Entry error |
| --- | --- | ---: | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| 268 | selected_nonoverlap | 263 | rz | 256-267 | [2, 14] | T-B1-004aj | 3 | 0 | 6.39893112687052e-13 | 4.525273102184799e-13 |
| 1378 | dropped_overlap | 1372 | U | 1369-1377 | [4, 8] | T-B1-004ai | 3 | 0 | 9.049428032408627e-13 | 6.398911863522162e-13 |
| 1381 | selected_nonoverlap | 1375 | U | 1369-1379 | [4, 8] | T-B1-004al | 3 | 5 | 6.513210005207597e-13 | 3.4460057102876843e-13 |

## Claim Boundary

- This is not a Qiskit OpenQASM 3 loader parse.
- This is not a symbolic exact full-circuit unitary proof.
- This is not arbitrary-input or full-Hilbert-space coverage.
- This does not recover the dropped line-1378 overlap delta.
- This does not price or eliminate the remaining line-1381 off-grid local-U3 parameters.
- This does not improve the B7 resource ledger.

## Validation

- Patch witness packet passed: True
- Validation errors: 0
