# At 25% Z coverage, does a clean quarter reveal robustness—or only a larger denominator?

Date: 2026-11-21  
Scope: #021/B7, #022/B2, #023 only

## Question

Can the unchanged stateful RTL route double its contiguous Z coverage again—through a quarter of the frozen corpus—without hiding state, leaving a closing residual, or drifting from the expected logical frame?

## Frozen shard

The fourth Z shard was fixed before execution:

- new shots: 128–255, 128 distinct trajectories;
- complete windows per shot: 164;
- new cases: 20,992;
- input evidence ID: `f3e256170c580687e33958fac17215e3637e85abe30d09360b64f239de1c0320`;
- accepted Z corpus SHA-256: `b4ac832c043de211d28a77d5db817d15c6ff3db886af0f0ab3092984d42811cf`.

The self-contained Micro Blossom patch, generated `DistributedDual` RTL, Verilator 5.040 backend, persistent selector service, and closed-loop state feedback are unchanged from shots 0–127. No acceptance threshold or semantic rule changed.

## Result

All new trajectories pass:

- shots: 128/128;
- windows: 20,992/20,992;
- syndrome-valid windows: 20,992/20,992;
- occupancy checks clear: 214,463/214,463;
- commit-residual failures: 0;
- final-residual failures: 0;
- final-frame failures: 0;
- maximum iterations: 29;
- total iterations: 125,379;
- forbidden runtime errors: 0;
- unexpected warnings: 0.

The capture exits zero after 1,001.782674 host seconds. This is reproducibility metadata, not hardware latency. The cumulative evidence audit passes 31/31 checks with evidence ID `c1f67303a1724e7227e55f580c084095069183ebfd5f8e4ce8c8c74a14a016f5`.

## Cumulative denominator

Combining four non-overlapping shards gives a contiguous Z prefix:

- accepted shots: 0–255, or 256/1,024;
- accepted cases: 41,984/167,936;
- tested fraction: 25%;
- remaining shots: 768;
- remaining cases: 125,952.

`full_x=true` remains supported. `full_z=false` remains binding.

## Claim boundary

This result establishes a clean executed quarter of the frozen Z denominator. It does not establish AXI integration, FPGA timing/resources, measured hardware latency, `p99 <= 1 us`, miss `<= 1%`, full B2, scalable #023, or B7 resource credit. The 120-qubit / depth-7,000 capacity question is outside this acceptance design and is not an acceptance gate.

## Next falsifier

Continue from shot 256 under the identical frozen route. The remaining three quarters must be executed or falsified; they cannot be inferred from the clean first quarter.
