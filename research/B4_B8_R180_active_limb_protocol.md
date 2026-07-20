# B4/B8/B10 R180 Active-Limb Linux x86-64 Protocol

- Status: `preregistered_unopened`
- Protocol payload hash: `a10ab4cb90c5e9b9fe5b0d6ef78209ea268a9939581fcfdd76cfd1dc9112a80c`
- Contract payload hash: `95176ab2f84b6e32fcaaad74ca4c3205dc82131edfe85f59f926264e97375d7b`
- Execution: unopened until a public Discussion is created

## Research Question

Can tracking the highest active 64-bit limb preserve exact retained-binary64 selection while reversing R179's Linux performance loss caused by scanning all 34 fixed limbs?

## Frozen Matrix

The workflow fixes `52` isolated Linux x86-64 workers, `3200` recorded calls, and `832` warmups across source f64, BigUint exact, fixed-34 exact, and active-limb fixed exact scoring.

## Performance Gates

Active/source must remain at most `3.0` per cell and `2.5` aggregate. Active/fixed-34 must be at most `0.9` and active/BigUint at most `1.0`. Active/source peak RSS must remain at most `1.25`.

## Claim Boundary

This is a preregistered Ubuntu x86-64 cost-attribution experiment. It does not claim an upstream patch, production remedy, confirmed Qiskit bug, hardware evidence, quantum advantage, BQP separation, solved B4/B8/B10, or new credit before execution.
