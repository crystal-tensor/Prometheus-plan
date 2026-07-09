# B1/B7 Cone01 R107 Material Evidence Packet Contract Gate

- Target: `T-B1-004he/T-B7-016n`
- Upstream target: `T-B1-004hd/T-B7-016m`
- Method: `b1_b7_cone01_r107_material_evidence_packet_contract_gate_v0`
- Status: `cone01_r107_material_evidence_packet_contract_ready_no_external_counter`
- Model status: `r106_materiality_blockers_converted_to_fillable_external_evidence_packet`

## Result

R107 converts the R106 materiality blockers into a fillable external
material evidence packet contract. It rejects both the empty template and
a self-declared packet that reuses the R106 negative-control artifact.

## Key Counters

- Contract required fields: `30`
- Acceptance gates: `22`
- Empty template accepted: `False`
- Empty template gates passed / failed: `5` / `18`
- Self-declared packet accepted: `False`
- Self-declared packet gates passed / failed: `18` / `5`
- Counter transition accepted: `False`
- Counter delta: `0`
- Accepted external reproductions: `0`
- Accepted external falsifications: `0`
- New credit delta: `0`

## Requirements

- `A1` PASS: R107 binds R106 materiality audit and blocker queue
- `A2` PASS: R107 emits a fillable material evidence packet contract and template
- `A3` PASS: R107 rejects the empty template before any counter audit
- `A4` PASS: R107 rejects self-declared reuse of the R106 negative-control packet
- `A5` PASS: R107 keeps counters and new credit at zero
- `A6` PASS: R107 emits blockers for key registry, signature, CI, fetch transcript, and contact verification

## Artifacts

- Result JSON: `results/B1_B7_cone01_R107_material_evidence_packet_contract_gate_v0.json`
- Contract: `results/B1_B7_cone01_o3_f4_exit_route_submissions/R107-G1-external-material-evidence-packet-contract/external-material-evidence-packet-contract.json`
- Template: `results/B1_B7_cone01_o3_f4_exit_route_submissions/R107-G1-external-material-evidence-packet-contract/external-material-evidence-packet.template.json`
- Empty-template preflight: `results/B1_B7_cone01_o3_f4_exit_route_submissions/R107-G1-external-material-evidence-packet-contract/empty-template-preflight.verdict.json`
- Self-declared negative control: `results/B1_B7_cone01_o3_f4_exit_route_submissions/R107-G1-external-material-evidence-packet-contract/self-declared-materiality-negative-control.json`
- Self-declared preflight: `results/B1_B7_cone01_o3_f4_exit_route_submissions/R107-G1-external-material-evidence-packet-contract/self-declared-packet-preflight.verdict.json`
- Blocker queue: `results/B1_B7_cone01_o3_f4_exit_route_submissions/R107-G1-post-material-evidence-contract-blocker-queue.json`

## Claim Boundary

R107 is a contract and preflight gate. It does not accept an external
reproduction, does not move any counter, and does not grant new B7/O3/
resource/layout credit. A future packet must pass this contract before a
separate single-counter audit can be run.
