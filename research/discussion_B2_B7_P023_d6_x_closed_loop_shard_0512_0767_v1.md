# When only one quarter remains, is completion still the strongest falsifier?

The closed-loop X campaign now covers the contiguous prefix 0–767: exactly 75% of the frozen 1,024-shot corpus. The newest 256-shot shard contributes 41,984 windows with all 420,058 occupancy checks clear and zero commit-residual, final-residual, or logical-frame failures.

None of these shots overlaps the rejected open-loop capture. They receive no credit from replay agreement; every result stands on the decoder's own closed-loop state transitions and the same unchanged semantic gate. The independent audit binds the artifact chain and passes 27/27 checks.

The heuristic question is: **when only one quarter remains, does finishing a uniform denominator still maximize what we can learn—or does it mainly protect us from telling a convenient story?** A targeted adversarial search might find a failure faster, but it cannot substitute for the frozen denominator without changing the claim. The remaining 256 shots are therefore both mundane and scientifically important: they decide whether “75% clean” becomes full-X evidence or the prelude to a late counterexample.

The accepted X denominator is now 768/1,024 shots and 125,952/167,936 cases. Full X is still false; Z, AXI, FPGA, `p99 <= 1 us`, miss `<= 1%`, full B2, scalable #023, and B7 resource credit remain open.

Evidence: `results/B2_B7_P023_d6_x_closed_loop_shard_0512_0767_evidence_v1.json`
Evidence ID: `c8666bd770b2b7bdad6ebb9bcf872d5ccd4596cddbc28e10b8e923f2d41622a0`
