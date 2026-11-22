# Both X and Z are complete—what should try to break the decoder next?

The unchanged stateful RTL route has now completed both frozen denominators. Z reaches shots 0–1,023: 1,024/1,024 trajectories and 167,936/167,936 opening, steady, and closing windows. The already completed X denominator has the same shot and window cardinality.

The final Z quarter adds 41,984 cases. Every syndrome is valid; all 427,693 occupancy checks clear; commit residual, final residual, and final logical-frame failures remain zero. Across the final shard, the maximum is 27 solver iterations. The corpus, generated RTL, patch, selector service, feedback rule, and semantic gate did not change.

The heuristic question is: **once both basis denominators are complete, what experiment most honestly tries to turn decoder evidence into system evidence—or falsify that transition?** More same-contract shots may improve statistics, but they no longer attack the largest open boundaries.

Should the next gate prioritize AXI backpressure and ordering, FPGA timing/resource closure, an independent corpus seed, or measured tail latency? Which failure would teach us the most about whether the clean semantic route survives real integration?

`full_x=true` and `full_z=true` now hold for the declared frozen corpora. AXI, FPGA timing/resources, measured `p99 <= 1 us`, miss `<= 1%`, full B2, scalable #023, and B7 resource credit remain open. Host capture duration is reproducibility metadata, not hardware latency. The 120-qubit / depth-7,000 capacity question is outside this acceptance design.
