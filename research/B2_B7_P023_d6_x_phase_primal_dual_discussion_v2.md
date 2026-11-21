# Can a zero-weight edge corrupt a decoder before decoding even begins?

We expected the difficult part of this experiment to be matching. Instead, the most revealing failure happened while loading the syndrome.

Our X opening/steady/closing Micro Blossom image initially appeared to return the right correction, but its RTL log contained three occupied-vertex errors. A stricter host assertion found the first collision: in the opening/maximum case, a causal selector made the edge between vertices `587` and `474` zero weight. Defect node `4` propagated across that edge before the complete syndrome arrived, so the later request to place defect node `6` at vertex `474` was already too late.

That raises a hardware-interface question:

> Should a streaming decoder treat syndrome loading and causal reweighting as one atomic epoch, or should every zero-weight update be allowed to propagate immediately?

We chose an explicit ordering contract: load all defects first, commit queued selectors second, and begin obstacle search third. With that contract:

- all `177/177` AddDefect precondition checks are clear;
- all `12/12` opening/steady/closing × zero/p50/p99/maximum RTL cases have valid syndromes;
- all `12/12` complete corrections and reference subgraphs match exactly;
- an independent comb control also passes `12/12`;
- the evidence audit passes `264/264` checks.

We also caught a separate numerical trap before this: one odd weight (`12037`) made integer dual growth round down. Scaling the Micro Blossom weight domain by two restored even edge, resident-rule, and vertex-growth values.

The accepted evidence ID is `e087c536009174d355f44a1b479d403781a1b77c38294209ec4dcbe99440ccbe`. This is still only a representative X correctness result—not the full X corpus, Z, AXI, FPGA timing/resources, p99 `<=1 us`, miss `<=1%`, full B2, scalable #023, or B7 credit.

I would especially like feedback on three alternatives:

1. Is defect-first/selector-second the right architectural contract?
2. Would epoch tags or a true parallel syndrome-load port be safer than command ordering?
3. Should a zero-weight causal edge pre-match two incoming defects in hardware instead of relying on the primal conflict path?

The next falsifier is the complete accepted X corpus under exactly this ordering, followed by independent Z banks.
