# At 12.5% Z coverage, what kind of late counterexample could still defeat the route?

Date: 2026-11-21  
Scope: #021/B7, #022/B2, #023 only

## Question

After a clean 64-shot prefix, does doubling the contiguous denominator expose state accumulation, closing-window residue, or logical-frame drift under the same frozen semantic contract?

## Frozen shard

The third Z shard was fixed before execution:

- new shots: 64–127, 64 distinct trajectories;
- complete windows per shot: 164;
- new cases: 10,496;
- input evidence ID: `a2aa4e5524bf2a65f1fe07dc380284e5c140fad6240e41a47161ff8ea1605e4e`;
- accepted Z corpus SHA-256: `b4ac832c043de211d28a77d5db817d15c6ff3db886af0f0ab3092984d42811cf`.

The run preserves the same self-contained Micro Blossom patch, generated `DistributedDual` RTL, Verilator 5.040 backend, persistent selector service, and closed-loop state feedback used for shots 0–63. The interrupted first attempt produced no result and counted nothing; the authoritative replay used the exact frozen shots without changing the gate or input.

## Result

All new trajectories pass:

- shots: 64/64;
- windows: 10,496/10,496;
- syndrome-valid windows: 10,496/10,496;
- occupancy checks clear: 106,317/106,317;
- commit-residual failures: 0;
- final-residual failures: 0;
- final-frame failures: 0;
- maximum iterations: 24;
- total iterations: 62,245;
- forbidden runtime errors: 0;
- unexpected warnings: 0.

The capture exits zero after 440.176464 host seconds. This is reproducibility metadata, not hardware latency. The cumulative evidence audit passes 31/31 checks with evidence ID `3f82f2df89bcff8d3b0068244492e936608d5167c1345deded8b828a052f760a`.

## Cumulative denominator

Combining three non-overlapping shards gives a contiguous Z prefix:

- accepted shots: 0–127, or 128/1,024;
- accepted cases: 20,992/167,936;
- tested fraction: 12.5%;
- remaining shots: 896;
- remaining cases: 146,944.

`full_x=true` remains supported. `full_z=false` remains binding.

## Claim boundary

This result expands the executed Z denominator. It does not establish AXI integration, FPGA timing/resources, measured hardware latency, `p99 <= 1 us`, miss `<= 1%`, full B2, scalable #023, or B7 resource credit. The 120-qubit / depth-7,000 capacity question is outside this acceptance design and is not an acceptance gate.

## Next falsifier

Continue from shot 128 under the identical frozen route. A late counterexample should be preserved and diagnosed; a clean continuation should count only as additional denominator coverage, not as deployment evidence.
