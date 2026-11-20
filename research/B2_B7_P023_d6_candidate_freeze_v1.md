# B2/B7/#023 Distance-6 Candidate Freeze v1

As of 2026-11-20. Scope is exactly #021/B7, #022/B2, and #023.

## Heuristic question

Can 26 fewer active qubits preserve the strict 1,000-round X/Z reliability of the verified distance-7 reference? This packet freezes that question before looking at one candidate sample.

## Candidate selected without outcome data

The nearest lower-distance member of the same Stim rotated-surface-code family is distance 6. It uses 71 active operational qubits versus the corrected reference's 97, at the same 1,000 rounds, physical error 0.001, circuit-level noise model, and PyMatching MWPM decoder.

| basis | distance | index span | active qubits | detectors | cost | raw circuit hash | canonical hash |
|---|---:|---:|---:|---:|---:|---|---|
| X | 6 | 89 | 71 | 35001 | 71,000 | `25ff38889a317147…` | `ffe0341ec245de66…` |
| Z | 6 | 89 | 71 | 34999 | 71,000 | `07a03803963f6bf1…` | `4fd739aab97b6dc7…` |

If—and only if—both bases pass the frozen correctness gate, the resource score is `97/71 = 1.366197183`, above the 1.25 threshold. Before correctness, the accepted score is 0.

## What is deliberately absent

- candidate stochastic shots: 0
- observed candidate logical failures: none
- acceptance salt: absent
- acceptance seeds: absent
- candidate pass/fail decision: absent

The packet permits only deterministic circuit construction, coordinate-canonical hashing, DEM construction, and matching-graph dimension inspection before the public freeze.

## Post-freeze gate

After this exact packet is committed and published, bind that commit into the acceptance salt and run 102,400 shots per basis. Both one-sided Clopper–Pearson upper bounds at confidence `1-2^-128` must be at most 1%; otherwise the candidate score is 0.

## Claim boundary

This is a preregistered candidate, not an accepted code, B2 improvement, scalable #023 memory, threshold result, hardware result, or B7 credit.

Formal checks: **21/21**. Run ID: `df451381b3dba6a24c00d97b7bfb15d06dd9c45f11d5635876c40b5305f91b44`.
