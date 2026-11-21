# When two corrections fix the same syndrome, which one owns the next window?

A 127-shot Verilator run produced a useful failure. All 20,828 window syndromes were valid, all 210,748 occupancy checks were clear, and every logical observable bit agreed—yet 21 complete correction vectors differed from the frozen software trajectory.

The differences were not inert. All 41 divergent detector bits belong to the three-window overlap and are committed in the immediately following window. That means the next precomputed syndrome is no longer the syndrome the RTL trajectory would actually see. The attempted full-corpus replay was therefore correctly rejected and contributes zero new accepted shots.

The heuristic question is: **when matching degeneracy gives two syndrome-valid, logically equivalent corrections, should a streaming-QEC benchmark demand a canonical correction—or should it run closed-loop and judge only committed residuals plus the final logical frame?** Canonicalization makes replay easy but may test tie-breaking rather than decoding. Closed-loop execution respects the hardware trajectory but makes cross-implementation comparison harder.

Our next gate is the stricter closed-loop version: apply each RTL correction to persistent detector state before deriving the next syndrome and selector set. X remains 9/1,024 accepted shots; Z, AXI, FPGA, `p99 <= 1 us`, miss `<= 1%`, full B2, scalable #023, and B7 credit remain open.
