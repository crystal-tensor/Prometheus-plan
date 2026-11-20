# If correctness costs two cycles per edge, should the decoder stop shipping weights?

The accepted X/Z corpus has now been turned into a hardware-facing trace: 167,936 per-window batches per basis, each bound to its syndrome, selected causal edges, normalized replacement weights, prediction hash, and reset semantics. No new stochastic samples were opened.

The scale is revealing. X contains 6,362,111 update writes and Z contains 6,425,518. Their p99 batches contain 102 and 103 updates; the largest contain 170 and 179. An independent `108/108` audit reconstructs the representative batches directly from selected source edges and the frozen correlation rules.

Eight real zero/p50/p99/maximum batches were then replayed through the full 2,973-edge steady AXI4 RTL. Every batch passes, and all 23,784 edge-state checks agree after Reset plus writes.

But functional correctness exposes the next bottleneck: the current serial path takes exactly two slow-clock cycles per update. X/Z p99 therefore cost 204/206 cycles before the decoder does any matching. Fitting only those writes into one microsecond requires at least a 204/206 MHz slow clock, with no time left for Reset, syndrome transfer, decoding, or correction output.

Heuristic question: should the next design widen the bus, cache the three rule images beside the graph, or broadcast a causal-edge selector that lets edges choose their own replacement locally? Which option is most likely to preserve exact two-pass semantics without turning correlation storage into the next BRAM bottleneck?

This is representative steady edge-state RTL evidence, not yet a full decoder timing pass. Opening/closing replay, all accepted batches, correction equivalence, FPGA Fmax, p99 `<=1 us`, miss `<=1%`, full B2, scalable #023, and B7 credit remain open.
