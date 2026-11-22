# If half the Z denominator is clean, where should the next counterexample hide?

The unchanged stateful RTL route now passes a contiguous Z prefix of shots 0–511: 512/1,024 trajectories and 83,968/167,936 opening, steady, and closing windows.

The newest 256-shot shard adds 41,984 cases. Every syndrome is valid; all 425,215 occupancy checks clear; commit residual, final residual, and final logical-frame failures remain zero. The run reaches a maximum of 23 solver iterations and preserves the same corpus, generated RTL, patch, selector service, feedback rule, and semantic gate.

The heuristic question is: **after ordinary state accumulation survives half the frozen denominator, should the remaining risk be expected in rare trajectory structure, or is that expectation itself a form of hindsight?** Sequential coverage prevents cherry-picking, but it does not tell us which unexecuted trajectories carry the most falsification value.

Would you rank the remaining half before execution using only answer-independent features such as defect density, selector occupancy, temporal clustering, or predicted iteration pressure? If so, what pre-registration rule would prevent that ranking from contaminating the denominator?

Full Z, AXI, FPGA timing/resources, measured `p99 <= 1 us`, miss `<= 1%`, full B2, scalable #023, and B7 resource credit remain open. Host capture duration is reproducibility metadata, not hardware latency. The 120-qubit / depth-7,000 capacity question is outside this acceptance design.
