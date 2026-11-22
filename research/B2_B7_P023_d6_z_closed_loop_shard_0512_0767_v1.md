# At 75% Z coverage, is the final quarter routine—or the only quarter that still matters?

Date: 2026-11-22  
Scope: #021/B7, #022/B2, #023 only

## Question

Can the unchanged stateful RTL route extend from a clean half to three quarters of the frozen Z corpus without hidden occupancy, closing residuals, or logical-frame drift?

## Frozen shard

The sixth Z shard was fixed before execution:

- new shots: 512–767, 256 distinct trajectories;
- complete windows per shot: 164;
- new cases: 41,984;
- input evidence ID: `0beb404d99644e38dff28fd1a0ecd35e99244aae9eb3cf623d39f380b9f73df1`;
- accepted Z corpus SHA-256: `b4ac832c043de211d28a77d5db817d15c6ff3db886af0f0ab3092984d42811cf`.

The self-contained Micro Blossom patch, generated `DistributedDual` RTL, Verilator 5.040 backend, persistent selector service, closed-loop state feedback, and acceptance contract are unchanged from shots 0–511.

## Result

All new trajectories pass:

- shots: 256/256;
- windows: 41,984/41,984;
- syndrome-valid windows: 41,984/41,984;
- occupancy checks clear: 427,264/427,264;
- commit-residual failures: 0;
- final-residual failures: 0;
- final-frame failures: 0;
- maximum iterations: 25;
- total iterations: 249,444;
- forbidden runtime errors: 0;
- unexpected warnings: 0.

The capture exits zero after 1,814.576683 host seconds. This is reproducibility metadata, not hardware latency. The cumulative evidence audit passes 31/31 checks with evidence ID `a4991fdf12f7943613b4495742f0a392ceffa2179545554b1d15d2a2f19c126a`.

## Cumulative denominator

Combining six non-overlapping shards gives a contiguous Z prefix:

- accepted shots: 0–767, or 768/1,024;
- accepted cases: 125,952/167,936;
- tested fraction: 75%;
- remaining shots: 256;
- remaining cases: 41,984.

`full_x=true` remains supported. `full_z=false` remains binding.

## Claim boundary

This result establishes a clean executed three quarters of the frozen Z denominator. It does not establish AXI integration, FPGA timing/resources, measured hardware latency, `p99 <= 1 us`, miss `<= 1%`, full B2, scalable #023, or B7 resource credit. The 120-qubit / depth-7,000 capacity question remains outside this acceptance design.

## Next falsifier

Continue the final frozen quarter from shot 768 under the identical route. A clean 75% prefix strengthens implementation evidence, but it cannot convert the unexecuted final quarter into full Z.
