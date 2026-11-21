# Closed-loop X RTL: 64-shot prefix and six new trajectory responses

Date: 2026-11-21
Scope: #021/B7, #022/B2, #023 only

## Question

Can the closed-loop semantic gate survive a larger contiguous prefix while reproducing every known feedback-sensitive divergence inside that prefix?

## Frozen shard

The second multi-shot extension freezes shots 25–63, adding 39 previously uncredited X shots and 6,396 consecutive windows. Combined with the earlier evidence, the cumulative accepted set is now the contiguous prefix 0–63.

Every window is driven by the decoder's actual state trajectory:

1. raw arrivals enter persistent detector state;
2. the prior RTL correction is XORed into that state;
3. selectors are derived for the resulting syndrome;
4. the real Rust-primal plus Verilator-dual path returns a correction;
5. the host applies that correction and requires the current commit residual to be zero.

Final detector residual and logical frame are checked after all 164 windows of each shot.

## Formal result

The pinned Verilator 5.040 capture passes:

- frozen shots: 39/39;
- complete windows: 6,396/6,396;
- syndrome-valid windows: 6,396/6,396;
- occupancy checks clear: 64,465/64,465;
- commit-residual failures: 0;
- final-residual failures: 0;
- final logical-frame failures: 0;
- maximum iterations: 23;
- total iterations: 37,454;
- forbidden runtime hits: 0;
- unexpected warnings: 0.

The capture exits zero after 396.53 seconds. This includes elaboration, selector service, host control, and RTL simulation; it is not a decoder-latency measurement.

## Six additional feedback-sensitive trajectories

The earlier open-loop falsifier identified six noncanonical corrections inside shots 25–63:

| Shot | Noncanonical correction | Closed-loop response |
|---:|---:|---:|
| 29 | window 143 | window 144 |
| 36 | window 127 | window 128 |
| 38 | window 145 | window 146 |
| 54 | window 154 | window 155 |
| 58 | window 120 | window 121 |
| 60 | window 15 | window 16 |

The closed-loop result diverges from the frozen open-loop replay in exactly those six response windows and nowhere else in the shard. Each response window clears its commit residual, and every trajectory reconverges with the replay by the following window.

Together with shot 15, the accepted 0–63 prefix now contains seven feedback-sensitive shots. This tests both replay-equivalent behavior and the sequential response to matching degeneracy.

## Updated denominator

The cumulative frozen X denominator is now:

- 64/1,024 distinct shots;
- 10,496/167,936 cases;
- exactly 6.25% of the X corpus;
- 960 shots and 157,440 cases remaining.

The rejected open-loop block is still not counted. Only shots that have passed the closed-loop state-feedback route contribute to this denominator.

## Claim boundary

This establishes a passing 64-shot X prefix with seven feedback-sensitive trajectories. It does not establish full X, any Z result, AXI integration, FPGA timing/resources, measured hardware latency, `p99 <= 1 us`, miss `<= 1%`, full B2, scalable #023, or B7 resource credit.

Machine evidence ID: `49871986321dd63fc8b869f795af90b74af0f595019627f9d351494816100122` (28/28 checks).
