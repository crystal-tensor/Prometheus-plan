# If a decoder's graph fits in 8 bits, where does the missing microsecond go?

The last experiment isolated the bottleneck to correlated matching. Two tempting shortcuts now have hard negative evidence: zero/single-edge caching covers only about 5% of windows, while `decode_batch` with exactly one syndrome still lands near 4 µs per committed layer.

The next route changes architecture, not semantics. The current X/Z workload needs only three static graph classes per basis, and its 630-vertex, 2,973-edge steady graph repeats 162 of 164 times. An all-zero preflight shows that every graph endpoint, correction map, and correlation group survives an 8-bit fixed-point representation; no fresh random sample has been observed yet.

But the correlation step is the interesting part. On the already observed diagnostic prefix, the first match selects only p99 13 edges, while their correlation neighborhoods expose p99 103/102 potentially affected X/Z edges—roughly 2,060/2,040 bits if every update is sent as a 12-bit edge index plus 8-bit weight.

So the heuristic question is: should a controller stream a hundred replacement weights, or broadcast the thirteen causal edges into a resident on-chip correlation table and reweight in parallel?

The public holdout will first demand exact X/Z logical agreement and zero residuals on 1,024 new shots per basis. Even a pass grants only graph/semantic admission. No Micro Blossom RTL, FPGA latency, p99 deadline, LUT/BRAM, full B2, #023, or B7 claim is being made.

