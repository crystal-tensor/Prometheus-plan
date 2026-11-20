# If the missing hardware write path now works, where does the one-microsecond budget actually go?

The 16-bit software bridge removed every X/Z streaming disagreement, but that result stopped at an awkward boundary: pinned Micro Blossom had registers for dynamic weights and even reserved `LoadWeightsExternal`, yet no instruction could actually write an edge.

The first RTL bridge now exists. Because a 15-bit edge index plus a 16-bit weight cannot share a 32-bit instruction with the opcode, the patch uses the reserved operation as the semantic commit and carries the payload on a sideband. The update still passes through the existing FIFO, clock-domain crossing, context race guard, broadcast network, response accounting, and edge register/RAM path.

Three generated-RTL simulations pass:

- the addressed edge changes while its neighbour remains untouched;
- the 64-bit AXI `0x3000` window reaches the same edge state;
- the 32-bit AXI-Lite window does too, and Reset restores the frozen base weight.

Heuristic question: when a real window needs p99 `102/103` edge replacements, is one serial update per decoder clock already enough, or will bus handshakes, context ordering, and decode work consume the deadline before the last weight lands? If it fails, should the next architecture widen the stream, cache the three rule images, or broadcast causal-edge selectors instead of weights?

The boundary is deliberate: this is a real RTL write-path pass, not yet a d6 decoder or FPGA timing pass. The six frozen images have not entered RTL, fresh X/Z corrections have not been replayed there, and p99 `<=1 us`, miss `<=1%`, full B2, scalable #023, and B7 resource credit remain closed.

Patch SHA-256: `990beb9fc86329960a6eef88b9f88b601f5807f0e2ae2abd71acc0d3671e27d5`.
