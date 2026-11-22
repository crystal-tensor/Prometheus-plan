# When both X and Z denominators are complete, what still prevents a decoder claim from becoming a system claim?

Date: 2026-11-22  
Scope: #021/B7, #022/B2, #023 only

## Question

Does the unchanged stateful RTL route close the final frozen Z quarter without hidden occupancy, closing residuals, or logical-frame drift—and if it does, which claim boundaries remain untouched?

## Frozen final shard

The seventh and final Z shard was fixed before execution:

- new shots: 768–1,023, 256 distinct trajectories;
- complete windows per shot: 164;
- new cases: 41,984;
- input evidence ID: `b166f74a5fd093acb2db275f5e7e04ad69a9fbffc077851ec0e8b068e8523a16`;
- accepted Z corpus SHA-256: `b4ac832c043de211d28a77d5db817d15c6ff3db886af0f0ab3092984d42811cf`.

The self-contained Micro Blossom patch, generated `DistributedDual` RTL, Verilator 5.040 backend, persistent selector service, closed-loop state feedback, and acceptance contract are unchanged from shots 0–767.

## Final-shard result

All final trajectories pass:

- shots: 256/256;
- windows: 41,984/41,984;
- syndrome-valid windows: 41,984/41,984;
- occupancy checks clear: 427,693/427,693;
- commit-residual failures: 0;
- final-residual failures: 0;
- final-frame failures: 0;
- maximum iterations: 27;
- total iterations: 249,172;
- forbidden runtime errors: 0;
- unexpected warnings: 0.

The capture exits zero after 1,669.751987 host seconds. This is reproducibility metadata, not hardware latency. The full-denominator evidence audit passes 31/31 checks with evidence ID `2b45cb80b09b19cc1b0378cdea60f7014e6e1c580285f6f67596a3fd9524a2c9`.

## Complete Z denominator

Combining seven non-overlapping shards gives the complete frozen Z corpus:

- accepted shots: 0–1,023, or 1,024/1,024;
- accepted cases: 167,936/167,936;
- tested fraction: 100%;
- remaining shots: 0;
- remaining cases: 0.

`full_x=true` and `full_z=true` are now both supported for their declared frozen corpora and closed-loop RTL contract.

## Claim boundary

Complete X and Z establish the declared decoder semantic route across both frozen denominators. They do not establish AXI integration, FPGA timing/resources, measured hardware latency, `p99 <= 1 us`, miss `<= 1%`, full B2, scalable #023, or B7 resource credit. Those remain separately gated. The 120-qubit / depth-7,000 capacity question remains outside this acceptance design.

## Next falsifier

Preserve full X/Z as immutable decoder evidence and move to a separately bound integration falsifier. The next useful target is not another claim about corpus coverage; it is an executable AXI/backpressure boundary that can fail without rewriting the completed denominator.
