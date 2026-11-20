# B2/B7/#023 resident causal-selector RTL replay v1

## Question

If a decoder spends two slow-clock cycles shipping every replacement weight, can it preserve the same frozen semantics by shipping only the causal source edges and keeping the rules beside the graph?

## Resident selector implementation

A supplemental patch on pinned Micro Blossom commit `a3530d9e` adds a separate AXI selector window at `0x4000` while preserving the existing `0x3000` direct-weight protocol. The steady X/Z image contains 15,610 directed rules, of which 15,606 strictly lower a target's base weight. X and Z use the same steady rule table.

Each target edge stores its local `(source edge, replacement weight)` rules. Reset restores the base state. Every selected source applies `min(current, resident replacement)` at matching targets, so selector order is irrelevant and repeated or overlapping causal neighborhoods reproduce the frozen strict-lowering aggregation.

The 541-line supplemental patch has SHA-256 `cd2f7a819a7fea699f07c504d5ae5c88dfe447dbe3b9515ebd580aec4c55b511`. The prerequisite dynamic-weight patch remains byte-identical at `990beb9fc86329960a6eef88b9f88b601f5807f0e2ae2abd71acc0d3671e27d5`.

## Full-edge RTL replay

The full 2,973-edge steady design elaborates under SpinalHDL 1.9.3, generates 412,800,759 bytes of Verilog, and passes Icarus Verilog 13.0 compilation. The eight frozen X/Z zero, p50, p99, and maximum batches are reset and replayed through real 64-bit AXI selector writes.

All `8/8` batches pass. Every edge is compared after every batch, yielding `23,784/23,784` exact edge-state checks with zero mismatches. An independent evidence audit passes `102/102`.

## Transport reduction

The selector path retains the measured two slow-clock cycles per AXI command, but one command fans out through the resident rule table:

- X representative p99: 102 replacement writes / 204 cycles become 11 selectors / 22 cycles, a 9.27× reduction.
- Z representative p99: 103 replacement writes / 206 cycles become 12 selectors / 24 cycles, an 8.58× reduction.
- X/Z representative maximum spans become 30/38 cycles instead of 340/358.
- Across the complete accepted trace, the selected-source p99 is 13 for both bases, projecting 26 update-only cycles. That full-distribution number is not yet a full RTL replay result.

## Claim boundary

This establishes steady representative edge-state correctness for the resident selector. It does not establish FPGA Fmax, LUT/BRAM, routing closure, opening/closing switching, all 335,872 accepted batches in RTL, full correction equivalence, or end-to-end decoder latency.

Therefore p99 `<=1 us`, miss `<=1%`, full B2, scalable #023, and B7 resource credit remain false, false, false, false, and zero. The next gate is FPGA synthesis plus opening/closing and full correction replay. Evidence ID: `5e871d6b0654cb9b2681b438bec8ee3839deb4468c617ac3a358acd3a51b5518`.

