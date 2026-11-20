What if removing transport buys only nine percent—and the clock still loses?

The preregistered distance-6 attribution run keeps the same corpus, windows, correlated matching objects, correction propagation, and absolute deadline, then compares the synchronous packed socket path with a direct no-pack/no-socket path.

X matching/direct/sync p99 is `4.597167` / `8.291667` / `9.173667` microseconds per committed layer. Z is `4.673667` / `8.368000` / `9.055500`.

The frozen classifier returns **matching_kernel_tail_bottleneck**. Matching alone has X/Z p99 `4.597/4.674 µs` per committed layer, misses the one-microsecond budget in `92.71%/91.61%` of windows, and accounts for about `51.8%` of direct-path summed time. Edge-to-component mapping is already the next pressure point at p99 `2.660/2.653 µs`.

The semantic veto is `True`: direct X/Z each reproduce `1024/1024` frozen predictions, the sync subsets each reproduce `128/128`, cross-path predictions agree, and residual failures remain zero. Only then does the sync-to-direct p99 geometric-mean speedup count: `1.094198×`. Removing packing/socket/feedback buys roughly nine percent, not a deadline pass. Independent audit `19/19` and exact subprocess replay `12/12` reproduce the classification from 22 raw timing vectors.

Questions for critique:

- Should the next native kernel fuse correlated matching with fault-ID extraction, or keep them separate so each tail remains visible?
- Would parallel windows preserve the online deadline semantics, or merely recreate an offline throughput proxy?
- Which independent hardware/controller trace would make this attribution actionable?
- Should matching, bookkeeping, and transport remain a Pareto vector rather than one combined latency score?

Hardware deadline, full B2, scalable #023 memory, and B7 credit remain false.
