# B2/B7/#023 X phase-superset edge-bank RTL v1

## Question

If one clock edge can switch 3,762 edge masks and weights, what state still prevents a complete decoder phase transition?

## Same-image X phase banks

The phase-superset plan is now realized as one generated RTL image for the X basis. It contains 3,762 canonical edges and 1,147 canonical vertices, with opening, steady, and closing banks for edge-active masks, base weights, resident rules, vertex-active masks, and maximum-growth bounds.

At a legal `phaseSelectValid` event, the prototype selects one phase and restores every banked register in one simulated clock edge. Subsequent causal selectors apply only resident rules belonging to the active phase. A selector aimed at an inactive or out-of-range source increments the rejection counter and cannot change any edge weight.

## Generated-RTL replay

SpinalHDL 1.9.3 generated a 31,684,681-byte Verilog image, and Icarus Verilog 13.0 compiled and executed it. All 12 opening/steady/closing × zero/p50/p99/maximum batches pass.

The transition replay performs 12 phase selections and accepts 103 causal-selector commands. It deliberately submits 12 inactive selectors; all 12 are rejected, with 45,144 full-edge no-change comparisons. Post-selection and post-batch checks contribute another 90,288 edge comparisons, for 135,432 conservative edge-state comparisons in total. Vertex-active and maximum-growth state contribute 27,528 comparisons.

The evidence audit binds the source plan, source traces, Scala harness, simulation transcript, generated-artifact hashes, comparison accounting, and every positive and negative claim gate. It passes `96/96`. Evidence ID: `c4b2298aefd66f95d537639872c2890adf5cc9bcd16f7283f8af55962a564a86`.

## Claim boundary

This is a same-image X edge/vertex bank and transition prototype, not a complete Micro Blossom decoder. It is not yet integrated into the real `DistributedDual` vertices, edges, convergecast, or conflict logic. Phase-banked fault/output maps, complete corrections, Z-basis banks, an AXI phase-control path, FPGA synthesis, Fmax, LUT/BRAM, routing closure, and end-to-end update-plus-decode latency are absent.

Consequently p99 `<=1 us`, miss `<=1%`, full B2, scalable #023, and B7 resource credit remain false, false, false, false, and zero.

## Next gate

Integrate the X banks and active masks into the real `DistributedDual` data and control paths, bind phase selection to a quiescent reset command, add phase-banked fault/output maps, and compare complete corrections before extending the same mechanism to Z.
