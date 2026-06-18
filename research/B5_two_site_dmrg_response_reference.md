# B5 Two-Site Finite-DMRG Response Reference v0.1

- Status: two_site_finite_dmrg_pressure_reference_not_production_dmrg_or_advantage_claim
- Method: b5_two_site_finite_dmrg_response_reference_v0
- Instances: 9
- Bond dimensions tested: [4]
- Restarts x sweeps: 2 x 4
- Mean/max relative response error: 0.08196129814275509 / 0.2771034796538877
- Rows beating one-site MPS/ALS: 4
- Rows beating exact-state-seeded MPS pressure: 0
- Production DMRG: False
- Validation errors: []

## Row Summary

| sites | U/t | selected bond | rel response error | energy error/site | overlap | beats ALS | beats seeded pressure |
|---:|---:|---:|---:|---:|---:|---|---|
| 4 | 2.0 | 4 | 5.73266e-09 | 1.11022e-16 | 1 | True | False |
| 4 | 4.0 | 4 | 1.21334e-07 | 5.45675e-14 | 1 | True | False |
| 4 | 8.0 | 4 | 1.83631e-08 | 1.11022e-16 | 1 | True | False |
| 6 | 2.0 | 4 | 0.0137544 | 0.0256028 | 0.96937 | True | False |
| 6 | 4.0 | 4 | 0.0528165 | 0.0257241 | 0.951629 | False | False |
| 6 | 8.0 | 4 | 0.166258 | 0.0202545 | 0.956301 | False | False |
| 8 | 2.0 | 4 | 0.0543932 | 0.0202454 | 0.963477 | False | False |
| 8 | 4.0 | 4 | 0.173326 | 0.0255006 | 0.939453 | False | False |
| 8 | 8.0 | 4 | 0.277103 | 0.0283637 | 0.951382 | False | False |

## Claim Boundary

- two_site_finite_dmrg_style: True
- canonical_environment_production_dmrg: False
- production_dmrg: False
- exact_state_seeded: False
- quantum_response_win_claimed: False
- accuracy_per_resource_win_claimed: False
- what_is_supported: A two-site finite-DMRG-style block update has been tested on the same 9 B5/B10 D5 response rows, with the same response observable and denominator comparisons.
- what_is_not_supported: This is not a production DMRG implementation, not a canonical-environment proof, not a 2D correlated-matter solver, not a quantum response kernel, and not an accuracy-per-resource win.
