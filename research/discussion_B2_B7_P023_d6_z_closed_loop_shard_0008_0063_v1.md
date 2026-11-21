# When a decoder passes 6.25% of Z, what should we expect the remaining 93.75% to reveal?

The first eight Z shots showed that the stateful RTL route could run. We have now extended the same unchanged gate through shots 8–63: 56 new trajectories and 9,184 consecutive opening/steady/closing windows.

Every syndrome is valid. All 93,512 occupancy checks clear. Commit residual, final residual, and final logical-frame failures remain zero, with a maximum of 21 solver iterations. Combined with the first shard, the accepted Z prefix is now 64/1,024 shots and 10,496/167,936 cases—exactly 6.25%.

The heuristic question is: **does early clean coverage mainly test implementation stability, while rare trajectory structure dominates the value of the remaining denominator?** A wider clean prefix increases confidence that the route is not a smoke-test artifact. It still cannot tell us whether a late, low-frequency state sequence will falsify the contract.

So full Z remains false. AXI, FPGA timing/resources, measured `p99 <= 1 us`, miss `<= 1%`, full B2, scalable #023, and B7 resource credit remain open. The 120-qubit / depth-7,000 capacity question is deliberately outside this acceptance design.
