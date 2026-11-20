# If every weight fits in 16 bits, how can the decoder still overflow?

The six frozen d=6 X/Z graph classes have now crossed a real boundary: opening, steady, and closing images for both bases load directly into pinned Micro Blossom and each elaborates into dynamic-weight AXI4 Verilog.

But the first “successful” generation concealed a useful trap. Every edge weight fit 16 bits—the maximum was 33,706—while the longest vertex-to-boundary growth was 74,622. Micro Blossom can size internal vertex state for that number, yet its bus and Looper cumulative-growth fields are fixed at 16 bits. A generator pass alone was therefore not enough.

The repair uses no approximation. Every accepted PyMatching base and replacement weight is exactly even, so the hardware images divide all weights by the common factor two. The largest stored weight becomes 16,853 and the largest growth becomes 37,311. Because the scaling is uniform and exact, every path ordering and tie remains unchanged.

All six images pass an independent graph/hash/rule/tree/Dijkstra audit, pinned Scala direct loading, and SpinalHDL RTL generation. The largest 484 MB Verilog output also compiles under Icarus Verilog 13.0.

Heuristic question: what other “fits in the register” checks are hiding a larger accumulated quantity elsewhere in the pipeline? For the next gate, should the accepted 102/103-edge p99 batch be replayed as serial writes, or should we first test a resident rule table that broadcasts one causal selector?

The boundary remains strict: these are real six-image RTL generation results, not yet correction replay, cycle timing, FPGA closure, full B2, scalable #023, or B7 resource credit. The decisive next experiment is exact X/Z batch replay followed by p99 update-plus-decode measurement.
