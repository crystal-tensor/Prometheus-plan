# If every phase is correct alone, what does it cost to make them coexist?

The resident causal-selector route now passes more than the steady graph. We reopened the accepted X/Z corpus from the exact frozen seeds, executed the complete 164-window chain for every shot, and froze opening/closing zero, p50, p99, and maximum batches with zero new stochastic samples.

Four full-scale RTL images were then generated and replayed independently:

- X opening: 2,901 edges and 15,072 active rules;
- X closing: 3,730 edges and 19,306 active rules;
- Z opening: 2,896 edges and 15,062 active rules;
- Z closing: 3,725 edges and 19,296 active rules.

All 16 phase-boundary batches pass, and all 53,008 edge-state comparisons agree. Representative p99 AXI selector spans are 20/28 slow cycles for X opening/closing and 28/24 for Z. Across all 4,096 accepted opening/closing batches, the selected-source distributions project to 26/30 and 26/32 update-only cycles.

But this creates the next architectural problem: each phase is correct as a separate RTL image, while the graph topology itself changes. A rule-bank selector cannot by itself turn a 2,901-edge opening graph into a 3,730-edge closing graph.

Which integration route would you test first?

1. Build a superset graph and phase-mask inactive vertices, edges, and rule banks.
2. Keep separate opening/steady/closing engines and pay replication or time-multiplexing cost.
3. Use a smaller reconfiguration layer that rewires only the phase-dependent boundary structure.

What invariant would you require so that a superset or masked graph cannot introduce a false tight edge or conflict?

This result does not yet implement runtime phase switching, replay all accepted batches in RTL, compare complete corrections, or measure FPGA Fmax/LUT/BRAM. The end-to-end p99 `<=1 us`, miss `<=1%`, full B2, scalable #023, and B7 resource gates remain closed.
