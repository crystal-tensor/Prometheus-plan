# B3/B10 Full-Covariance Provenance Manifest Gate

Status: `b3_b10_full_covariance_provenance_manifest_open_missing_artifact`

## Summary

- Method: `b3_b10_full_covariance_provenance_manifest_gate_v0`
- Manifest: `B3-R1-full-covariance-provenance-manifest`
- Downstream packet: `B3-R1-full-compiled-covariance`
- Manifest hash: `fdd5573fad11326b92f633c9d477cd83422106724d3e15ccd4999ca76c1e2811`
- Requirements passed/failed: `6` / `3`
- Failed requirement IDs: `['P6', 'P7', 'P8']`
- Required key / production key / evidence file count: `11` / `8` / `10`
- Row-aligned / compiled-pilot instances: `4` / `1`
- Full compiled-state covariance computed: `False`
- Submitted manifest exists: `False`
- Accepted priority reopen rows: `0`
- validation_error_count: `0`

## Manifest Packet

- Submission path: `results/B3_B10_full_covariance_provenance_manifest_submissions/B3-R1-full-covariance-provenance-manifest.json`

Required evidence files:

- state_preparation_family_manifest
- state_preparation_circuit_hash_manifest
- compiled_covariance_protocol_note
- grouped_observable_ledger_protocol
- derivative_shot_floor_protocol
- reference_validation_protocol
- b10_access_contract_bridge_note
- source_rescue_gate_manifest
- source_negative_boundary_manifest
- claim_boundary_note

Acceptance predicates:

- manifest_id equals B3-R1-full-covariance-provenance-manifest
- downstream_packet_id equals B3-R1-full-compiled-covariance
- row_aligned_instance_count equals the locked four-row B3 scope
- state-preparation, covariance, observable-ledger, derivative-shot-floor, validation, and B10 access-contract protocol hashes are present
- source evidence files are present and hash-bound
- claim_boundary forbids B3 reopen, positive same-access route, reaction-dynamics solution, quantum advantage, and BQP separation claims

## Requirement Results

- P1 [PASS]: Priority reopen packet remains valid and blocked only on P6/P7/P8
- P2 [PASS]: Provenance manifest is bound to the full compiled-covariance reopen packet
- P3 [PASS]: Manifest packet carries locked schema and evidence file classes
- P4 [PASS]: Four-row B3 reaction-coordinate scope remains preserved
- P5 [PASS]: Current B3/B10 route remains demoted before provenance evidence
- P6 [FAIL]: Full-covariance provenance manifest artifact has been submitted
- P7 [FAIL]: Submitted manifest satisfies the locked provenance schema
- P8 [FAIL]: Submitted manifest is source-backed, downstream-bound, and four-row-bound
- P9 [PASS]: Forbidden reopen, solution, advantage, and BQP claims remain false

## Claim Boundary

- Supported: The B3/B10 full-covariance reopen route now has a concrete provenance manifest packet that must be accepted before full compiled-state covariance rows can count.
- Not supported: No provenance manifest or full-covariance row has been submitted or accepted; B3 remains demoted and no reaction-dynamics solution, positive same-access route, quantum advantage, or BQP separation is supported.
- Next gate: Submit B3-R1-full-covariance-provenance-manifest with four-row state-prep provenance, compiled covariance protocol, grouped observable ledger, derivative shot-floor protocol, validation protocol, B10 access-contract bridge hash, and claim boundary.
- b3_reopen_ready: False
- positive_same_access_route_claimed: False
- reaction_dynamics_solution_claimed: False
- quantum_advantage_claimed: False
- bqp_separation_claimed: False

## Validation

- validation_error_count: 0
