# A decoder reads one word instead of two. What happens if the next answer is already ready?

On 1,640 paired distance-6 decoder windows, bundling the growable length and conflict flag saved 20,368 AXI reads and 40,736 sampled bus cycles. Expanding each packed word into its two original fields reproduced the same transaction sequence, and the correction outputs were byte-identical.

The interesting failure came in a tiny test: hold the conflicting answer from query A while query B completes. The registered bus beat keeps A's answer. If we let the beat track the live state instead, it changes while held, and the regression catches it.

**Would you stop at the packed status word, or combine issuing the query and returning its status in one request?** If you would combine them, what's the smallest bus trace that could make the decoder execute twice or return a result too early? Counterexamples welcome.

This is serialized RTL simulation; it does not cover overlapped multi-register results or FPGA timing. [Replay, audit, and negative control](https://github.com/crystal-tensor/Prometheus-plan/blob/main/research/B2_B7_P023_d6_axi_packed_status_v1.md)
