# If a decoder clears the first quarter of Z, where should we search for the counterexample?

The unchanged stateful RTL route now passes a contiguous Z prefix of shots 0–255: 256/1,024 trajectories and 41,984/167,936 opening, steady, and closing windows.

The newest 128-shot shard adds 20,992 cases. Every syndrome is valid; all 214,463 occupancy checks clear; commit residual, final residual, and final logical-frame failures remain zero. The maximum rises to 29 solver iterations, but the semantic gate remains unchanged and passes every case.

The heuristic question is: **when ordinary state accumulation has survived a clean quarter, how should we spend the remaining test budget to maximize the chance of falsification?** Sequential coverage protects the frozen denominator from cherry-picking. Targeted pressure—high defect density, occupancy, iteration count, temporal clustering—might find a rarer weakness sooner, but can also distort what the denominator means.

Would you continue strictly sequentially, add a separately labeled adversarial stratum, or do both? What property should define that stratum without leaking the expected answer?

Full Z, AXI, FPGA timing/resources, measured `p99 <= 1 us`, miss `<= 1%`, full B2, scalable #023, and B7 resource credit remain open. Host capture duration is reproducibility metadata, not hardware latency. The 120-qubit / depth-7,000 capacity question is outside this acceptance design.
