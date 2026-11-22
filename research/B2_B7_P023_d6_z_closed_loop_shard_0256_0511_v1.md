# When half of Z is clean, what evidence would still distinguish robustness from a lucky prefix?

Date: 2026-11-22  
Scope: #021/B7, #022/B2, #023 only

## Question

Can the unchanged stateful RTL route extend from a clean quarter to a contiguous half of the frozen Z corpus without hidden occupancy, closing residuals, or logical-frame drift?

## Frozen shard

The fifth Z shard was fixed before execution:

- new shots: 256–511, 256 distinct trajectories;
- complete windows per shot: 164;
- new cases: 41,984;
- input evidence ID: `f2202a2da303af00d0c97e63d8a20c019ca8b86304f3f44ecf28aaac2111768d`;
- accepted Z corpus SHA-256: `b4ac832c043de211d28a77d5db817d15c6ff3db886af0f0ab3092984d42811cf`.

The self-contained Micro Blossom patch, generated `DistributedDual` RTL, Verilator 5.040 backend, persistent selector service, closed-loop state feedback, and acceptance contract are unchanged from shots 0–255.

## Result

All new trajectories pass:

- shots: 256/256;
- windows: 41,984/41,984;
- syndrome-valid windows: 41,984/41,984;
- occupancy checks clear: 425,215/425,215;
- commit-residual failures: 0;
- final-residual failures: 0;
- final-frame failures: 0;
- maximum iterations: 23;
- total iterations: 248,505;
- forbidden runtime errors: 0;
- unexpected warnings: 0.

The capture exits zero after 1,455.062042 host seconds. This is reproducibility metadata, not hardware latency. The cumulative evidence audit passes 31/31 checks with evidence ID `3aa1d323b39bb90000a26d571fc47b5a081e55701bdd1c9928a1d6abbacc1c4a`.

## Cumulative denominator

Combining five non-overlapping shards gives a contiguous Z prefix:

- accepted shots: 0–511, or 512/1,024;
- accepted cases: 83,968/167,936;
- tested fraction: 50%;
- remaining shots: 512;
- remaining cases: 83,968.

`full_x=true` remains supported. `full_z=false` remains binding.

## Claim boundary

This result establishes a clean executed half of the frozen Z denominator. It does not establish AXI integration, FPGA timing/resources, measured hardware latency, `p99 <= 1 us`, miss `<= 1%`, full B2, scalable #023, or B7 resource credit. The 120-qubit / depth-7,000 capacity question remains outside this acceptance design.

## Next falsifier

Continue from shot 512 under the identical frozen route. A clean first half is meaningful implementation evidence, but it cannot certify the unexecuted second half or any deployment property.
