# B2/B7/#023 X full-corpus shot 0000 real-RTL calibration v1

As of 2026-11-21. Scope is exactly #021/B7, #022/B2, and #023.

## Research question

Can the accepted phase-aware Rust-primal plus real SpinalHDL `DistributedDual` path execute one complete frozen X shot—all 164 opening, steady, and closing windows—without using representative-window sampling, and what software-simulation cost does that imply for the full 1,024-shot denominator?

## Frozen denominator

The accepted X corpus remains unchanged:

- corpus SHA-256: `86185652355a9197eabc0503945820837dbf497ff822812f37f47a0e26836e89`;
- accepted prediction SHA-256: `3c9e23b747a0527ad15a042954a1cf7a6c1be31501450c7c3e0b1366360e1331`;
- 1,024 shots × 164 windows = 167,936 decode cases;
- window 0 is opening, windows 1–162 are steady, and window 163 is closing.

The shard generator reopens that corpus from its fixed seed, verifies both accepted hashes plus the graph/rule sequence hashes, and then reconstructs the sequential received/correction state. Shot 0 produces a 164-case shard with evidence ID `b5dbc56a20c31c7d82240f99aad31c43d760fe9f8639fc74f72d65a1f0c96c02`.

## Accepted real-RTL result

| Gate | Result |
|---|---:|
| Complete frozen shots tested | 1/1,024 |
| Sequential windows | 164/164 |
| Opening / steady / closing | 1 / 162 / 1 |
| Syndrome checks | 164/164 pass |
| Complete correction checks | 164/164 exact |
| AddDefect occupancy checks | 1,648/1,648 clear |
| Causal selectors | 918 |
| Total resolved obstacles | 946 |
| Maximum resolved obstacles in one window | 15 |
| Capture exit code | 0 |
| Forbidden errors | 0 |
| Unexpected warnings | 0 |
| Independent evidence audit | 40/40 pass |

The result accepts any matching subgraph whose syndrome and complete correction are correct. It deliberately does not require equality with one chosen reference edge set because multiple matching subgraphs can represent the same valid correction.

The captured evidence ID is `a7e512f7210af72eecf3f96224eaa2c94d5fc22160fcd2ed41d81b6dc8014304`. The exact 14-file patch SHA-256 is `e943b2fea3d13bdae01f6649b7eebfabeef2033057f22b2adbbe612af162645b`; it applies cleanly to pinned Micro Blossom commit `a3530d9e58ff790dafc93d56c9a2769ceac84731`.

## Simulator calibration

The formal Icarus capture takes 658.652475 seconds end to end, or 4.016174 seconds per case including Scala startup, RTL elaboration, and compilation. The simulator reports 439.699413 seconds for the simulation body, or 2.681094 seconds per case.

These measurements imply two deliberately rough bounds:

- repeating 1,024 independent one-shot captures would take about 187.35 hours;
- one persistent simulator with the same shot-0 body rate would take about 125.07 hours.

Neither projection is an acceptance result. Workload complexity varies across shots, parallel contention is not measured, and software-simulator runtime is not hardware latency.

## Rejected acceleration attempt

A bounded Verilator experiment was not accepted. The first attempt stopped because 2,294 `UNOPTPUBLIC` warnings were fatal. After suppressing only that warning class and overriding SpinalHDL 1.9.3's C++11 flag with C++14, compilation reached a second incompatibility: SpinalHDL's generated wrapper expects the older `WData*` ABI, while local Verilator 5.054 exposes `VlWide`/`WDataOutP` types.

No Verilator correctness or speed claim is made. The experimental backend switch was removed from the accepted source patch.

## Claim boundary

This result closes the first complete-shot X real-RTL calibration only—`164/167,936`, or exactly `1/1,024` of the frozen X denominator. It does not close:

- the remaining 1,023 X shots;
- independent Z phase banks and end-to-end correction;
- AXI phase control and correction readout;
- FPGA synthesis, Fmax, LUT/BRAM, routing, or measured hardware latency;
- p99 `<= 1 us` per committed layer or miss rate `<= 1%`;
- full B2, scalable #023, or any B7 resource credit.

## Next falsifier

Either establish a replay-equivalent fast backend by pinning a Verilator version compatible with SpinalHDL 1.9.3 or adapting the generated wide-signal wrapper, or execute audited Icarus shards in parallel. In either route, every case must remain bound to the same corpus and prediction hashes, and full-X credit stays false until all 167,936 cases pass.
