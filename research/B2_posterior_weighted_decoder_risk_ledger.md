# B2 Posterior-Weighted Decoder-Risk Ledger v0.1

Status: **posterior_weighted_decoder_risk_boundary_not_production_decoder**

## Summary

- Method: b2_posterior_weighted_decoder_risk_ledger_v0
- Model status: posterior_weighted_risk_ledger_not_circuit_level_decoder
- Source result: results/B2_shot_conditioned_erasure_decoder_boundary_v0.json
- Risk budgets: 4
- Evaluated budget/profile rows: 4608
- Source raw surviving d=5/d=7 profile rows: 6
- Mild adjusted survivors: 6
- Nominal adjusted survivors: 5
- Conservative adjusted survivors: 3
- Strict adjusted survivors: 3
- Strict high-purity adjusted survivors: 0
- Robust all-profile adjusted survival: False
- Validation errors: []

## Decoder-Risk Budgets

| budget | adjusted survivors | survivor loss | profiles with survivors | strict high-purity survivors | max adjusted reduction | mean adjusted reduction | robust all-profile |
|---|---:|---:|---:|---:|---:|---:|---|
| mild_decoder_penalty | 6 | 0 | 3 | 0 | 3.323 | 1.884 | False |
| nominal_decoder_penalty | 5 | 1 | 3 | 0 | 2.563 | 1.577 | False |
| conservative_decoder_penalty | 3 | 3 | 2 | 0 | 1.994 | 1.425 | False |
| strict_decoder_penalty | 3 | 3 | 2 | 0 | 1.794 | 1.311 | False |

## Adjusted Surviving Rows

| budget | profile | basis | p | leakage/tick | fp/tick | target | d | posterior | risk x | adjusted reduction |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| conservative_decoder_penalty | high_purity_detector_0p95 | x | 0.005 | 0.005 | 0.001 | 0.05 | 5 | 0.827 | 1.875 | 1.140 |
| conservative_decoder_penalty | nominal_lab_detector_0p90 | x | 0.003 | 0.01 | 0.001 | 0.05 | 5 | 0.901 | 2.250 | 1.994 |
| conservative_decoder_penalty | nominal_lab_detector_0p90 | x | 0.005 | 0.005 | 0.001 | 0.05 | 5 | 0.819 | 1.875 | 1.140 |
| mild_decoder_penalty | field_detector_0p80 | x | 0.005 | 0.005 | 0.001 | 0.05 | 5 | 0.801 | 1.350 | 1.583 |
| mild_decoder_penalty | high_purity_detector_0p95 | x | 0.005 | 0.005 | 0.001 | 0.05 | 5 | 0.827 | 1.225 | 1.745 |
| mild_decoder_penalty | nominal_lab_detector_0p90 | x | 0.003 | 0.01 | 0.001 | 0.05 | 5 | 0.901 | 1.350 | 3.323 |
| mild_decoder_penalty | nominal_lab_detector_0p90 | x | 0.005 | 0.005 | 0.001 | 0.05 | 5 | 0.819 | 1.225 | 1.745 |
| mild_decoder_penalty | nominal_lab_detector_0p90 | z | 0.003 | 0.01 | 0.001 | 0.05 | 5 | 0.901 | 1.350 | 1.622 |
| mild_decoder_penalty | nominal_lab_detector_0p90 | x | 0.001 | 0.01 | 0.001 | 0.02 | 7 | 0.901 | 1.350 | 1.287 |
| nominal_decoder_penalty | field_detector_0p80 | x | 0.005 | 0.005 | 0.001 | 0.05 | 5 | 0.801 | 1.750 | 1.222 |
| nominal_decoder_penalty | high_purity_detector_0p95 | x | 0.005 | 0.005 | 0.001 | 0.05 | 5 | 0.827 | 1.500 | 1.425 |
| nominal_decoder_penalty | nominal_lab_detector_0p90 | x | 0.003 | 0.01 | 0.001 | 0.05 | 5 | 0.901 | 1.750 | 2.563 |
| nominal_decoder_penalty | nominal_lab_detector_0p90 | x | 0.005 | 0.005 | 0.001 | 0.05 | 5 | 0.819 | 1.500 | 1.425 |
| nominal_decoder_penalty | nominal_lab_detector_0p90 | z | 0.003 | 0.01 | 0.001 | 0.05 | 5 | 0.901 | 1.750 | 1.251 |
| strict_decoder_penalty | high_purity_detector_0p95 | x | 0.005 | 0.005 | 0.001 | 0.05 | 5 | 0.827 | 2.000 | 1.069 |
| strict_decoder_penalty | nominal_lab_detector_0p90 | x | 0.003 | 0.01 | 0.001 | 0.05 | 5 | 0.901 | 2.500 | 1.794 |
| strict_decoder_penalty | nominal_lab_detector_0p90 | x | 0.005 | 0.005 | 0.001 | 0.05 | 5 | 0.819 | 2.000 | 1.069 |

## Claim Boundary

- new_code_claimed: False
- threshold_claimed: False
- calibrated_device_claimed: False
- full_physical_leakage_decoder_claimed: False
- production_decoder_claimed: False
- circuit_level_decoder_claimed: False
- hardware_result_claimed: False
- shot_conditioned_erasure_decoder_claimed: False
- posterior_weighted_decoder_risk_model_performed: True
- reduced_rounds_used: False
- distance_3_candidate_used: False
- what_is_supported: Posterior-calibrated rows can be re-costed with explicit decoder-risk multipliers; the surviving signal shrinks under conservative and strict risk budgets and still lacks all-profile robustness.
- what_is_not_supported: This is not a circuit-level shot-conditioned decoder, production decoder, hardware-calibrated leakage model, threshold result, new code, or hardware QEC result.

## Next Gate

The ledger keeps a small number of adjusted survivors under some risk budgets,
but strict high-purity and all-profile robustness still fail. The next B2 gate
must either implement a real circuit-level shot-conditioned decoder with these
posterior weights as decoder inputs, or demote the heralded-erasure route until
calibrated leakage and flag data support it.
