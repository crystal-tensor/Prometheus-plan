# The closing correction takes 25 reads. Why is the slow tail elsewhere?

We replayed the same 1,640 distance-6 decoder windows twice, comparing each transaction and correction bit. Removing the deliberately injected AXI response stalls moved the simulated p99 from 1,562 to 921 cycles for X and from 1,609 to 946 for Z. The outputs did not change.

The surprise came after the stalls were gone: in the windows at or above p99, issuing solve commands and reading obstacle status used 65% of the X bus cycles and 68% of the Z bus cycles. Those slow windows were all steady-state, and their correction reads used about 2%. The long closing correction is real, but it was not what put these windows in the tail.

**Would you start by combining the two common obstacle-status reads, or by removing round trips between the host and the solver?** If we pack the status, what sequence of back-to-back queries and held responses would you use to catch a status word or conflict detail coming from the wrong query?

This is a bounded RTL simulation, not an FPGA latency claim. [Paired replay and audit](https://github.com/crystal-tensor/Prometheus-plan/blob/main/research/B2_B7_P023_d6_axi_cycle_profile_v1.md)
