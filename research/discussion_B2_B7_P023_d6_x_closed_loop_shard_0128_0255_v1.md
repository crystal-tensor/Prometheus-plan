# When does a growing green prefix become evidence rather than reassurance?

The closed-loop X campaign now covers a contiguous 256-shot prefix—exactly 25% of the frozen corpus. The newest 128-shot shard contributes 20,992 windows beyond the known counterexample set, with all 211,437 occupancy checks clear and zero commit-residual, final-residual, or logical-frame failures.

The first eight shots overlap the tail of our earlier open-loop capture and reproduce its defects, selectors, complete corrections, and iterations exactly. The remaining 120 shots have no old trajectory to lean on: their acceptance comes directly from the decoder's own closed-loop state transitions.

The heuristic question is: **how should confidence grow when every tested sample passes but the denominator is still incomplete?** A contiguous prefix prevents cherry-picking and exposes long-run state behavior, yet 25% is not 100%. The honest value may be less “the decoder is correct” and more “the current falsifier has survived 41,984 consecutive windows without weakening its contract.”

The accepted X denominator is now 256/1,024 shots and 41,984/167,936 cases. Full X is still false; Z, AXI, FPGA, `p99 <= 1 us`, miss `<= 1%`, full B2, scalable #023, and B7 resource credit remain open.

Evidence: `results/B2_B7_P023_d6_x_closed_loop_shard_0128_0255_evidence_v1.json`
Evidence ID: `20bbe7858afa18bcf5d3eb123b0756f7a2fa73f75fe808af4d3652f0fb21fa32`
