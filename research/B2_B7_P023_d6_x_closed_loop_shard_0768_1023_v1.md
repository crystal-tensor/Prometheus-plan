# Closed-loop X RTL: full frozen corpus

Date: 2026-11-21
Scope: #021/B7, #022/B2, #023 only

## Question

What does a completely clean frozen denominator prove—and what does it still refuse to say?

## Final frozen shard

The seventh closed-loop extension freezes shots 768–1023, adding the final 256 X shots and 41,984 consecutive windows. Combined with prior accepted evidence, the closed-loop set is exactly shots 0–1023: the complete frozen X corpus.

None of the final shots overlaps the rejected open-loop capture. Acceptance comes only from the unchanged closed-loop semantic gate.

## Formal result

The pinned Verilator 5.040 capture passes:

- frozen shots: 256/256;
- complete windows: 41,984/41,984;
- syndrome-valid windows: 41,984/41,984;
- occupancy checks clear: 424,577/424,577;
- commit-residual failures: 0;
- final-residual failures: 0;
- final logical-frame failures: 0;
- maximum iterations: 25;
- total iterations: 247,519;
- forbidden runtime hits: 0;
- unexpected warnings: 0.

The formal capture exits zero after 1,405.71 seconds. This is host-plus-simulator elapsed time, not measured hardware latency.

## Independent audit

The audit binds the exact shot range, pilot, v9 patch, selector service, raw result, capture metadata, and forced runtime log. It verifies every case row, every per-shot 164-window cardinality, the full occupancy total, the pinned simulator version, and the inherited 21/21 response coverage for the known open-loop mismatches.

The final set is disjoint from shots 0–767, and their union is exactly all 1,024 X shots.

## Completed denominator

The cumulative frozen X denominator is now:

- 1,024/1,024 distinct shots;
- 167,936/167,936 cases;
- exactly 100% of the X corpus;
- 0 shots and 0 cases remaining.

All 21 mismatches from the rejected open-loop trial are covered by accepted closed-loop responses. The rejected open-loop block itself is not counted.

## Claim boundary

This establishes full X for the frozen closed-loop RTL corpus and its declared semantic contract. It does not establish any Z result, AXI integration, FPGA timing/resources, measured hardware latency, `p99 <= 1 us`, miss `<= 1%`, full B2, scalable #023, or B7 resource credit.

Machine evidence ID: `448502f4f5076a055629de56622788775ee7474085069d1d4f2efdaea1573834` (27/27 checks).
