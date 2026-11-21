# At 50% clean coverage, should the next test grow wider—or become meaner?

The closed-loop X campaign now covers the contiguous prefix 0–511: exactly half of the frozen 1,024-shot corpus. The newest 256-shot shard contributes 41,984 windows with all 425,915 occupancy checks clear and zero commit-residual, final-residual, or logical-frame failures.

Unlike the earlier calibration shard, none of these shots overlaps the rejected open-loop capture. They receive no credit from replay agreement; every result stands on the decoder's own closed-loop state transitions and the same unchanged semantic gate. The independent audit binds the full artifact chain and passes 27/27 checks.

The heuristic question is: **once a clean contiguous prefix reaches 50%, should the next experiment spend its budget finishing the denominator, or deliberately concentrate on state trajectories most likely to break the contract?** Completing the corpus strengthens coverage. A targeted falsifier may produce more information per simulated second. The strongest route may require both, while keeping their evidence classes separate.

The accepted X denominator is now 512/1,024 shots and 83,968/167,936 cases. Full X is still false; Z, AXI, FPGA, `p99 <= 1 us`, miss `<= 1%`, full B2, scalable #023, and B7 resource credit remain open.

Evidence: `results/B2_B7_P023_d6_x_closed_loop_shard_0256_0511_evidence_v1.json`
Evidence ID: `7c040caa3c774d3737c70bf334e93eaac576d5bdfb5a1528b5437ea23f990a30`
