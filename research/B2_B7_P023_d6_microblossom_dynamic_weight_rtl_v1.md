# B2/B7/#023 Micro Blossom dynamic-weight RTL path v1

## Question

If 16-bit weights remove every streaming disagreement in software, can the pinned Micro Blossom design accept an explicit edge update without bypassing its ordering and context-safety machinery?

## Result

Classification: `dynamic_weight_write_path_rtl_sim_pass_d6_batch_and_timing_open`.

The previously reserved `LoadWeightsExternal` operation now has a concrete sideband carrying a 15-bit edge index and up to a 16-bit weight. A packed write window at `0x3000` feeds the existing instruction FIFO, clock-domain crossing, Looper context race guard, broadcast path, response accounting, and per-edge register/RAM writeback. A bare opcode is rejected because it cannot carry the edge and weight payload.

## Executed checks

| level | result | falsifier exercised |
|---|---:|---|
| Scala/SpinalHDL compile | pass | all modified source type-checks against pinned SpinalHDL 1.9.3 |
| core sideband RTL simulation | 1/1 | target edge changes, adjacent edge does not, Reset restores base |
| 64-bit AXI end-to-end RTL simulation | 1/1 | `0x3000` write crosses bus, CDC FIFO, Looper, broadcast, and register writeback |
| 32-bit AXI-Lite end-to-end RTL simulation | 1/1 | address-derived context and packed 32-bit update reach the same state transition |

The patch applies cleanly to Micro Blossom commit `a3530d9e58ff790dafc93d56c9a2769ceac84731`. Patch SHA-256: `990beb9fc86329960a6eef88b9f88b601f5807f0e2ae2abd71acc0d3671e27d5`.

## What changed

- The ISA recognises and formats `LoadWeightsExternal` explicitly.
- The payload travels as a sideband because `15-bit edge + 16-bit weight + 6-bit opcode` cannot fit a 32-bit instruction.
- Dynamic edge state writes only the addressed edge and restores the graph weight on Reset.
- Both 64-bit AXI and 32-bit AXI-Lite expose the same packed update semantics.
- Updates remain ordered with decoder instructions; they do not write the edge array through an unsynchronised debug port.

## Claim boundary

This closes the source-level “write path absent” blocker and adds generated-RTL simulation evidence. It does **not** yet run the six frozen d6 graph/rule images, replay the fresh X/Z corrections in RTL, measure a 102/103-edge p99 batch, close FPGA timing, or measure LUT/BRAM cost. Therefore p99 `<=1 us`, miss `<=1%`, full B2, scalable #023, and B7 resource credit remain false, false, false, false, and zero.

## Next gate

Generate the six frozen images, stream every replacement batch through this exact bus path, compare RTL corrections to the accepted v2 software frames, and measure update-plus-decode p99 cycles. A single wrong edge, stale context, missed write, or deadline miss is a veto.
