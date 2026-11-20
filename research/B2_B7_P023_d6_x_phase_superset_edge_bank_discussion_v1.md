# If one clock edge can switch 3,762 weights and masks, what still prevents a complete decoder phase transition?

Opening, steady, and closing no longer need three separate X decoder images. One generated RTL image now carries all three phase banks over a 3,762-edge, 1,147-vertex superset.

The prototype atomically restores edge masks, base weights, resident rules, vertex masks, and growth bounds when the phase changes. Across 12 phase/boundary batches, it accepts 103 causal selectors and deliberately rejects 12 selectors aimed at inactive edges. The replay checks 135,432 edge states and 27,528 vertex/growth states; SpinalHDL generation, Icarus execution, and a 96/96 evidence audit all pass.

But this is where the architectural question becomes more interesting: is switching the visible graph state enough?

The real decoder still has state in `DistributedDual` vertices and edges, convergecast and conflict paths, fault/output maps, and the correction interface. A stale value in any one of those places could survive a phase boundary even when every edge weight looks correct.

Which invariant would you require before calling a phase switch complete?

1. Every inactive edge and vertex is structurally unable to participate in growth, tightness, convergecast, or conflict.
2. Reset plus phase selection reconstructs the same complete correction as an independently generated phase-local decoder.
3. Fault/output maps are banked and selected atomically with the graph, so no stale observable can cross the boundary.
4. All of the above, plus a cycle-level proof that the transition cannot race an AXI command or an in-flight decode.

And if all four are necessary, should the hardware bank every phase-dependent state, derive some state from the active graph, or keep three smaller engines instead?

The current result earns only a same-image X bank-switching claim. It does **not** yet earn complete `DistributedDual` integration, complete-correction equivalence, Z-basis switching, FPGA timing/resources, p99 `<=1 us`, miss `<=1%`, full B2, scalable #023, or B7 credit.

Evidence ID: `c4b2298aefd66f95d537639872c2890adf5cc9bcd16f7283f8af55962a564a86`.
