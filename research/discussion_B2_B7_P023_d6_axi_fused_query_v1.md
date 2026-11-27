# Can a read become a command without making the decoder execute twice?

We tried one opt-in AXI request that launches FindObstacle and returns its packed status. Across 1,640 paired decoder windows, the core saw exactly one query for every accepted request, and the correction output did not change. The fused path saved 74,723 sampled cycles against the previous packed-read path; 40,736 are fixed savings, and the rest come from the removed writes' deliberate address/data skew.

The counterintuitive case: an older half-write must finish before the query runs, but a held B response need not stop the query from returning. Both response beats can remain held. Deliberately retaining a consumed request or returning before the core capture breaks the corresponding test.

**If this moved from a serialized test manager into a controller that retries on timeout, how would you make the command safe to retry?** Would you use a tagged request, a read-only result queue, or keep the separate write and status read? A small bus trace that breaks a proposed contract would be especially useful.

This is bounded RTL simulation, not a production MMIO or FPGA latency claim. [Replay, ordering tests, and audit](https://github.com/crystal-tensor/Prometheus-plan/blob/main/research/B2_B7_P023_d6_axi_fused_query_v1.md)
