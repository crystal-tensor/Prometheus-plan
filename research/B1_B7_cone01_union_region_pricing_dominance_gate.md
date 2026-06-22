# B1/B7 cone_01 Union-Region Pricing Dominance Gate

- Method: `b1_b7_cone01_union_region_pricing_dominance_gate_v0`
- Status: `cone01_union_region_two_cnot_candidates_pricing_dominated`
- Model status: `current_line1381_patch_has_lower_local_u3_pricing_pressure`
- Workload: `qasmbench_medium_exact/gcm_h6.qasm`
- Source 2-CNOT census: `results/B1_B7_cone01_union_region_two_cnot_orientation_census_gate_v0.json`
- Source line-1381 pricing: `results/B1_B7_cone01_line1381_local_u3_pricing_gate_v0.json`
- Source overlap bound: `results/B1_B7_cone01_overlap_additivity_bound_gate_v0.json`

## Result

- Union window: `[1369, 1379]`
- Source CNOT / replacement CNOT / CNOT delta: `5` / `2` / `3`
- Current line-1381 off-grid parameters / proxy-T pressure: `5` / `100`
- Reviewed exact 2-CNOT census sequences: `4`
- Best priced census sequence: `01-10`
- Census min off-grid parameters / proxy-T pressure: `13` / `260`
- Delta vs current line-1381 off-grid / proxy-T pressure: `8` / `160`
- Census candidate dominates current pricing: `False`
- Current patch pricing dominates census: `True`
- Selected replacement changed: `False`
- Accepted occurrence / proxy-T reduction / B7 claim: `0` / `0` / `False`

## Claim Boundary

- This is a pricing-dominance check, not a global optimality theorem.
- The 2-CNOT census remains robustness evidence; it is not adopted as a better B7 resource route.
