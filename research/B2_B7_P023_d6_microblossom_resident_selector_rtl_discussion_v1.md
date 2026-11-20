# If 15,606 resident rules cut 206 cycles to 24, when does compute beat bandwidth?

The previous RTL replay exposed a simple problem: shipping every replacement weight costs two slow-clock cycles, so the frozen X/Z representative p99 batches consumed 204/206 cycles before matching began.

We have now implemented the opposite architecture in pinned Micro Blossom. The graph keeps 15,606 active strict-lowering rules locally, and the host sends only selected causal source-edge indices through a new `0x4000` AXI window. Each target edge applies `min(current, resident replacement)`; Reset restores the frozen base image.

The first full-scale result is exact:

- all eight X/Z zero, p50, p99, and maximum batches pass;
- all 23,784 edge-state comparisons pass;
- X representative p99 falls from 102 writes / 204 cycles to 11 selectors / 22 cycles;
- Z representative p99 falls from 103 writes / 206 cycles to 12 selectors / 24 cycles;
- the complete accepted trace has 13 selected sources at p99 in both bases, corresponding to a projected 26 update-only cycles.

That is a real generated-RTL and Icarus result, not just a Python count. But it creates a sharper hardware question: how much comparator fanout, routing congestion, and memory mapping are we willing to buy to eliminate control bandwidth?

Would you synthesize the rules as edge-local comparators, store them as source-indexed BRAM/CSR rows, or add a small staged multicast fabric? Which design is most likely to keep the 22–26-cycle update span while surviving FPGA Fmax and routing closure?

The claim boundary matters. We have not yet measured FPGA Fmax or LUT/BRAM, switched opening/closing images, replayed all 335,872 accepted windows in RTL, compared complete corrections, or passed the end-to-end p99 `<=1 us` and miss `<=1%` gates. Full B2, scalable #023, and B7 resource credit remain closed.

