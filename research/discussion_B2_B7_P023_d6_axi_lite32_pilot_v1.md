# A decoder returns 789 bits. What if the bus stalls between words?

A closing correction takes 25 data reads on a 32-bit bus, before reading any metadata. We held a nonzero word on the bus while the decoder switched phase and latched a new correction. The stalled read still returned the old word. When we removed the response latch in a small negative-control test, that same check failed.

On the full distance-6 graphs, the AXI4-Lite pilot reproduced all 1,640 windows from 2 X and 8 Z trajectories bit-for-bit against the direct RTL baseline. The write address and data arrived in both orders, and all 89,484 write and 88,455 read transactions balanced under response stalls.

**What would you test next to tell a faster interface from one that merely hides a race?** Would you start with a packed correction stream, or first measure how much of the tail comes from serial obstacle reads and clock-domain boundaries?

This is same-clock RTL simulation on frozen trajectories, not FPGA or hardware-latency evidence. [Audit and replay details](https://github.com/crystal-tensor/Prometheus-plan/blob/main/research/B2_B7_P023_d6_axi_lite32_pilot_v1.md)
