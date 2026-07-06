# B1/B7 Cone01 R13 NL-C02 Source-Domain Binding Gate

- Target: `T-B1-004do/T-B7-012x`
- Method: `b1_b7_cone01_r13_nlc02_source_domain_binding_gate_v0`
- Status: `cone01_r13_nlc02_source_domain_binding_ready_not_full_lemma`
- Candidate: `NL-C02`
- Binding hash: `1bcce90e3b032fab819e3062f90df7f8c631aa48bf744605b6e622cbd66c5598`
- Domain hash: `8222f1c0cee51f1ad1a7e8f696938d261c01d7a1841559e451b4fc22a8a676d3`

## Result

The R13 source-domain binding gate passes 10/10 requirements. It closes O4 for the current hash chain, but does not make NL-C02 a checked negative lemma.

## Domain

- Canonical line: `1381`
- Parameter indices: `[3, 4, 9, 16, 17]`
- Parameter count: `5`
- Exact tolerance: `1e-08`
- Leave-out source count: `5`
- Normalized subset keys: `31`

## Hash Chain

- `R7` b1_b7_cone01_r7_r1_submission_contract_gate_v0: `ffee37b9f6d07567fb60488cec42140757903ff8cb2deec812f4195f91bd897b`
- `R8` b1_b7_cone01_r8_r1_contract_preflight_gate_v0: `e6d5be7ca79021780009f91fd17df8ec206db924e6d402c12472aa854bbac977`
- `R9` b1_b7_cone01_r9_r1_reroute_pressure_gate_v0: `6d91bce5a09c4407ef9d7bcac0a81a5983c186dc23b3c98edb1a91b4a4ef4505`
- `R11` b1_b7_cone01_r11_nlc02_leaveout_proof_skeleton_gate_v0: `4ec8ffb777d13acefabebfd213a61e0d7e7bc11d904ba227d8bbb6727fc833ab`
- `R12` b1_b7_cone01_r12_nlc02_tolerance_bridge_gate_v0: `f35487dc67401193e1f455cf42e2fff05900792ddb72f97a5efad2787772b6d9`

## Decision

- O4 closed for current hash chain: `True`
- Remaining open obligations: `['O1', 'O3']`
- Checked negative lemma present: `False`
- NL-C02 full lemma ready: `False`
- Reroute allowed: `False`

## Requirement Results

- `D1` PASS: R7-R12 source artifacts are validation-clean where summaries expose validation counts
- `D2` PASS: R7-R12 hash chain is consistent
- `D3` PASS: Canonical domain is the five current line1381 off-grid parameters
- `D4` PASS: R7 and R8 domain counts match the canonical five-parameter domain
- `D5` PASS: All five leave-out source files expose identical parameter indices, values, and tolerance
- `D6` PASS: Leave-out sources are validation-clean and hash-bound
- `D7` PASS: R9/R11/R12 row counts bind to the same 31 leave-out rows
- `D8` PASS: All R7-R12 stage files are file-hash and artifact-hash bound
- `D9` PASS: O4 is closed only for the current hash chain while O1/O3 remain open
- `D10` PASS: Binding is not upgraded into a checked negative lemma or reroute

## Claim Boundary

- Supported: R13 closes O4 for the current R7-R12 hash chain by binding NL-C02 to the same line1381 five-parameter domain and the same 31 leave-out subset rows.
- Not supported: R13 does not close optimizer completeness or parameterization invariance. NL-C02 is still not a checked negative lemma. No R5 reroute, R1 solution, occurrence removal, proxy-T reduction, B7 credit, resource saving, or impossibility theorem is supported.
- Next gate: Close O1 or O3; or falsify the binding with a source hash mismatch, domain drift, or a leave-out source whose parameter indices, values, or tolerance differ.

This source-domain binding gate does not claim resource saving, occurrence removal, proxy-T reduction, B7 ledger improvement, FT resource credit, a checked impossibility theorem, an R5 reroute, or a solved B1/B7 problem.

## Validation

- validation_error_count: `0`
