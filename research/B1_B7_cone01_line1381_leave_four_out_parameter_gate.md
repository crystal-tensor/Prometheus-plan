# B1/B7 cone_01 Line-1381 Leave-Four-Out Parameter Gate

- Method: `b1_b7_cone01_line1381_leave_four_out_parameter_gate_v0`
- Status: `cone01_line1381_no_four_parameter_free_removal`
- Model status: `line1381_off_grid_parameter_quadruples_are_leave_four_out_required`
- Workload: `qasmbench_medium_exact/gcm_h6.qasm`
- Source five-parameter repair: `results/B1_B7_cone01_five_parameter_line1381_exact_repair_gate_v0.json`
- Source leave-three-out gate: `results/B1_B7_cone01_line1381_leave_three_out_parameter_gate_v0.json`

## Result

- Current line-1381 off-grid parameter indices: `[3, 4, 9, 16, 17]`
- Base five-parameter residual: `6.513210005207597e-13`
- Leave-four-out rows: `5`
- Exact pass / fail: `0` / `5`
- Best leave-four-out residual: `0.45761708677312707` at parameters `[3, 4, 9, 16]`
- Worst leave-four-out residual: `0.8369082341779268` at parameters `[4, 9, 16, 17]`
- Minimum residual ratio to exact tolerance: `45761708.67731271`
- Four-parameter free removal accepted: `False`
- Accepted occurrence / proxy-T reduction / B7 claim: `0` / `0` / `False`

## Leave-Four-Out Rows

| Fixed parameters | Snap errors | Reoptimized indices | Residual | Exact |
| --- | ---: | --- | ---: | --- |
| [3, 4, 9, 16] | [0.142527506515, 0.362110796574, 0.267119127289, 0.226452509199] | `[17]` | 0.457617086773 | False |
| [3, 4, 9, 17] | [0.142527506515, 0.362110796574, 0.267119127289, 0.362110796574] | `[16]` | 0.637547292236 | False |
| [3, 4, 16, 17] | [0.142527506515, 0.362110796574, 0.226452509199, 0.362110796574] | `[9]` | 0.771964587059 | False |
| [3, 9, 16, 17] | [0.142527506515, 0.267119127289, 0.226452509199, 0.362110796574] | `[4]` | 0.470136262704 | False |
| [4, 9, 16, 17] | [0.362110796574, 0.267119127289, 0.226452509199, 0.362110796574] | `[3]` | 0.836908234178 | False |

## Claim Boundary

- This is a scaffold-local leave-four-out pressure gate, not a global minimality theorem.
- The result blocks a cheap four-parameter removal claim for line 1381, but it does not remove, absorb, or symbolically decompose the five-parameter burden.
