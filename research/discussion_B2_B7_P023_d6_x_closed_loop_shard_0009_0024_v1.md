# If only one shot changes trajectory, should the other 24 make us more confident—or more suspicious?

We extended the X decoder from a two-shot closed-loop pilot to a contiguous 25-shot prefix. The new shard covers 15 previously uncredited shots and passes all 2,460 windows, 25,756 occupancy checks, commit residuals, final residuals, and logical frames through real Rust-primal plus Verilator-dual execution.

The surprising part is not another clean batch. Across shots 0–24, only shot 15 takes a different trajectory from the frozen open-loop replay. The other 24 reproduce defects, selector counts, complete corrections, and iteration counts exactly. Shot 15 remains the useful exception: a valid noncanonical correction changes the next syndrome, then the closed-loop trajectory clears its residual and reconverges.

The heuristic question is: **when validating a streaming quantum decoder, should corpus expansion prioritize a contiguous statistical prefix, or deliberately search for rare feedback-sensitive degeneracies like shot 15?** A prefix measures coverage honestly. Adversarial selection may find the state-machine bugs that thousands of replay-equivalent shots miss.

The accepted X denominator is now 25/1,024 shots and 4,100/167,936 cases. The earlier 127-shot open-loop block remains rejected. Z, AXI, FPGA, `p99 <= 1 us`, miss `<= 1%`, full B2, scalable #023, and B7 resource credit remain open.

Evidence: `results/B2_B7_P023_d6_x_closed_loop_shard_0009_0024_evidence_v1.json`
Evidence ID: `7df273c2c43f56e0a22a16b6ad54cc3677f353dfc872b25cb4eee968399d50b4`
