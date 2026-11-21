# Closed-loop X RTL: contiguous quarter-corpus prefix

Date: 2026-11-21
Scope: #021/B7, #022/B2, #023 only

## Question

After closing every known replay divergence, does the same closed-loop contract remain stable on a large region with no preselected counterexamples?

## Frozen shard

The fourth closed-loop extension freezes shots 128–255, adding 128 previously uncredited X shots and 20,992 consecutive windows. Combined with prior evidence, the accepted set is the contiguous prefix 0–255: exactly one quarter of the 1,024-shot X corpus.

Shots 136–255 lie beyond the earlier open-loop replay capture. They therefore add new closed-loop coverage rather than reinterpreting old replay data.

## Formal result

The pinned Verilator 5.040 capture passes:

- frozen shots: 128/128;
- complete windows: 20,992/20,992;
- syndrome-valid windows: 20,992/20,992;
- occupancy checks clear: 211,437/211,437;
- commit-residual failures: 0;
- final-residual failures: 0;
- final logical-frame failures: 0;
- maximum iterations: 27;
- total iterations: 123,307;
- forbidden runtime hits: 0;
- unexpected warnings: 0.

The formal capture exits zero after 824.53 seconds. This is host-plus-simulator elapsed time, not measured hardware latency.

## Boundary calibration

Shots 128–135 overlap the tail of the earlier open-loop capture. Across all 1,312 overlapping windows, closed-loop and open-loop results are identical in defect count, selector count, complete correction, and iteration count.

This overlap supplies a boundary calibration before the campaign enters shots for which no open-loop trajectory exists. Acceptance beyond that boundary comes from the closed-loop semantic gate itself: valid syndrome, zero committed residual, zero final residual, and correct final logical frame.

## Updated denominator

The cumulative frozen X denominator is now:

- 256/1,024 distinct shots;
- 41,984/167,936 cases;
- exactly 25% of the X corpus;
- 768 shots and 125,952 cases remaining.

All 21 mismatches from the rejected open-loop trial remain covered by accepted closed-loop responses. The rejected open-loop block itself is still not counted.

## Claim boundary

This establishes a passing quarter-corpus X prefix. It does not establish full X, any Z result, AXI integration, FPGA timing/resources, measured hardware latency, `p99 <= 1 us`, miss `<= 1%`, full B2, scalable #023, or B7 resource credit.

Machine evidence ID: `20bbe7858afa18bcf5d3eb123b0756f7a2fa73f75fe808af4d3652f0fb21fa32` (27/27 checks).
