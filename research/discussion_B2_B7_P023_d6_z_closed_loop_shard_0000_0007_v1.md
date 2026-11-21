# If one Pauli basis passes completely, what would justify trusting the other one?

The X campaign now has a clean 1,024-shot denominator, but we refused to transfer that confidence to Z. The Z route has a different frozen corpus, graph occupancy, fault map, and logical trajectory, so it has started from shot 0 under the same closed-loop semantic contract.

The first Z prefix executes 8 complete shots and 1,312 consecutive opening/steady/closing windows through generated RTL. All 1,312 syndromes are valid, all 13,498 occupancy checks clear, and commit residual, final residual, and final logical-frame failures are all zero. The maximum solver depth is 23 iterations.

The run also found a useful reproducibility falsifier before the science began: the first patch replay was not self-contained because it omitted the instruction helpers for the external-weight opcode. After binding that missing dependency into the patch, a fresh checkout compiled and the complete Z shard passed. This is why “the code worked in yesterday's source tree” is not enough evidence.

The heuristic question is: **when X and Z share a decoder architecture but not an executed denominator, what evidence—if any—should transfer across bases?** Architectural reuse argues for a shared implementation. Error-correction semantics argue that each basis still has to survive its own stateful trajectories.

We currently count only 8/1,024 Z shots and 1,312/167,936 Z cases. Full Z, AXI, FPGA timing/resources, measured `p99 <= 1 us`, miss `<= 1%`, full B2, scalable #023, and B7 resource credit remain open. The 120-qubit / depth-7,000 question is exploratory and is not part of this acceptance design.
