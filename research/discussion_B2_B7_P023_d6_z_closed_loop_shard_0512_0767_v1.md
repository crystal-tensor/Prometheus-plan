# At 75% clean Z coverage, is the final quarter routine—or the only quarter that matters?

The unchanged stateful RTL route now passes a contiguous Z prefix of shots 0–767: 768/1,024 trajectories and 125,952/167,936 opening, steady, and closing windows.

The newest 256-shot shard adds 41,984 cases. Every syndrome is valid; all 427,264 occupancy checks clear; commit residual, final residual, and final logical-frame failures remain zero. The run reaches a maximum of 25 solver iterations and preserves the same corpus, generated RTL, patch, selector service, feedback rule, and semantic gate.

The heuristic question is: **when only the final quarter remains, does its value come from statistical mass, from the possibility of a rare late trajectory, or from closing the logical meaning of `full_z`?** A 75% clean prefix is strong evidence against a smoke-test artifact. It is still categorically different from a complete frozen denominator.

If the final quarter also passes, what should be the next falsification target: a separately pre-registered adversarial stratum, an independent corpus seed, AXI backpressure, FPGA timing, or a mixed integration stress test? Which one most directly attacks the current claim boundary?

Full Z remains open until shots 768–1,023 execute. AXI, FPGA timing/resources, measured `p99 <= 1 us`, miss `<= 1%`, full B2, scalable #023, and B7 resource credit also remain open. Host capture duration is reproducibility metadata, not hardware latency. The 120-qubit / depth-7,000 capacity question is outside this acceptance design.
