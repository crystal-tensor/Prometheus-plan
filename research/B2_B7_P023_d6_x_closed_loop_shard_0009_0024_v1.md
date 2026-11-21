# Closed-loop X RTL: first multi-shot shard

Date: 2026-11-21
Scope: #021/B7, #022/B2, #023 only

## Question

Does a closed-loop streaming decoder preserve its correctness contract across a contiguous frozen prefix, including the first known degenerate-matching counterexample?

## Frozen shard

The first multi-shot closed-loop extension freezes fifteen previously uncredited X shots:

- shots 9–14;
- shots 16–24.

Together with the previously accepted shots 0–8 and 15, the cumulative accepted set is now the contiguous prefix 0–24. No open-loop result is imported as acceptance evidence.

Each window derives its syndrome from raw arrivals XOR the correction state returned by earlier RTL windows. The persistent PyMatching selector service sees that actual state, and the real Rust-primal plus Verilator-dual path must satisfy:

- a syndrome-valid matching at every window;
- zero residual on every committed detector set;
- zero final detector residual;
- the accepted final logical frame.

## Formal result

The pinned Verilator 5.040 capture passes:

- frozen shots: 15/15;
- complete windows: 2,460/2,460;
- syndrome-valid windows: 2,460/2,460;
- occupancy checks clear: 25,756/25,756;
- commit-residual failures: 0;
- final-residual failures: 0;
- final logical-frame failures: 0;
- maximum iterations: 24;
- total iterations: 14,951;
- forbidden runtime hits: 0;
- unexpected warnings: 0.

The formal capture exits zero after 236.54 seconds. This duration includes RTL elaboration, software control, selector service, and simulation; it is not decoder or FPGA latency.

## Open-loop comparison

All fifteen new shots are trajectory-equivalent to their earlier open-loop replay across defects, selector counts, complete correction vectors, and iteration counts. The previously accepted shot 15 remains the only trajectory divergence in the cumulative 0–24 prefix.

This is useful for two reasons:

1. the new harness reproduces the old path whenever no feedback-sensitive degeneracy occurs;
2. shot 15 demonstrates that the same harness follows the actual RTL trajectory when one does occur.

Thus the closed-loop route is both a replay calibration and a sequential-correctness test.

## Updated denominator

The cumulative frozen X denominator is now:

- 25/1,024 distinct shots;
- 4,100/167,936 cases;
- 999 shots and 163,836 cases remaining.

The rejected 127-shot open-loop block is still not counted. Only the fifteen newly closed-loop-accepted shots increase the denominator in this step.

## Claim boundary

This establishes a passing 25-shot X prefix under the closed-loop semantic gate. It does not establish full X, any Z result, AXI integration, FPGA timing/resources, measured hardware latency, `p99 <= 1 us`, miss `<= 1%`, full B2, scalable #023, or B7 resource credit.

Machine evidence ID: `7df273c2c43f56e0a22a16b6ad54cc3677f353dfc872b25cb4eee968399d50b4` (25/25 checks).
