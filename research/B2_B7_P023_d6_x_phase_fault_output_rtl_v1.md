# B2/B7/#023 X phase-banked fault-output RTL v1

## Question

If the matching is already known, can a decoder still be wrong at its final XOR?

## Sparse phase-banked output map

The X opening, steady, and closing banks now include the missing fault/output map inside the real Micro Blossom `DistributedDual` component. Each phase-local edge stores zero, one, or two fault IDs. A reset-bound phase selection clears a 789-bit maximum-width correction accumulator; the primal host can then submit each selected subgraph edge exactly once, and the RTL XORs its phase-local fault IDs into the correction vector.

The three output widths are 229 bits for opening, 246 bits for steady, and 789 bits for closing. The fixed two-ID bound is derived from every edge in the frozen phase images rather than assumed by the implementation.

## Exhaustive edge-map and complete-reference replay

The generated RTL replay checks all 3 × 3,762 phase/edge combinations: 11,286/11,286 mappings pass. This includes 1,682 phase-inactive edges, all of which produce an empty fault map.

Twelve accepted zero/p50/p99/maximum representative syndromes are reconstructed from the frozen X corpus with every preceding online window applied. Their final second-pass MWPM subgraphs contain 104 selected edges in total. Feeding those complete subgraphs through the RTL accumulator reproduces all 12 public correction vectors bit-for-bit.

SpinalHDL 1.9.3 generates 573,238,230 bytes of Verilog; Icarus Verilog 13.0 compiles a 701,116,898-byte simulation image. The independent evidence audit passes 119/119. Evidence ID: `8bd353f5cd2785fb2221a123d819d42ddca53fa20fa621188db1724d4234e852`.

## Claim boundary

This closes the X phase-banked fault/output-map and complete-reference-subgraph readout gate. It does not prove that the phase-aware `DistributedDual` produced those subgraphs: the frozen, previously accepted software second-pass MWPM supplies them to the RTL accumulator. Therefore `complete_corrections_compared` remains false until the Rust primal host and the real phase-aware dual jointly generate the same selected edges.

Z phase banks, AXI phase control and correction readout, race proof, FPGA synthesis, Fmax, LUT/BRAM, routing, and end-to-end latency also remain open. Consequently p99 `<=1 us`, miss `<=1%`, full B2, scalable #023, and B7 resource credit remain false, false, false, false, and zero.

## Next gate

Extend the Scala/Rust host protocol with reset-bound phase selection and resident-selector commands. Run the Rust primal against the real phase-aware `DistributedDual`, obtain its final subgraph, and feed that subgraph directly into this verified accumulator. Only exact correction equality can close the end-to-end X gate.
