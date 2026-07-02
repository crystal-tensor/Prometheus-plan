# B3/B10 Full-Covariance Row Replay-Validation Manifest Gate

Status: `b3_b10_full_covariance_row_replay_validation_manifest_open_missing_artifact`

## Summary

- Method: `b3_b10_full_covariance_row_replay_validation_manifest_gate_v0`
- Manifest: `B3-R1-full-covariance-row-replay-validation-manifest`
- Denominator replay manifest: `B3-R1-full-covariance-denominator-replay-manifest`
- Downstream packet: `B3-R1-full-compiled-covariance`
- Denominator manifest hash: `d2e3e564caaa97f8f2a61805637651e94f2f6d7f5c86d6fa5f80ab87b9e53fde`
- Provenance manifest hash: `fdd5573fad11326b92f633c9d477cd83422106724d3e15ccd4999ca76c1e2811`
- Manifest hash: `1b1d0b18bd2c1027e36dcb70c281c4d5f5f52b9d47ac047f29841334651b955f`
- Requirements passed/failed: `6` / `3`
- Failed requirement IDs: `['P6', 'P7', 'P8']`
- Required key / production key / evidence file count: `18` / `15` / `14`
- Row-aligned / compiled-pilot instances: `4` / `1`
- Selected-CI larger-basis denominator wins: `0`
- Max optimizer-loop lower-bound shots: `475043013690000`
- Submitted manifest exists: `False`
- Accepted priority reopen rows: `0`
- validation_error_count: `0`

## Row Replay-Validation Manifest Packet

- Submission path: `results/B3_B10_full_covariance_row_replay_validation_manifest_submissions/B3-R1-full-covariance-row-replay-validation-manifest.json`

Required evidence files:

- accepted_denominator_replay_manifest
- full_covariance_row_scope_manifest
- full_covariance_row_table
- compiled_state_replay_or_sampler_trace
- pauli_grouping_covariance_replay
- derivative_estimator_replay
- selected_ci_fci_denominator_replay
- optimizer_loop_cost_replay
- same_access_decision_replay
- b10_access_boundary_replay
- row_acceptance_ledger
- negative_boundary_nonpromotion_note
- reproduction_command_manifest
- claim_boundary_note

Acceptance predicates:

- manifest_id equals B3-R1-full-covariance-row-replay-validation-manifest
- denominator_replay_manifest_id equals B3-R1-full-covariance-denominator-replay-manifest
- downstream_packet_id equals B3-R1-full-compiled-covariance
- denominator_manifest_hash and provenance_manifest_hash match the source gates
- full covariance row table, compiled-state replay, Pauli grouping covariance replay, derivative estimator replay, denominator replay, optimizer-loop cost replay, same-access decision replay, and B10 access boundary replay are hash-bound
- row_acceptance_ledger and negative_boundary_nonpromotion_hash keep accepted rows at 0 until full evidence exists
- source evidence files are present and replay_hashes bind denominator manifest, provenance manifest, downstream packet, row count, and denominator-win count
- claim_boundary forbids B3 reopen, positive same-access route, reaction-dynamics solution, quantum advantage, and BQP separation claims until accepted

## Requirement Results

- P1 [PASS]: Denominator replay manifest gate remains valid and blocked only on P6/P7/P8
- P2 [PASS]: Row replay manifest is bound to denominator replay and full compiled-covariance packet
- P3 [PASS]: Row replay packet carries locked replay schema and evidence classes
- P4 [PASS]: Four-row scope and denominator negative boundary remain preserved
- P5 [PASS]: B3/B10 route remains non-promoted before accepted rows
- P6 [FAIL]: Full-covariance row replay-validation manifest artifact has been submitted
- P7 [FAIL]: Submitted row replay manifest satisfies the locked replay schema
- P8 [FAIL]: Submitted row replay manifest is source-backed, gate-bound, replay-bound, and claim-boundary-safe
- P9 [PASS]: Forbidden row acceptance, solution, advantage, and BQP claims remain false

## Claim Boundary

- Supported: The B3/B10 full-covariance reopen route now has a row replay-validation manifest packet after the denominator replay manifest and before any full compiled-state covariance rows can count.
- Not supported: No row replay-validation manifest or full-covariance row has been submitted or accepted; B3 remains demoted and no reaction-dynamics solution, positive same-access route, quantum advantage, or BQP separation is supported.
- Next gate: Submit B3-R1-full-covariance-row-replay-validation-manifest with denominator manifest hash, row table replay, compiled-state replay, covariance replay, derivative estimator replay, denominator replay, optimizer-loop cost replay, same-access decision replay, B10 access-boundary replay, row acceptance ledger, and claim boundary before B3-R1-full-compiled-covariance rows can count.
- accepted_full_covariance_rows: 0
- b3_reopen_ready: False
- positive_same_access_route_claimed: False
- reaction_dynamics_solution_claimed: False
- quantum_advantage_claimed: False
- bqp_separation_claimed: False

## Validation

- validation_error_count: 0
