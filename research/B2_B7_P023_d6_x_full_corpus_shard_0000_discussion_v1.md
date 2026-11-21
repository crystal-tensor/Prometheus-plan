# When one complete shot passes, is correctness still the bottleneck—or is the simulator?

Representative cases can hide sequential state bugs, so we stopped sampling windows and sent the first complete frozen X shot through the real phase-aware Micro Blossom path.

The shot contains all 164 consecutive windows: one opening window, 162 steady windows, and one closing window. The Rust primal and real SpinalHDL `DistributedDual` jointly produced:

- `164/164` valid syndromes;
- `164/164` bit-exact complete corrections;
- `1,648/1,648` clear AddDefect occupancy checks;
- 918 causal selectors and 946 resolved obstacles;
- a maximum of 15 iterations in any window;
- zero forbidden errors and zero unexpected warnings.

The evidence audit passes `40/40`, and the accepted evidence ID is `a7e512f7210af72eecf3f96224eaa2c94d5fc22160fcd2ed41d81b6dc8014304`.

But this is where the engineering question changes:

> If one full shot is correct but a faithful software RTL simulation costs eleven minutes, what is the most convincing way to test the remaining 1,023 shots without weakening the denominator?

The frozen denominator is 1,024 shots × 164 windows = 167,936 cases. This run covers exactly `1/1,024`. Icarus took 658.65 seconds end to end and 439.70 seconds in the simulation body. A one-shot linear projection is roughly 125–187 hours, depending on whether startup is amortized.

We tried the obvious faster backend. Verilator 5.054 first rejected 2,294 public-signal optimization warnings; after narrowly suppressing that warning class and restoring C++14, compilation exposed a real version boundary: SpinalHDL 1.9.3's generated wrapper expects the old `WData*` ABI, while current Verilator uses `VlWide`/`WDataOutP`. We removed the failed backend experiment from the accepted patch.

Which route would you trust most?

1. Pin an older Verilator compatible with the SpinalHDL 1.9.3 wrapper.
2. Adapt and independently test the wide-signal wrapper for Verilator 5.054.
3. Keep Icarus as the oracle and run hash-bound shards in parallel.
4. Use a fast backend for the full corpus but randomly cross-check shards against Icarus.

The claim boundary remains strict: this is `164/167,936` X cases, not full X; Z, AXI, FPGA timing/resources, p99 `<=1 us`, miss `<=1%`, full B2, scalable #023, and B7 credit are still open.
