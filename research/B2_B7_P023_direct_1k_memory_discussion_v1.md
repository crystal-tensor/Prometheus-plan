If 1,000 rounds pass in a simulator, what—exactly—has been learned about scalable quantum memory?

The new #021/B7 · #022/B2 · #023 packet removes one ambiguity from our earlier result: this time the X and Z memories are **directly executed for 1,000 rounds**. There is no seven-round extrapolation hiding inside the claim.

The frozen run uses Stim 1.16.0 and PyMatching 2.4.0 at circuit-level physical error 0.001, distances 3/5/7, and 3,838 shots per basis-distance row. Across 23,028 shots and 1,596,608,000 physical-qubit-rounds, 1 distance(s) clear a 1% total-failure Wilson gate in both X and Z: **[7]**. The stricter 0.1% paired gate is passed by 0 distance(s).

Every row is bound to its exact circuit, detector error model, bit-packed detector/observable/prediction chunks, failure vector, seed, toolchain, and local decoder timing. But the raw traces are not published, the noise is not calibrated hardware noise, and a million-round experiment has not been run.

So where should the scientific boundary sit?

- Is 1,000 directly observed rounds a meaningful staging milestone, or still too short to earn any memory-language at all?
- Should a million-round simulator run be attempted next, or should correlated-noise and drift stress come first?
- Are hash-bound traces enough for reproducibility, or must the full detector stream be public before the result is useful?
- What same-condition qLDPC or alternative-code denominator would prevent a surface-code baseline from grading itself?
- Which decoder-throughput measurement belongs in a resource ledger: local batch throughput, worst-case latency, or a hardware-timed deadline miss rate?

Useful contributions are falsifiable: propose a drift/correlation model, a public trace format, a paired-basis confidence rule, or a code-family comparison that keeps the identical noise, decoder, horizon, and confidence budget.

Current boundary: **the direct 1,000-round staging gate is evaluated; #023 scalable-memory readiness remains false; B2 low-overhead credit remains false; B7 memory-derived resource credit remains zero.** Formal checks: 24/24.
