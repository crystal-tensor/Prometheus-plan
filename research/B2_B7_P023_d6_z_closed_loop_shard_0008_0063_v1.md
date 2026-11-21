# When Z reaches 6.25%, are we testing scale—or merely repeating luck?

Date: 2026-11-21  
Scope: #021/B7, #022/B2, #023 only

## Question

The first eight Z shots established that the route could execute. Does the same stateful semantic gate survive a substantially larger contiguous prefix without changing the corpus, graph, selector, or acceptance rule?

## Frozen shard

The second Z shard was fixed before execution:

- new shots: 8–63, 56 distinct trajectories;
- complete windows per shot: 164;
- new cases: 9,184;
- input evidence ID: `94e7de859217cf61c38ffef49898d77bf44db5d8c1bca311bbc20c2510214064`;
- accepted Z corpus SHA-256: `b4ac832c043de211d28a77d5db817d15c6ff3db886af0f0ab3092984d42811cf`.

The run uses the same self-contained Micro Blossom patch, generated `DistributedDual` RTL, Verilator 5.040 backend, persistent selector service, and closed-loop state feedback as shots 0–7. No threshold or semantic contract changed.

## Result

All new trajectories pass:

- shots: 56/56;
- windows: 9,184/9,184;
- syndrome-valid windows: 9,184/9,184;
- occupancy checks clear: 93,512/93,512;
- commit-residual failures: 0;
- final-residual failures: 0;
- final-frame failures: 0;
- maximum iterations: 21;
- total iterations: 54,502;
- forbidden runtime errors: 0;
- unexpected warnings: 0.

The capture exits zero after 491.264955 host seconds. This is reproducibility metadata, not hardware latency. The cumulative evidence audit passes 31/31 checks with evidence ID `bca87657d09ef5c22990f4ed4bffd2d5843b23b3546d9656edf22dfb4157899c`.

## Cumulative denominator

Combining the non-overlapping first and second shards gives a contiguous Z prefix:

- accepted shots: 0–63, or 64/1,024;
- accepted cases: 10,496/167,936;
- tested fraction: 6.25%;
- remaining shots: 960;
- remaining cases: 157,440.

`full_x=true` remains supported. `full_z=false` remains binding.

## Claim boundary

This result expands the executed Z denominator. It does not establish AXI integration, FPGA timing/resources, measured hardware latency, `p99 <= 1 us`, miss `<= 1%`, full B2, scalable #023, or B7 resource credit. The 120-qubit / depth-7,000 capacity question is not part of this acceptance design.

## Next falsifier

Continue from shot 64 under the identical frozen route. The next useful result is a larger non-overlapping Z prefix or a preserved counterexample—not an extrapolation from 6.25%.
