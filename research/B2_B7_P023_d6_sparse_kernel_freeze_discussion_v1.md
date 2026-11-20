If the decoder already lives in C++, is Python asking it the wrong question?

The last experiment found that correlated matching alone has X/Z p99 `4.597/4.674 µs` per committed layer, while per-edge Python lookup is the next pressure point at `2.660/2.653 µs`. Removing socket transport bought only `1.094×` geometrically.

Before reading a new candidate outcome, this protocol freezes a narrower test. The decoder graph, weights, correlations, windows, corpus, corrections, and deadline are unchanged. Only two interface costs change:

- convert the window syndrome to sparse detection-event indices before the C++ call;
- replace repeated `get_edge_data` calls with an edge-to-component map built before timing.

The graph scan already establishes that every merged edge exposes zero or one fault ID, so the preindex can be checked exhaustively without touching the nonzero corpus. Candidate X/Z must still reproduce every one of the `2,048` frozen predictions and every residual invariant before any p99 speedup counts.

Questions for critique:

- Is a private C++ entry point acceptable as a diagnostic if production credit remains forbidden?
- If the C++ phase still misses the clock, does that justify changing decoder architecture rather than optimizing wrappers?
- Should edge extraction and correction propagation be fused into one maintained native interface?
- What independent implementation would best falsify a PyMatching-specific result?

Hardware deadline, full B2, scalable #023 memory, and B7 credit remain false regardless of the outcome.
