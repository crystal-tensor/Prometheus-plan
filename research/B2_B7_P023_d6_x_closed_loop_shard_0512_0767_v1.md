# Closed-loop X RTL: contiguous three-quarter-corpus prefix

Date: 2026-11-21
Scope: #021/B7, #022/B2, #023 only

## Question

When only one quarter of a frozen corpus remains, is finishing the denominator still the strongest falsifier—or merely the most honest one?

## Frozen shard

The sixth closed-loop extension freezes shots 512–767, adding 256 previously uncredited X shots and 41,984 consecutive windows. Combined with prior evidence, the accepted set is the contiguous prefix 0–767: exactly three quarters of the 1,024-shot X corpus.

None of the new shots overlaps the earlier open-loop capture. Acceptance comes only from the unchanged closed-loop semantic gate rather than replay equivalence with an old trajectory.

## Formal result

The pinned Verilator 5.040 capture passes:

- frozen shots: 256/256;
- complete windows: 41,984/41,984;
- syndrome-valid windows: 41,984/41,984;
- occupancy checks clear: 420,058/420,058;
- commit-residual failures: 0;
- final-residual failures: 0;
- final logical-frame failures: 0;
- maximum iterations: 29;
- total iterations: 245,547;
- forbidden runtime hits: 0;
- unexpected warnings: 0.

The formal capture exits zero after 1,316.09 seconds. This is host-plus-simulator elapsed time, not measured hardware latency.

## Independent audit

The audit binds the exact shot range, pilot, v9 patch, selector service, raw result, capture metadata, and forced runtime log. It verifies every case row, every per-shot 164-window cardinality, the full occupancy total, the pinned simulator version, and the inherited 21/21 response coverage for the known open-loop mismatches.

The new set is disjoint from shots 0–511, and their union is exactly the contiguous prefix 0–767.

## Updated denominator

The cumulative frozen X denominator is now:

- 768/1,024 distinct shots;
- 125,952/167,936 cases;
- exactly 75% of the X corpus;
- 256 shots and 41,984 cases remaining.

All 21 mismatches from the rejected open-loop trial remain covered by accepted closed-loop responses. The rejected open-loop block itself is still not counted.

## Claim boundary

This establishes a passing three-quarter-corpus X prefix. It does not establish full X, any Z result, AXI integration, FPGA timing/resources, measured hardware latency, `p99 <= 1 us`, miss `<= 1%`, full B2, scalable #023, or B7 resource credit.

Machine evidence ID: `c8666bd770b2b7bdad6ebb9bcf872d5ccd4596cddbc28e10b8e923f2d41622a0` (27/27 checks).
