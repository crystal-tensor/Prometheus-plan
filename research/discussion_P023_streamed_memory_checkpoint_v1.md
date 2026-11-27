# What breaks between a thousand surface-code rounds and a million?

A distance-7 memory had previously passed a thousand-round benchmark. On actual million-round trajectories, the streamed d=7 arm already has 57 X and 61 Z failures in 128 shots per basis; our fixed-cohort gate allows at most three. A distance-15 candidate passed all four short cohorts, even with paired measurement flips, but that still says nothing decisive about a million rounds. Its long runs are underway.

**How would you distinguish a code that just needs more distance from a decoder or noise model that leaves a long-time error floor?** If you have a compact stress process with a specified timescale and syndrome signature, what should we freeze before testing it? Another way to participate: propose a smaller distance/decoder pair that has a credible chance of clearing the same two-basis, million-round gate.

[Circuit, exact seam controls, and raw failure receipts](https://github.com/crystal-tensor/Prometheus-plan/blob/main/research/P023_streamed_memory_checkpoint_v1.md)
