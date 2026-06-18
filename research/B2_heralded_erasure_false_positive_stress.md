# B2 Heralded-Erasure False-Positive Stress v0.1

Status: **heralded_erasure_false_positive_boundary_not_shot_conditioned_decoder**

## Summary

- Method: b2_heralded_erasure_false_positive_stress_v0
- Model status: stim_generated_surface_code_with_tick_level_heralded_erasure_false_positive_stress
- Toolchain: Stim HERALDED_ERASE / DEPOLARIZE1 plus PyMatching detector-error-model decoder; candidate erasure rate is leakage_rate + false_positive_rate
- Configurations: 270
- Total shots: 324000
- Target comparisons: 288
- False-positive rates per tick: [0.0, 0.001, 0.003, 0.005]
- Candidate met count: 207
- Improved target-volume rows: 13
- Improved rows at positive false-positive rates: 5
- Positive false-positive d=5/d=7 improved rows: 5
- Max volume reduction after overhead: 4.5978260869565215
- Mean volume reduction on improved rows: 2.4620014545995943
- Validation errors: []

## False-Positive Rate Breakdown

| false-positive/tick | comparisons | candidate met | improved rows | d=5/7 improved | max reduction | mean reduction |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 72 | 58 | 8 | 8 | 4.598x | 2.423x |
| 0.001 | 72 | 55 | 5 | 5 | 4.486x | 2.525x |
| 0.003 | 72 | 49 | 0 | 0 | n/a | n/a |
| 0.005 | 72 | 45 | 0 | 0 | n/a | n/a |

## Improved Target-Volume Rows

| fp/tick | basis | p | leakage/tick | effective erasure/tick | target | baseline d | candidate d | baseline volume | candidate volume | reduction |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | x | 0.003 | 0.01 | 0.01 | 0.05 | 9 | 5 | 1692.00 | 368.00 | 4.598x |
| 0 | x | 0.001 | 0.005 | 0.005 | 0.01 | 7 | 5 | 826.00 | 368.00 | 2.245x |
| 0 | x | 0.003 | 0.003 | 0.003 | 0.02 | 7 | 5 | 826.00 | 368.00 | 2.245x |
| 0 | x | 0.003 | 0.005 | 0.005 | 0.02 | 7 | 5 | 826.00 | 368.00 | 2.245x |
| 0 | z | 0.003 | 0.01 | 0.01 | 0.05 | 7 | 5 | 826.00 | 368.00 | 2.245x |
| 0 | x | 0.005 | 0.005 | 0.005 | 0.05 | 7 | 5 | 826.00 | 368.00 | 2.245x |
| 0 | x | 0.001 | 0.01 | 0.01 | 0.02 | 9 | 7 | 1692.00 | 949.90 | 1.781x |
| 0 | x | 0.003 | 0.003 | 0.003 | 0.01 | 9 | 7 | 1692.00 | 949.90 | 1.781x |
| 0.001 | x | 0.003 | 0.01 | 0.011 | 0.05 | 9 | 5 | 1692.00 | 377.20 | 4.486x |
| 0.001 | z | 0.003 | 0.01 | 0.011 | 0.05 | 7 | 5 | 826.00 | 377.20 | 2.190x |
| 0.001 | x | 0.005 | 0.005 | 0.006 | 0.05 | 7 | 5 | 826.00 | 386.40 | 2.138x |
| 0.001 | x | 0.003 | 0.003 | 0.004 | 0.02 | 7 | 5 | 826.00 | 398.67 | 2.072x |
| 0.001 | x | 0.001 | 0.01 | 0.011 | 0.02 | 9 | 7 | 1692.00 | 973.65 | 1.738x |

## Claim Boundary

- new_code_claimed: False
- threshold_claimed: False
- calibrated_device_claimed: False
- full_physical_leakage_decoder_claimed: False
- shot_conditioned_erasure_decoder_claimed: False
- false_positive_overhead_stress_performed: True
- circuit_derived_stim_evidence: True
- reduced_rounds_used: False
- distance_3_candidate_used: False
- what_is_supported: Under a Stim generated rotated-surface-code memory circuit, some heralded-erasure target-volume improvements survive positive false-positive flag rates after explicit overhead penalties.
- what_is_not_supported: This is not a full shot-conditioned erasure decoder, calibrated leakage model, threshold estimate, new code, hardware result, or production QEC design.

## Next Gate

This artifact is a stronger false-positive stress boundary, not a full
shot-conditioned erasure decoder. The next B2 gate should either add real
shot-conditioned decoding or demote the heralded-erasure route if surviving
d=5/d=7 rows disappear under calibrated leakage and flag-noise data.
