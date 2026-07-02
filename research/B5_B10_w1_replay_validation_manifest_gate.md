# B5/B10 W1 Replay-Validation Manifest Gate

Status: `w1_replay_validation_manifest_open_missing_artifact`

## Summary

- Method: `b5_b10_w1_replay_validation_manifest_gate_v0`
- Manifest: `B5B10-W1-priority-row-replay-validation-manifest`
- Provenance manifest: `B5B10-W1-priority-row-provenance-manifest`
- Priority row: `D5H_s8_u2_eta0.25_n4x4_obs_density_site_4`
- Provenance manifest hash: `2616aae62cc6af33da763faac1d7275e975ca9699dd752231b600975cff74b90`
- Manifest hash: `21de29a096bd3c6534b4420a7d69afca1bc4c95e80750657f3a3d357dd17dd97`
- Requirements passed/failed: `6` / `3`
- Failed requirement IDs: `['P6', 'P7', 'P8']`
- Required key / production key / evidence file count: `17` / `13` / `13`
- Row contracts / prototype trace hashes / discarded-weight metric rows: `9` / `9` / `9`
- Production contract rows accepted: `0`
- Submitted manifest exists: `False`
- Accepted priority rows: `0`
- validation_error_count: `0`

## Manifest Packet

- Submission path: `results/B5_B10_w1_replay_validation_manifest_submissions/B5B10-W1-priority-row-replay-validation-manifest.json`

Required evidence files:

- accepted_priority_row_provenance_manifest
- canonical_state_replay_manifest
- left_environment_replay_manifest
- right_environment_replay_manifest
- orthonormal_residual_replay_table
- discarded_weight_replay_table
- convergence_replay_table
- same_access_cost_ledger
- wall_clock_memory_ledger
- sweep_matvec_count_ledger
- seeded_pressure_comparison_manifest
- b10_access_boundary_note
- claim_boundary_note

Acceptance predicates:

- manifest_id equals B5B10-W1-priority-row-replay-validation-manifest
- provenance_manifest_id equals B5B10-W1-priority-row-provenance-manifest
- row_id equals D5H_s8_u2_eta0.25_n4x4_obs_density_site_4
- row_contract_hash and provenance_manifest_hash match the source gates
- canonical state, left/right environments, residuals, discarded weights, convergence, same-access cost, wall-clock/memory, sweep/matvec counts, seeded-pressure comparison, and B10 access boundary are hash-bound
- replay_hashes bind row_contract_hash, provenance_manifest_hash, and row_id
- source evidence files are present and hash-bound
- claim_boundary forbids production DMRG, same-access positive route, quantum advantage, and BQP separation claims until accepted rows exist

## Requirement Results

- P1 [PASS]: Priority-row provenance manifest gate remains valid and blocked only on P6/P7/P8
- P2 [PASS]: Replay-validation manifest is bound to the priority W1 row contract
- P3 [PASS]: Manifest packet carries locked replay-validation schema and evidence classes
- P4 [PASS]: Prototype scope and production blockers remain preserved
- P5 [PASS]: Blocker queue still has no submitted or accepted production rows
- P6 [FAIL]: Replay-validation manifest artifact has been submitted
- P7 [FAIL]: Submitted manifest satisfies the locked replay-validation schema
- P8 [FAIL]: Submitted manifest is source-backed, row-bound, replay-bound, and claim-boundary-bound
- P9 [PASS]: Forbidden production, positive-route, advantage, and BQP claims remain false

## Claim Boundary

- Supported: The B5/B10 W1 priority-row route now has a replay-validation manifest packet that must bind canonical states, environments, residuals, discarded weights, convergence, same-access cost, resource ledgers, seeded-pressure comparison, and B10 boundary evidence before the priority row can count.
- Not supported: No replay-validation manifest or priority production row has been submitted or accepted; no production DMRG denominator, same-access positive route, quantum advantage, or BQP separation is supported.
- Next gate: Submit B5B10-W1-priority-row-replay-validation-manifest with the accepted provenance manifest hash, row replay hashes, cost ledgers, seeded-pressure comparison, B10 access boundary, and claim boundary before the priority production-row artifact can count.
- production_dmrg_claimed: False
- same_access_positive_route_claimed: False
- quantum_advantage_claimed: False
- bqp_separation_claimed: False

## Validation

- validation_error_count: 0
