# X-corpus long replay falsifier: look-ahead correction divergence

Date: 2026-11-21  
Scope: #021/B7, #022/B2, #023 only

## Question

If two matchings correct the same syndrome and preserve the same logical frame, may a streaming decoder treat their detector corrections as interchangeable?

## Frozen trial

- Basis: X only.
- Shot interval: 9–135 inclusive, 127 frozen shots.
- Cases: 20,828 consecutive opening, steady, and closing windows.
- Defect/occupancy checks: 210,748.
- Corpus, phase banks, selectors, expected corrections, simulator version, source patch, and acceptance rule were unchanged.
- Backend: Verilator 5.040 on pinned Micro Blossom commit `a3530d9e58ff790dafc93d56c9a2769ceac84731`.

## Result: rejected

The run completed every case, but the exact-correction gate failed:

- syndrome-valid cases: 20,828/20,828;
- occupancy checks clear: 210,748/210,748;
- exact correction mismatches: 21;
- logical observable mismatches: 0;
- process exit: 101, caused by the intended correction assertion;
- accepted-X denominator remains 9/1,024 shots and 1,476/167,936 cases.

The 127-shot block is not counted as correctness progress.

## First counterexample

The first divergence occurs at shot 15, window 59. Expected and actual correction vectors differ at local detector-correction bits 222 and 227. They map to global detectors 12,595 and 12,600. Both detectors:

- arrived in window 58;
- participate in detection windows 58–60;
- are committed in window 60.

The actual subgraph still reproduces the requested syndrome and leaves the logical observable bit unchanged. Nevertheless, the correction delta is part of persistent state and becomes committed one window later.

## Structural diagnosis

Across all 21 mismatched cases:

- 41 unique detector bits diverge;
- every delta is in the detector portion, never the observable portion;
- every divergent detector belongs to the three-window overlap;
- every divergent detector is committed in the immediately following window.

Therefore the difference is neither an unused padding bit nor a harmless output-format choice. It is a matching degeneracy that changes the state presented to a later window.

## What the falsifier invalidates

The present shard freezes each window's defect set from the accepted software trajectory. That is sufficient only while RTL returns the same correction trajectory. Once the first valid-but-different correction appears, replaying the next precomputed defect set is open-loop: it no longer represents the state that the RTL path would create.

Consequently:

- syndrome validity alone is too weak;
- logical-frame equality alone is too weak;
- exact equality against one degenerate software matching is too restrictive as a per-window semantic rule;
- yet relaxing exact equality without propagating the actual correction would be unsound.

## Correct next gate

Build a closed-loop RTL harness. For every window it must:

1. load new raw detector arrivals;
2. derive the syndrome from the persistent correction state actually returned by RTL;
3. derive the selector set for that actual syndrome;
4. run the phase-aware primal/dual path;
5. apply the returned correction before constructing the next window;
6. enforce zero committed residual and the correct final logical frame.

The original frozen corpus, X/Z separation, correctness veto, and hardware acceptance thresholds remain unchanged.

## Claim boundary

This is a rejected long replay and a validated test-design correction. It is not full X, Z, AXI, FPGA, hardware-latency, `p99 <= 1 us`, miss `<= 1%`, full B2, scalable #023, or B7 resource evidence.

Machine evidence ID: `8e7c0a3fc7edbd1497ad534ee3ac993af49ead319bea8e7573628cace0043948` (18/18 checks).
