# B5 Canonical DMRG Readiness Gate v0.1

Last updated: 2026-06-18

Status: **canonical_dmrg_readiness_gate_failed_not_production_dmrg**

## Summary

- Method: `b5_canonical_dmrg_readiness_gate_v0`
- Model status: `cross_reference_readiness_gate_not_solver`
- Instances: 9
- Readiness gates passed/failed: 0 / 8
- Two-site mean/max response error: 0.0819613 / 0.277103
- Variational MPS/ALS mean/max response error: 0.0180555 / 0.039072
- Seeded MPS pressure mean/max response error: 0.000441626 / 0.0016954
- Rows beating seeded MPS pressure, two-site / ALS: 0 / 0
- Mature canonical DMRG ready: False
- Validation errors: 0

## Readiness Gates

| Gate | Passed | Evidence | Required next step |
|---|---:|---|---|
| G1: Canonical left/right environments are present | False | two_site_canonical_environment_production_dmrg=False | Implement canonical-center sweeps with stored left/right environments and orthonormal residual checks. |
| G2: Production DMRG is available | False | two_site_production_dmrg=False; variational_production_dmrg=False | Replace prototype optimizers with a mature finite-system DMRG/MPS solver and convergence ledger. |
| G3: Non-seeded tensor references beat the seeded pressure reference | False | two_site_rows_beating_seeded_mps_pressure_reference=0; variational_mps_rows_beating_seeded_mps_pressure_reference=0 | Produce non-exact-state-seeded tensor rows that beat the seeded MPS pressure reference under the same D5 observables. |
| G4: Two-site prototype improves mean response error over one-site ALS | False | two_site_mean_relative_response_error=0.0819613; variational_mps_als_mean_relative_response_error=0.0180555; two_site_rows_beating_variational_mps_als_reference=4 | Improve the two-site update or demote it behind the stronger one-site ALS pressure reference. |
| G5: Prototype fixed-sector norms are stable before normalization | False | threshold=0.01; two_site_min_fixed_sector_norm_before_normalization=0.000434145; variational_min_fixed_sector_norm_before_normalization=0.000164833; seeded_min_fixed_sector_norm_before_normalization=0.999101 | Add canonical gauges and sector-aware initialization so selected states do not rely on tiny fixed-sector projection norms. |
| G6: Best non-seeded max response error is within seeded pressure max error | False | two_site_max_relative_response_error=0.277103; variational_mps_als_max_relative_response_error=0.039072; seeded_mps_pressure_max_relative_response_error=0.0016954 | Close the worst-row gap to the exact-state-seeded pressure reference before claiming a mature tensor denominator. |
| G7: Same-access quantum response kernel exists | False | quantum_response_win_claimed=False; same_access_response_oracle_available=False | If pursuing a quantum route, add state-preparation, mixing, measurement, and confidence costs on the same rows. |
| G8: Full cost accounting is ready for B10 same-access comparison | False | optimizer_loop_costs=missing; tensor_environment_costs=missing; quantum_measurement_costs=missing | Add wall-clock, matvec, sweep, memory, shot, and optimizer-loop costs before feeding a positive B10 route. |

## Interpretation

The current B5 tensor portfolio is useful as a pressure ladder, but it is not ready to be promoted to a mature canonical-DMRG denominator.
The exact-state-seeded MPS pressure reference remains strongest by response error, while both non-seeded prototypes have zero rows beating it.
This gate therefore closes T-B5-005 as a readiness audit and opens the next implementation task: build an actual canonical-environment solver or a same-access response oracle with full costs.

## Claim Boundary

- what_is_supported: A cross-reference readiness audit over the current B5 tensor and embedding pressure references.
- what_is_not_supported: This is not a production DMRG implementation, not a canonical-environment solver, not a quantum response kernel, not a same-access positive B10 route, and not an accuracy-per-resource win.
- next_gate: Implement mature canonical-environment DMRG/MPS with convergence and cost ledgers, or provide a same-access response oracle with full state-preparation and measurement costs.
- mature_canonical_dmrg_ready: False
- production_dmrg: False
- canonical_environment_production_dmrg: False
- quantum_response_win_claimed: False
- accuracy_per_resource_win_claimed: False
- same_access_positive_route_claimed: False
