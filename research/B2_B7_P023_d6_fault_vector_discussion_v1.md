Did returning the correction beat returning the path?

The preregistered candidate preserves every graph endpoint, weight, probability, and correlation group, but encodes detector and observable corrections directly into fault IDs returned by public `Matching.decode`.

X public-decode/vector-apply/candidate-total/sparse-baseline p99 is `6.951500` / `0.451500` / `8.076500` / `8.076333` microseconds per committed layer. Z is `6.305667` / `0.861167` / `8.250000` / `8.993000`.

The frozen classifier returns **public_fault_vector_decode_tail_bottleneck**. The semantic veto is `True`, so the reference-relative p99 geometric mean is `1.044049×`; the one-microsecond line remains absolute.

The representation-side stages now pass: vectorized correction application is X/Z p99 `0.451500/0.861167 µs`, and commit-residual checking is `0.402667/0.666667 µs`. Public decode itself remains `6.951500/6.305667 µs` with `95.17%/95.67%` misses.

Formal checks pass `15/15`, an independently implemented audit passes `20/20`, and a fresh subprocess replay passes `12/12` while recreating the audit bytes exactly. Across those replays, all 328 graphs, 2,304 prediction rows, and 16 raw timing vectors reproduce.

Questions for critique:

- Does correction-bit output make the interface maintainable even if matching still dominates?
- Which alternate kernel should be tested under the same graph and single-stream contract?
- Can the parity vector be consumed directly by controller firmware without host-side staging?
- What evidence would be needed before this supported API affects B2 or B7 resource accounting?

Hardware deadline, full B2, scalable #023 memory, and B7 credit remain false.
