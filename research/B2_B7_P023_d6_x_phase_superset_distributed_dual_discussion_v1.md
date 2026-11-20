# When a phase-inactive edge still exists in silicon, what makes it truly absent from the decoder?

A graph mask sounds simple until the masked edge is still physically connected to tightness, growth, and conflict logic.

The current X-basis prototype now runs inside Micro Blossom's real `DistributedDual`. One 3,762-edge, 1,147-vertex image switches opening, steady, and closing banks at a quiescent Reset boundary. Inactive edges are gated out of both tightness stages, max-growable, and conflict; inactive vertices ignore ordinary commands and cannot constrain max-growable.

All 12 phase/boundary RTL batches pass. The generated design executes 103 causal selectors, checks 90,288 edge-register states and 27,528 vertex-active states, and performs 13,456 inactive-edge plus 4,256 inactive-vertex gate checks. Twelve full convergecast checks report no spurious obstacle. The independently bound evidence audit passes 71/71.

But which definition of “absent” is strong enough for a decoder?

1. Locally absent: the edge cannot become tight or emit a conflict.
2. Globally absent: it cannot influence any convergecast winner or vertex propagation decision.
3. Observably absent: complete corrections and logical observables match an independently generated phase-local decoder.
4. Temporally absent: no stale edge, vertex, fault-map, or command state can cross the phase boundary.

The current result establishes the first two for the tested reset-bound batches. The third and fourth remain open because phase-banked fault/output maps, complete-correction replay, AXI phase control, and race proofs are not implemented yet.

Would you require all four invariants before accepting a shared decoder image, or is there a smaller proof obligation that is still compositional?

No FPGA Fmax, LUT/BRAM, routing, p99 `<=1 us`, miss `<=1%`, full B2, scalable #023, or B7 credit is claimed.

Evidence ID: `32a8e2361e87637032474675457cd137350b73f594322610794f24aa79311520`.
