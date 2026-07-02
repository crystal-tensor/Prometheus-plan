# B3/B10 Full-Covariance Denominator Replay Manifest Gate

Status: `b3_b10_full_covariance_denominator_replay_manifest_open_missing_artifact`

## Summary

- Method: `b3_b10_full_covariance_denominator_replay_manifest_gate_v0`
- Manifest: `B3-R1-full-covariance-denominator-replay-manifest`
- Provenance manifest: `B3-R1-full-covariance-provenance-manifest`
- Downstream packet: `B3-R1-full-compiled-covariance`
- Provenance manifest hash: `fdd5573fad11326b92f633c9d477cd83422106724d3e15ccd4999ca76c1e2811`
- Manifest hash: `d2e3e564caaa97f8f2a61805637651e94f2f6d7f5c86d6fa5f80ab87b9e53fde`
- Requirements passed/failed: `6` / `3`
- Failed requirement IDs: `['P6', 'P7', 'P8']`
- Required key / production key / evidence file count: `15` / `11` / `12`
- Row-aligned / compiled-pilot instances: `4` / `1`
- Selected-CI larger-basis denominator wins: `0`
- Max optimizer-loop lower-bound shots: `475043013690000`
- Submitted manifest exists: `False`
- Accepted priority reopen rows: `0`
- validation_error_count: `0`

## Manifest Packet

- Submission path: `results/B3_B10_full_covariance_denominator_replay_manifest_submissions/B3-R1-full-covariance-denominator-replay-manifest.json`

Required evidence files:

- accepted_full_covariance_provenance_manifest
- four_row_scope_manifest
- selected_ci_or_fci_reference_table
- compiled_covariance_replay_command
- grouped_observable_covariance_ledger
- derivative_shot_floor_replay_table
- optimizer_loop_cost_ledger
- same_access_denominator_decision_table
- b10_access_contract_boundary_note
- reference_validation_protocol
- negative_boundary_manifest
- claim_boundary_note

Acceptance predicates:

- manifest_id equals B3-R1-full-covariance-denominator-replay-manifest
- provenance_manifest_id equals B3-R1-full-covariance-provenance-manifest
- downstream_packet_id equals B3-R1-full-compiled-covariance
- provenance_manifest_hash matches the source full-covariance provenance manifest hash
- four-row scope, selected-CI/FCI reference table, compiled-covariance replay command, grouped-observable ledger, derivative shot-floor replay, optimizer-loop ledger, same-access decision, B10 access boundary, and validation protocol are hash-bound
- replay_hashes bind provenance_manifest_hash, downstream_packet_id, and row_aligned_instance_count
- source evidence files are present and hash-bound
- claim_boundary forbids B3 reopen, positive same-access route, reaction-dynamics solution, quantum advantage, and BQP separation claims

## Requirement Results

- P1 [PASS]: Full-covariance provenance manifest gate remains valid and blocked only on P6/P7/P8
- P2 [PASS]: Denominator replay manifest is bound to the full compiled-covariance packet
- P3 [PASS]: Manifest packet carries locked denominator replay schema and evidence classes
- P4 [PASS]: Four-row scope and negative denominator pressure remain preserved
- P5 [PASS]: Same-access and B10 boundary remain negative before replay evidence
- P6 [FAIL]: Denominator replay manifest artifact has been submitted
- P7 [FAIL]: Submitted manifest satisfies the locked denominator replay schema
- P8 [FAIL]: Submitted manifest is source-backed, provenance-bound, replay-bound, and claim-boundary-bound
- P9 [PASS]: Forbidden reopen, solution, advantage, and BQP claims remain false

## Claim Boundary

- Supported: The B3/B10 full-covariance route now has a denominator-replay manifest packet that must bind the provenance manifest, four-row denominator references, replay commands, optimizer-loop cost ledger, B10 access boundary, and negative claim boundary.
- Not supported: No denominator replay manifest or full-covariance row has been submitted or accepted; B3 remains demoted and no reaction-dynamics solution, positive same-access route, quantum advantage, or BQP separation is supported.
- Next gate: Submit B3-R1-full-covariance-denominator-replay-manifest with the accepted provenance manifest hash, four-row denominator reference table, compiled covariance replay command, optimizer-loop cost ledger, same-access decision hash, B10 access boundary hash, and explicit claim boundary.
- b3_reopen_ready: False
- positive_same_access_route_claimed: False
- reaction_dynamics_solution_claimed: False
- quantum_advantage_claimed: False
- bqp_separation_claimed: False

## Validation

- validation_error_count: 0
