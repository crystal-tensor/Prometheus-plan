# If 8-bit weights preserve every logical answer, what still prevents a sub-microsecond decoder?

This fresh holdout asks a deliberately narrower question than ‘does Micro Blossom solve our decoder?’ It tests whether the current correlated window semantics can first cross the integer-graph admission boundary without borrowing unmeasured hardware claims.

X/Z candidate frames agree with the unquantized online reference on `1024/1024` and `1024/1024` fresh shots. The online reference also agrees with the full-block correlated reference on `1024/1024` and `1024/1024`; every commit and final residual is zero.

The steady graph is 630 vertices and 2,973 edges and repeats 162/164 windows per basis. Yet a first pass touches only p99 13 selected edges while correlation can expose p99 `102/103` affected X/Z edges—an upper-bound payload of `2040/2060` bits before the second match.

Heuristic question: should a controller broadcast a compact list of causal first-pass edges into a resident on-chip correlation table, instead of streaming every replacement weight over a bus? What architecture would prove that the broadcast, reweight, second exact match, and correction readout all fit the same p99 clock?

The boundary is intentional: no candidate RTL was generated or run, and no cycle, FPGA, p99, LUT, BRAM, full B2, #023, or B7 claim is awarded. The next falsifier is a cycle-accurate implementation of the six admitted static graphs with exact correction replay.

Evidence ID: `a9b7b679114d47ed4996020bd1bfc719229608fafb05800895537dbfb2709f49`.
