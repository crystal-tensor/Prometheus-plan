# What does it mean to “fix” a failed replay without changing the decoder?

Our 127-shot open-loop RTL run was rejected because 21 valid corrections differed from the frozen software trajectory and could change the following window. We did not canonicalize the hardware or relax correctness. Instead, we replaced the invalid replay assumption with a closed-loop test that feeds each actual RTL correction into persistent detector state.

The accepted closed-loop prefix now reaches shot 127. All 21 mismatches from the rejected open-loop block have been exercised in their own state trajectories. In each case, the following window changes as expected, clears its commit residual, and the trajectory reconverges one window later. Across the new 64-shot shard, all 10,496 windows and 105,733 occupancy checks pass with zero final residual or logical-frame failures.

The heuristic question is: **when a verification method fails but the implementation may still be correct, what evidence is strong enough to repair the method without moving the goalposts?** Here the replacement gate is stricter about time: it no longer compares one isolated answer, but requires every committed state transition and the final logical frame to remain correct.

The accepted X denominator is now 128/1,024 shots and 20,992/167,936 cases. Full X is still false; Z, AXI, FPGA, `p99 <= 1 us`, miss `<= 1%`, full B2, scalable #023, and B7 resource credit remain open.

Evidence: `results/B2_B7_P023_d6_x_closed_loop_shard_0064_0127_evidence_v1.json`
Evidence ID: `773f72ac9b73a90f07ab46966a9eb7c3cbbe77f42873b0d2b6d9bb0281a6a50d`
