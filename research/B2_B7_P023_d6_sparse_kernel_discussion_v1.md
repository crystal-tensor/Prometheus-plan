Did a sparse C++ call remove the decoder's missing microsecond?

The preregistered candidate keeps the correlated graph and every correction decision fixed, but bypasses dense wrapper conversion and replaces repeated edge-data queries with a complete preindex.

X C++/mapping/candidate-total/baseline-total p99 is `4.409667` / `1.666667` / `7.284833` / `8.479167` microseconds per committed layer. Z is `4.618167` / `1.680500` / `7.576333` / `8.701333`.

The frozen classifier returns **cpp_correlated_matching_tail_bottleneck**. The semantic veto is `True`, so the reference-relative p99 geometric mean is `1.156192×`; the one-microsecond line remains absolute.

Formal checks pass `14/14`, an independently implemented audit passes `21/21`, and a fresh subprocess replay passes `12/12` while recreating the audit bytes exactly. Across those replays, all 2,304 candidate/baseline prediction rows and all 18 raw timing vectors reproduce.

Questions for critique:

- Does the result justify a maintained native decoder interface, or a different decoding architecture?
- Which independent implementation should reproduce the sparse-event kernel first?
- Can parallelism reduce tail latency without batching away single-stream causality?
- Where should a private-API diagnostic stop influencing system-level resource claims?

Hardware deadline, full B2, scalable #023 memory, and B7 credit remain false.
