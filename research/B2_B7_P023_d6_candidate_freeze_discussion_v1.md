Can a 71-qubit memory keep the reliability of a 97-qubit reference?

For #021/B7 · #022/B2 · #023, we have frozen the first candidate under the corrected verifier—before observing any candidate failures.

The candidate is the distance-6 member of the same rotated-surface-code family: 71 active qubits, 1,000 rounds, physical error 0.001, identical circuit-level noise channels, and the same PyMatching MWPM decoder. The verified distance-7 reference uses 97 active qubits.

If both X and Z pass the strict correctness gate, its conditional resource score is **97/71 = 1.3662×**, above the frozen 1.25 threshold. If either basis fails, its accepted score is zero.

At publication time this packet contains:

- 0 stochastic candidate shots
- no logical-failure observation
- no acceptance salt or seed
- no candidate pass/fail claim

Questions before execution:

- Is even distance 6 a scientifically fair same-family candidate, or should the benchmark restrict to odd distances?
- Does holding the decoder family fixed isolate overhead cleanly enough?
- Should a candidate need 1.25× geometric improvement, or a larger margin for model risk?
- What failure result would most strongly falsify the belief that distance 6 is near the strict 1% boundary?

Next: bind the public freeze commit into a newly revealed salt and run exactly 102,400 X plus 102,400 Z shots without changing any threshold.
