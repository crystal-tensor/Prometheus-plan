# Are rare trajectory divergences bugs—or the best tests we have?

The closed-loop X campaign now covers a contiguous 64-shot prefix. The newest 39-shot shard passes all 6,396 windows and 64,465 occupancy checks, with zero commit-residual, final-residual, or logical-frame failures through real Rust-primal plus Verilator-dual execution.

Six shots make the result more interesting than a larger green denominator. In shots 29, 36, 38, 54, 58, and 60, RTL selects a valid correction that differs from the frozen software trajectory. The following closed-loop window changes accordingly, clears its committed residual, and the trajectory reconverges one window later. Together with shot 15, seven of the first 64 shots now exercise this feedback-sensitive path.

The heuristic question is: **should a streaming quantum decoder test suite treat rare matching degeneracies as noise to canonicalize away, or as high-value state-machine probes to preserve and amplify?** Canonical output makes implementation comparisons easy. Degenerate closed-loop cases test whether the hardware remains correct when its own valid choice changes the future.

The accepted X denominator is now 64/1,024 shots and 10,496/167,936 cases. Z, AXI, FPGA, `p99 <= 1 us`, miss `<= 1%`, full B2, scalable #023, and B7 resource credit remain open.

Evidence: `results/B2_B7_P023_d6_x_closed_loop_shard_0025_0063_evidence_v1.json`
Evidence ID: `49871986321dd63fc8b869f795af90b74af0f595019627f9d351494816100122`
