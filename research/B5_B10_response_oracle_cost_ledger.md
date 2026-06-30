# B5/B10 Same-Access Response-Oracle Cost Ledger v0.1

Status: **same_access_response_oracle_cost_ledger_failed_no_oracle**

## Summary

- Method: `b5_b10_response_oracle_cost_ledger_v0`
- Row contract hash: `7ee407e20f51bd0c003d885c8d43282359f84bea9729f0da203b9b2c2970a9fc`
- Row contract count: 9
- Oracle requirements passed/failed: 3 / 5
- Failed oracle requirement IDs: ['O3', 'O4', 'O5', 'O6', 'O7']
- Measurement confidence ledger present: True
- State-preparation algorithm instantiated: False
- Mixing cost included: False
- Readout error included: False
- Optimizer-loop cost included: False
- Rows beating explicit D5 matvec for seeded target: 0
- Min/median/max shots to match seeded MPS pressure: 3861425434 / 7644706432712 / 284916076006665507134714675200
- Max optimistic seeded-target prep 2Q floor: 1139664304026662028538858700800
- W3 response oracle constructed: False
- Remaining positive-route packets: ['W1']
- Validation errors: []

## Oracle Requirements

| ID | Requirement | Passed | Key evidence |
|---|---|---:|---|
| O1 | W4 row contract is preserved before any oracle comparison | True | row_contract_hash=7ee407e20f51bd0c003d885c8d43282359f84bea9729f0da203b9b2c2970a9fc, row_contract_count=9, source_checks_failed=0 |
| O2 | Optimistic measurement-confidence ledger exists on all nine rows | True | instance_count=9, confidence_z=2.576, density_variance_upper_bound=1.0 |
| O3 | State-preparation algorithm and cost ledger are instantiated | False | state_preparation_floor_present=True, state_preparation_algorithm_instantiated=False, reason=sampler stress contains only an optimistic per-circuit floor |
| O4 | Mixing or response-query cost is included | False | mixing_cost_included=False, response_estimator=(E[n_i | +eta] - E[n_i | -eta]) / (2 eta) |
| O5 | Readout, noise, or backend calibration costs are included | False | readout_error_included=False, real_backend_or_hardware_rows=0 |
| O6 | Optimizer-loop or adaptive-query amplification cost is bounded | False | optimizer_loop_cost_included=False, reason=sampler stress prices fixed finite differences, not an optimizer loop |
| O7 | Oracle beats explicit D5 and seeded-pressure denominator ladder | False | rows_beating_explicit_d5_matvec_for_seeded_target=0, seeded_pressure_replaced=False, max_shots_to_match_seeded_pressure=284916076006665507134714675200, max_exact_d5_matvec_equivalent_ops=1014300 |
| O8 | Forbidden claims remain false | True | bridge_same_access_positive_route_ready=False, production_quantum_response_win_claimed=False, sampler_quantum_advantage_claimed=False, sampler_bqp_separation_claimed=False |

## Row Cost Pressure

| row | D5 ops | shots to seeded pressure | seeded prep 2Q floor | beats D5 by shots |
|---|---:|---:|---:|---:|
| 4|2 | 1620 | 284916076006665507134714675200 | 1139664304026662028538858700800 | False |
| 4|4 | 1620 | 2553758443925336829286416384 | 10215033775701347317145665536 | False |
| 4|8 | 1440 | 4610241870596310791037648896 | 18440967482385243164150595584 | False |
| 6|2 | 50400 | 11630698994 | 69784193964 | False |
| 6|4 | 47600 | 3279589736230 | 19677538417380 | False |
| 6|8 | 42000 | 7644706432712 | 45868238596272 | False |
| 8|2 | 1014300 | 3861425434 | 30891403472 | False |
| 8|4 | 926100 | 139216418548 | 1113731348384 | False |
| 8|8 | 705600 | 6695603121926592 | 53564824975412736 | False |

## Claim Boundary

- what_is_supported: W3 is executed as a same-access response-oracle cost ledger over the locked nine B5/B10 rows. The measurement-confidence floor is present, but the full oracle is not constructed.
- what_is_not_supported: This is not a state-preparation algorithm, not a mixing/query oracle, not a hardware/noise-calibrated response oracle, not production DMRG, not a positive same-access route, not quantum advantage, and not BQP separation.
- kill_condition: Any future W3 retry must preserve the row-contract hash, instantiate state preparation, include mixing/query and readout/noise costs, bound optimizer-loop amplification, and beat the seeded-pressure denominator ladder without hidden access advantages.
- next_gate: Run W1 production DMRG/MPS; W3 is closed unless a real same-access response oracle is instantiated.
- production_dmrg_claimed: False
- sampling_oracle_constructed: False
- same_access_response_oracle_constructed: False
- same_access_positive_route_claimed: False
- quantum_response_win_claimed: False
- accuracy_per_resource_win_claimed: False
- quantum_advantage_claimed: False
- bqp_separation_claimed: False
- dequantization_theorem_claimed: False
- sampling_access_theorem_claimed: False

## Interpretation

W3 is now an executed negative ledger, not an unexamined opportunity. The
existing sampler stress supplies a measurement-confidence floor, but the
project still lacks instantiated state preparation, mixing/query costs,
readout/noise costs, optimizer-loop amplification, and a denominator win.
The remaining positive B5/B10 route is W1 production DMRG/MPS unless a
future W3 submission supplies a real same-access response oracle.
