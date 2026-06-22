# B1/B7 cone_01 Union-Region Targeted Three-Free Expansion Pricing Gate

- Method: `b1_b7_cone01_union_region_three_free_expansion_pricing_gate_v0`
- Status: `cone01_union_region_targeted_three_free_expansion_rejected`
- Model status: `best_two_free_pair_plus_one_parameter_expansion_does_not_recover_exactness`
- Workload: `qasmbench_medium_exact/gcm_h6.qasm`
- Union window: `[1369, 1379]`
- Support qubits: `[4, 8]`
- Probe scope: `best_two_free_pair_plus_one_parameter_per_sequence`
- Exhaustive for three-free search: `False`
- Orientation sequences: `['01-01', '01-10', '10-01', '10-10']`
- Targeted three-free trials: `64`
- Exact pass / fail: `0` / `64`
- Best targeted three-free residual: `0.04582709543239648`
- Best sequence / parameter triple: `10-10` / `[5, 7, 4]`
- Worst best-sequence residual: `0.3812803680403496`
- Targeted three-free proxy-T pressure if accepted: `60`
- Current line-1381 proxy-T pressure: `100`
- Targeted candidate found: `False`
- B7 ledger improvement claimed: `False`

## Claim Boundary

Within the T-B1-004bf union-region two-CNOT census candidates, this targeted probe expands each sequence's best failed two-free pair by one additional free local-U3 parameter.

Unsupported claims:
- This is not an exhaustive three-free-parameter lower bound.
- A local exact targeted-three-free candidate, if present, is not a full-circuit replay certificate.
- This does not accept occurrence removal, proxy-T reduction, or a B7 ledger improvement.

## Sequence Best Rows

- `01-01`: base pair `[10, 17]`, best triple `[10, 17, 5]`, residual `0.045827095432396485`, exact passes `0` / `16`
- `01-10`: base pair `[4, 11]`, best triple `[4, 11, 16]`, residual `0.17961780740687913`, exact passes `0` / `16`
- `10-01`: base pair `[7, 15]`, best triple `[7, 15, 8]`, residual `0.3812803680403496`, exact passes `0` / `16`
- `10-10`: base pair `[5, 7]`, best triple `[5, 7, 4]`, residual `0.04582709543239648`, exact passes `0` / `16`
