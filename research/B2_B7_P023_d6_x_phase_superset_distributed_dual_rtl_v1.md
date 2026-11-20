# B2/B7/#023 X phase-superset DistributedDual RTL v1

## Question

When a phase-inactive edge still exists in silicon, what makes it truly absent from the decoder?

## Real DistributedDual integration

The X phase banks now enter the pinned Micro Blossom `DistributedDual` implementation rather than a parallel state-bank prototype. A reproducible patch adds a reset-bound phase register and carries opening, steady, and closing state through the real broadcast, Edge, Vertex, tightness, max-growable, conflict, and convergecast paths.

Each Edge receives a phase-active bit, phase base weight, and phase resident rules. Inactive edges cannot report offload or execute tightness, max-growable length, or conflict. Each Vertex receives a phase-active bit and phase-specific virtual reset state. Inactive vertices ignore ordinary commands and cannot constrain max-growable. Phase selection is legal only as a quiescent Reset event.

## Full-superset generated-RTL replay

The replay constructs the complete X superset with 1,147 vertices and 3,762 edges. SpinalHDL 1.9.3 generates 571,867,041 bytes of Verilog; Icarus Verilog 13.0 compiles a 697,900,922-byte simulation image and executes all 12 opening/steady/closing × zero/p50/p99/maximum batches.

All 12 batches pass. The run applies 12 phase selections and 103 causal selectors, then performs 90,288 full edge-register comparisons and 27,528 vertex-active comparisons. It additionally performs 13,456 inactive-edge output-gate checks, 4,256 inactive-vertex output-gate checks, and 12 no-obstacle checks through the complete max-growable and conflict convergecast trees.

The source patch applies cleanly to pinned Micro Blossom commit `a3530d9e58ff790dafc93d56c9a2769ceac84731` and reproduces the executed source hashes. The evidence audit passes `71/71`. Evidence ID: `32a8e2361e87637032474675457cd137350b73f594322610794f24aa79311520`.

## Claim boundary

This establishes the real X `DistributedDual` edge/vertex/tightness/max-growable/conflict/convergecast phase slice. It does not yet bank the phase fault/output map, compare complete corrections or observables, implement Z banks, expose an AXI phase-control path, prove command-race exclusion, synthesize for FPGA, measure Fmax/LUT/BRAM/routing, or measure end-to-end latency.

Therefore p99 `<=1 us`, miss `<=1%`, full B2, scalable #023, and B7 resource credit remain false, false, false, false, and zero.

## Next gate

Bank the X fault/output map, replay complete accepted syndromes through the phase-aware `DistributedDual`, and compare complete corrections against the three independent phase-local decoders. Only then extend the same path to Z and AXI.
