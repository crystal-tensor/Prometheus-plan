# B1/B7 Cone01 R7 R1 Submission Contract Gate

- Target: `T-B1-004di/T-B7-012r`
- Method: `b1_b7_cone01_r7_r1_submission_contract_gate_v0`
- Status: `cone01_r7_r1_submission_contract_ready_for_external_pr`
- Contract: `B1-B7-cone01-R7-R1-submission-contract`
- Contract hash: `ffee37b9f6d07567fb60488cec42140757903ff8cb2deec812f4195f91bd897b`
- Contract path: `results/B1_B7_cone01_r1_line1381_resolution_submissions/B1-B7-cone01-R1-line1381-resolution.contract.json`
- Target submission: `results/B1_B7_cone01_r1_line1381_resolution_submissions/B1-B7-cone01-R1-line1381-resolution.json`

## Result

The R7 contract gate passes 10/10 requirements. It creates a separate contract artifact for the next R1 PR while keeping the real R1 submission absent and B7 credit at zero.

## Acceptance Routes

### Route A - parameter_elimination_with_replay_or_symbolic_equivalence

- packet_id == B1-B7-cone01-R1-line1381-resolution
- source_r6_inventory_hash matches this contract
- line1381_off_grid_parameter_count_before == 5
- line1381_off_grid_parameter_count_after == 0
- line1381_resolution_artifact_hash is present
- full_replay_or_symbolic_equivalence_hash is present
- resource_delta_ledger_hash is present
- no_double_counting_ledger_hash is present
- all six evidence rows are referenced by hash

### Route B - physical_pricing_replay_beats_boundary

- packet_id == B1-B7-cone01-R1-line1381-resolution
- source_r6_inventory_hash matches this contract
- physical_pricing_replay.cost_minus_credit <= 0
- physical_pricing_replay_hash is present
- resource_delta_ledger_hash is present
- no_double_counting_ledger_hash is present
- all six evidence rows are referenced by hash
- claim boundary forbids B7 credit until resource-escape acceptance accepts the route

## Evidence Bindings

- `E1` line1381_repaired_packet_candidate -> result `1c5bb9ade0ed1367e30d3c41fbc0cf83055a490e31bd5968feabfd5f2b722eb5`, report `ec5d9ecde524de8886ab9f18e24dd0d2de5d2e1081c2b3b7f7fdca5c84620f69`
- `E2` line1381_local_u3_pricing_boundary -> result `3d86831c11f7d758e72f794971ba283b0fc1a884093929b3f810bfdfe97a8275`, report `85c6fda0ba5b94e9a2c994c7a5e8ae075ae6fb5f6ea47058496bd9aed885e21a`
- `E3` physical_synthesis_pricing_rejection -> result `bca6235672c89680c12894dd934deee34880dc2b06206c8ad35459a0385e08e6`, report `c2462ee1945bfe0c7079785965725c302de6ed15b454c0db4fda51357a2c1e31`
- `E4` openqasm3_qiskit_loader_evidence_seal -> result `f7a5f57ced33e3d8c3f8be12fbcd0dba26a5b42206dac8bb0e1ed1723a735ad2`, report `7a648d78758b0f6499d7a743993714fef3d47932b9b02ec5de317228c7828dc7`
- `E5` openqasm3_seeded_product_replay -> result `1e5ca69059d4b991198968b1e7b419133aff5dbf65d542c4038323cf9520d8a7`, report `dac7d37e1cf4104902d642bacc899f7e96c52cb4b36934bba7b1ab292f6a9ec2`
- `E6` seeded_resource_boundary -> result `f57ff6dd952167f65ce4cdfab1823d5d1480708830be45e59de576dab418723c`, report `9695e8092e4dfa0be86c012b2ec733abb629edf0c4ff99f6b9bbf5a96f06e989`

## Required Submission File Classes

- line1381_resolution_manifest
- line1381_rewritten_patch_or_parameter_elimination_artifact
- full_replay_or_symbolic_equivalence_certificate
- physical_pricing_replay
- resource_delta_ledger
- no_double_counting_ledger
- qiskit_loader_seeded_replay_reference
- claim_boundary_note

## Boundary

- line1381 off-grid parameters: `5`
- line1381 unpriced proxy-T pressure: `100`
- Target submission exists: `False`
- Accepted occurrence / proxy-T reduction: `0` / `0`
- B7 credit delta / STV credit: `0` / `0`

## Requirement Results

- `C1` PASS: R6 inventory is current and source-bound to R1
- `C2` PASS: The real R1 submission artifact is still absent
- `C3` PASS: Contract is non-conflicting and points at a separate .contract.json artifact
- `C4` PASS: All six R6 evidence rows are hash-bound in the contract
- `C5` PASS: All eight missing R1 submission file classes are represented
- `C6` PASS: Route A requires eliminating all five line1381 off-grid parameters
- `C7` PASS: Route B requires honest physical pricing to beat the current boundary
- `C8` PASS: Forbidden B1/B7 claims remain impossible inside the contract
- `C9` PASS: Negative R1 evidence can be submitted without pretending to solve R1
- `C10` PASS: Contract is hash-bound to R1, R6, triage, and acceptance packet sources

## Claim Boundary

- Supported: R7 creates a hash-bound R1 submission contract that external PRs can satisfy or refute.
- Not supported: No submitted R1 resolution artifact, line1381 parameter elimination, physical-pricing win, accepted exit route, occurrence removal, proxy-T reduction, B7 credit, or resource saving is supported.
- Next gate: Submit the target R1 artifact against this contract, either by eliminating all five line1381 off-grid parameters with replay/symbolic equivalence or by providing a physical-pricing replay with cost-minus-credit <= 0.

This contract gate does not claim resource saving, occurrence removal, proxy-T reduction, B7 ledger improvement, FT resource credit, or a solved B1/B7 problem.

## Validation

- validation_error_count: `0`
