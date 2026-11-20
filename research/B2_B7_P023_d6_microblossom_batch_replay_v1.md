# B2/B7/#023 accepted-batch trace and representative RTL replay v1

## Question

If a serial dynamic-weight path is functionally exact, does its p99 batch already consume the one-microsecond budget before decoding begins?

## Accepted trace reconstruction

The Discussion #341 seeds reconstruct the already accepted 1,024-shot X and 1,024-shot Z corpus without opening any new stochastic sample. Every one of the 167,936 windows per basis is converted into a reset-bound list of `(15-bit edge index, normalized integer weight)` updates.

X contains 160,975 unique update batches and 6,362,111 total writes; Z contains 161,129 unique batches and 6,425,518 writes. The accepted corpus hashes, candidate prediction hashes, residual zeros, and full replacement-count distributions reproduce exactly. An independent audit passes `108/108`, including recomputation of the zero/p50/p99/maximum batches from their selected source edges and the serialized correlation tables.

## Full-edge representative RTL replay

The eight X/Z zero, p50, p99, and maximum batches all occur in the steady phase. Each batch executes Reset and then real 64-bit AXI dynamic-weight writes against the full 2,973-edge steady RTL. After every batch, all 2,973 edge registers are compared with the expected base-or-replacement value.

All `8/8` batches pass and all `23,784/23,784` edge-state comparisons pass. X p99 applies 102 updates; Z p99 applies 103. The observed write span is exactly two slow-clock cycles per update: 204 cycles for X p99 and 206 for Z p99. Maximum batches require 340 and 358 cycles.

## Deadline interpretation

An update-only span of 204/206 cycles needs at least a 204/206 MHz slow clock to fit one microsecond. That calculation deliberately excludes Reset, syndrome delivery, first and second matching, and correction output. No FPGA Fmax has been measured, so this is architecture pressure—not a timing pass or a fabricated hardware failure.

The serial path is now the binding fork: widen the update lane, keep the three rule images resident and select by causal edge, or broadcast causal selectors instead of shipping each replacement.

## Claim boundary

Representative steady edge state passes in RTL. Opening/closing representatives, all 335,872 accepted window batches, RTL correction equivalence, full update-plus-decode p99, FPGA timing, and LUT/BRAM remain open. Therefore p99 `<=1 us`, miss `<=1%`, full B2, scalable #023, and B7 resource credit remain false, false, false, false, and zero.
