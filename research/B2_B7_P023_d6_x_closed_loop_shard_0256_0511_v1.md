# Closed-loop X RTL: contiguous half-corpus prefix

Date: 2026-11-21
Scope: #021/B7, #022/B2, #023 only

## Question

When a contiguous closed-loop prefix reaches half of the frozen corpus without a failure, what should the next test optimize for: more confidence, or a more aggressive falsifier?

## Frozen shard

The fifth closed-loop extension freezes shots 256–511, adding 256 previously uncredited X shots and 41,984 consecutive windows. Combined with prior evidence, the accepted set is the contiguous prefix 0–511: exactly one half of the 1,024-shot X corpus.

None of the new shots overlaps the earlier open-loop capture. Acceptance therefore comes only from the frozen closed-loop semantic gate rather than replay equivalence with an old trajectory.

## Formal result

The pinned Verilator 5.040 capture passes:

- frozen shots: 256/256;
- complete windows: 41,984/41,984;
- syndrome-valid windows: 41,984/41,984;
- occupancy checks clear: 425,915/425,915;
- commit-residual failures: 0;
- final-residual failures: 0;
- final logical-frame failures: 0;
- maximum iterations: 23;
- total iterations: 248,603;
- forbidden runtime hits: 0;
- unexpected warnings: 0.

The formal capture exits zero after 1,407.50 seconds. This is host-plus-simulator elapsed time, not measured hardware latency.

## Independent audit

The audit binds the exact shot range, pilot, v9 patch, selector service, raw result, capture metadata, and forced runtime log. It verifies every case row, every per-shot 164-window cardinality, the full occupancy total, the pinned simulator version, and the inherited 21/21 response coverage for the known open-loop mismatches.

The new set is disjoint from shots 0–255, and their union is exactly the contiguous prefix 0–511.

## Updated denominator

The cumulative frozen X denominator is now:

- 512/1,024 distinct shots;
- 83,968/167,936 cases;
- exactly 50% of the X corpus;
- 512 shots and 83,968 cases remaining.

All 21 mismatches from the rejected open-loop trial remain covered by accepted closed-loop responses. The rejected open-loop block itself is still not counted.

## Claim boundary

This establishes a passing half-corpus X prefix. It does not establish full X, any Z result, AXI integration, FPGA timing/resources, measured hardware latency, `p99 <= 1 us`, miss `<= 1%`, full B2, scalable #023, or B7 resource credit.

Machine evidence ID: `7c040caa3c774d3737c70bf334e93eaac576d5bdfb5a1528b5437ea23f990a30` (27/27 checks).
