# B1/B7 cone_01 Line-1381 Local-U3 Pricing Boundary Gate

- Method: `b1_b7_cone01_line1381_local_u3_pricing_gate_v0`
- Status: `cone01_line1381_local_u3_pricing_boundary_no_b7_credit`
- Model status: `semantic_patch_certificate_blocked_by_unpriced_local_u3_and_dropped_line1378`
- Workload: `qasmbench_medium_exact/gcm_h6.qasm`
- Source composable patch: `results/B1_B7_cone01_composable_patch_certificate_gate_v0.json`
- Source non-overlap subset: `results/B1_B7_cone01_nonoverlap_patch_subset_gate_v0.json`

## Result

- Semantic patch certificate passed: `True`
- Selected lines: `[268, 1381]`
- Dropped overlap lines: `[1378]`
- Selected CNOT delta: `6`
- Lost CNOT delta from line 1378: `3`
- Line-1381 off-grid local-U3 parameters: `5`
- Line-1381 unpriced proxy-T pressure: `100`
- Selected unpriced proxy-T pressure: `100`
- Local-U3 pricing boundary passed: `True`
- Local-U3 resource pricing accepted: `False`
- Accepted occurrence / proxy-T reduction: `0` / `0`

## Claim Boundary

- This is a resource-pricing boundary, not a resource win.
- B7 ledger improvement remains 0 until line 1381 is priced/eliminated/absorbed and line 1378 is recovered or replaced by another occurrence-removing route.
