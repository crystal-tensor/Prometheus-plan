# B2/B7/#023 six-image Micro Blossom RTL generation v1

## Question

Can the six frozen d=6 X/Z graph and rule classes enter the pinned Micro Blossom toolchain without silently overflowing the fixed 16-bit growth budget?

## Result

Classification: `six_bound_d6_images_direct_load_and_rtl_generation_pass_batch_replay_and_timing_open`.

All six opening/steady/closing images are exported as directly loadable `SingleGraph` JSON, independently audited, loaded by the pinned Scala decoder configuration, and elaborated into dynamic-weight AXI4 Verilog. The largest output is 484,005,989 bytes. Icarus Verilog 13.0 independently accepts the complete largest X-closing output.

## The overflow caught before publication

The first image export preserved PyMatching's accepted even weights literally. Its maximum base weight, 33,706, fit 16 bits, but the independently recomputed maximum vertex-to-boundary growth reached 74,622. Micro Blossom gives individual vertex grown state enough bits, yet its bus and Looper cumulative-growth fields are fixed at 16 bits. Generator success alone therefore could not establish a safe representation.

Every accepted base and replacement weight has an exact common divisor of two. The final images store the corresponding integral half weights: maximum 16,853, with no rounding or clamping. Uniform division by a positive common factor preserves every path ordering and every tie. The independently recomputed maximum growth becomes 37,311, below 65,535.

## Executed checks

| gate | result |
|---|---:|
| independent graph/hash/rule/tree/Dijkstra audit | pass, 6/6 |
| pinned `DualConfig` direct load and `sanityCheck` | pass, 6/6 |
| inferred hardware weight width | 15 bits, 6/6 |
| SpinalHDL dynamic-weight AXI4 generation | pass, 6/6 |
| independent full Icarus compile | pass on largest X-closing RTL |

The six image evidence ID is `b80bc090b32ac4a3aad2e3eca7247156a8571bfd9ee659c302afd4f67b95e3f8`.

## Claim boundary

This closes the “six images have not entered RTL” gate. It does **not** yet replay the accepted fresh X/Z replacement batches or corrections in RTL, measure p99 update-plus-decode cycles, close FPGA timing, or measure LUT/BRAM. Thus p99 `<=1 us`, miss `<=1%`, full B2, scalable #023, and B7 resource credit remain false, false, false, false, and zero.

## Next gate

Reconstruct the already accepted 2,048-shot X/Z corpus from its frozen seeds, emit the exact per-window edge-update batches, replay them against these six RTL configurations, and compare every addressed edge and correction before measuring p99 cycles.
