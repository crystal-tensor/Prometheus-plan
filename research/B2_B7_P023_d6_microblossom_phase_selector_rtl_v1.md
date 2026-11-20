# B2/B7/#023 opening/closing resident-selector RTL replay v1

## Question

If opening, steady, and closing are each correct as separate RTL images, what must an integrated decoder pay to make three different graph topologies coexist?

## Frozen phase trace

The already accepted X/Z corpus is reopened from its exact public seeds with zero new stochastic samples. Every shot still executes all 164 windows so the closing syndrome includes the accumulated correction state from the preceding 163 windows.

For each basis and each opening/closing phase, the trace freezes zero, p50, p99, and maximum replacement-count batches. Accepted corpus and candidate-prediction hashes reproduce exactly; commit and final residual failures remain zero. The phase-trace evidence ID is `9fe10f289a4ab8a3bf77d736ea2511ed48e80e776dfa86960f85fb5bc5428bfc`.

## Four independent full-scale RTL replays

Pinned Micro Blossom independently elaborates, generates, and Icarus-compiles four resident-selector designs:

- X opening: 2,901 edges, 15,072 active rules, 403,691,974-byte Verilog.
- X closing: 3,730 edges, 19,306 active rules, 516,206,724-byte Verilog.
- Z opening: 2,896 edges, 15,062 active rules, 402,764,279-byte Verilog.
- Z closing: 3,725 edges, 19,296 active rules, 515,281,783-byte Verilog.

All 16 zero/p50/p99/maximum batches pass. Every edge is checked after every reset-bound batch: `53,008/53,008` states agree with zero mismatches. The independent evidence audit passes `157/157`.

## Selector transport

Each selector still takes two simulated slow-clock cycles:

- representative p99 spans are X opening/closing `20/28` cycles and Z opening/closing `28/24`;
- representative maxima span `38/38/36/36` cycles;
- across all 4,096 accepted opening/closing batches, selected-source p99 projects to X `26/30` and Z `26/32` update-only cycles.

The all-batch figures are trace projections, not all-batch RTL replay.

## Integration boundary

These are four independently generated phase images. They do not implement runtime opening/steady/closing switching. The graph edge counts and topology differ by phase, so changing only a rule bank is insufficient without a superset topology, replicated engines, or reconfiguration mechanism.

No FPGA Fmax, LUT/BRAM, routing closure, integrated phase transition, full correction output, or update-plus-decode p99 has been measured. Therefore p99 `<=1 us`, miss `<=1%`, full B2, scalable #023, and B7 resource credit remain false, false, false, false, and zero. Evidence ID: `15e90f8c1847ed1a30b3057fc790f3f4bb2e57d0472e2f026c211e45fe8cff4c`.
