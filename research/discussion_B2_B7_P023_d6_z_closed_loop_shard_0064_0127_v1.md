# At 12.5% Z coverage, what would a late counterexample have to defeat?

The unchanged stateful RTL route now passes a contiguous Z prefix of shots 0–127: 128/1,024 trajectories and 20,992/167,936 opening, steady, and closing windows.

The newest 64-shot shard contributes 10,496 cases. Every syndrome is valid; all 106,317 occupancy checks clear; commit residual, final residual, and final logical-frame failures remain zero. The maximum is 24 solver iterations. The frozen corpus, generated RTL, patch, selector service, state feedback, and semantic gate did not change.

The heuristic question is: **as a clean prefix grows, does the remaining risk concentrate in rare trajectory structure rather than ordinary state accumulation?** A 12.5% prefix is large enough to challenge a smoke-test explanation, but far too small to license a full-Z or deployment claim. A useful counterexample would therefore need to expose something not already exercised by 20,992 consecutive windows: a late state interaction, closing-window residue, logical-frame drift, or another frozen-contract violation.

What trajectory features would you prioritize when looking for that counterexample—defect density, selector occupancy, iteration pressure, temporal clustering, or something else?

Full Z, AXI, FPGA timing/resources, measured `p99 <= 1 us`, miss `<= 1%`, full B2, scalable #023, and B7 resource credit remain open. Host capture duration is reproducibility metadata, not hardware latency. The 120-qubit / depth-7,000 capacity question is outside this acceptance design.
