# Does full X generalize to Z—or must Z earn its own denominator?

Date: 2026-11-21  
Scope: #021/B7, #022/B2, #023 only

## Question

After all 1,024 frozen X shots passed the closed-loop RTL gate, can that result be transferred to the Z basis, or does the different graph, fault map, and corpus require an independent execution?

## Frozen Z route

The first Z shard uses the already accepted 1,024-shot Z corpus:

- corpus SHA-256: `b4ac832c043de211d28a77d5db817d15c6ff3db886af0f0ab3092984d42811cf`;
- seed: `8540768509709157704`;
- superset graph: 1,142 vertices and 3,756 edges;
- opening/steady/closing active edges: 2,896 / 2,973 / 3,725;
- complete windows per shot: 164;
- frozen first shard: shots 0–7.

The route keeps one persistent generated-RTL `DistributedDual` instance and one persistent hash-bound selector service. Each returned correction is fed into the next window's detector state. The semantic gate is unchanged: every syndrome must be valid, every committed detector set must clear, the final detector residual must be zero, and the final logical frame must match.

## Self-contained patch falsifier

The first clean-source replay exposed a reproducibility defect before any Z case executed: the patch used `LoadWeightsExternal` but did not carry the corresponding `Instruction.scala` helpers. This was not counted as a scientific failure or hidden as a successful run. The missing instruction methods were added to the patch, which then applied cleanly to pinned Micro Blossom commit `a3530d9e58ff790dafc93d56c9a2769ceac84731` and passed a Java-17 `sbt compile` from a fresh checkout.

The accepted run uses the corrected self-contained patch with SHA-256 `a1b1b4a2036f44039f6448d16a357ea07d1105c272644e805e9f8ebc7c5b5b27` and Verilator 5.040. Host compile and capture time are reproducibility metadata, not FPGA latency.

## Result

The bounded Z shard passes:

- shots: 8/8;
- complete windows: 1,312/1,312;
- syndrome-valid windows: 1,312/1,312;
- occupancy checks clear: 13,498/13,498;
- commit-residual failures: 0;
- final-residual failures: 0;
- final-frame failures: 0;
- maximum iterations: 23;
- total iterations: 7,907;
- forbidden runtime errors: 0;
- unexpected warnings: 0.

The independent evidence audit passes 28/28 checks. Evidence ID: `016fcda68094d8c4368bc36f9b991bd295d8288f84f3a366539f4751a0de0077`.

## Denominator and claim boundary

This establishes the first accepted Z prefix:

- accepted: 8/1,024 shots and 1,312/167,936 cases;
- remaining: 1,016 shots and 166,624 cases;
- `full_x=true` remains supported;
- `full_z=false` remains binding.

The result does not establish AXI integration, FPGA timing/resources, measured hardware latency, `p99 <= 1 us`, miss `<= 1%`, full B2, scalable #023, or B7 resource credit. The 120-qubit / depth-7,000 capacity question is explicitly excluded from this acceptance design and remains exploratory.

## Next falsifier

Continue the same frozen Z corpus from shot 8 without changing the corpus, graph/rule bindings, closed-loop feedback, or residual gate. A clean eight-shot prefix is evidence that the route is executable; it is not permission to extrapolate the remaining 99.21875% of the Z denominator.
