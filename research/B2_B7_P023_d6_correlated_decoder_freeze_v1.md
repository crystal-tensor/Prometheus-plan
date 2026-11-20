# B2/B7/#023 Distance-6 Correlated-Decoder Freeze v1

As of 2026-11-20. Scope is exactly #021/B7, #022/B2, and #023.

## Heuristic question

Can correlations rescue a 1.366× cheaper memory that independent matching rejected? This packet freezes the decoder change before the correlated route sees one stochastic syndrome.

## One change, publicly frozen

The distance-6 circuit, 71 active qubits, 1,000-round horizon, physical error 0.001, four circuit-level noise channels, DEM, 1% target, and `1-2^-128` confidence contract are byte-for-byte unchanged. The only candidate change is enabling PyMatching 2.4.0 two-pass correlated matching at graph construction and decoding.

| basis | decomposed hyperedge instructions | components | max detectors/component | matching nodes | matching edges | stochastic shots |
|---|---:|---:|---:|---:|---:|---:|
| X | 540,061 | 1,154,166 | 2 | 35,001 | 169,918 | 0 |
| Z | 540,040 | 1,154,120 | 2 | 34,999 | 169,908 | 0 |

Stim's suggested decompositions preserve correlation groups with separators; PyMatching's two-pass mode can use those groups when reweighting its second matching pass. Their presence makes the decoder route structurally non-vacuous, but says nothing yet about its logical failure rate.

If—and only if—both X and Z pass after the public freeze, the physical-memory score is `97/71 = 1.366197183`. Before correctness, the accepted score remains 0.

## What is deliberately absent

- stochastic correlated-decoder shots: 0
- correlated-route logical failures: none observed
- acceptance salt or seed: absent
- candidate pass/fail decision: absent
- hardware decoder deadline or production-runtime claim: absent

The all-zero syndrome API sanity check is deterministic and contains no sampled detector or logical outcome.

## Post-freeze gate

After this exact packet is committed and publicly discussed, a new salt will be bound to that publication. Exactly 102,400 shots per basis will be decoded with correlations enabled. Both strict upper bounds must be at most 1%; otherwise the score is zero. Same-host batch timing will be reported but cannot stand in for a hardware deadline.

## Claim boundary

This is a no-outcome decoder preregistration. It is not an accepted B2 improvement, scalable #023 memory, hardware result, production decoder, threshold result, or B7 resource credit.

Formal checks: **24/24**. Run ID: `80075f1e11637e8696afe1915e4bff6a1675c3185b05cfae316486df33a24665`.

Structural references: [PyMatching correlation-aware decoding](https://github.com/oscarhiggott/PyMatching/blob/master/src/pymatching/matching.py); [Stim detector-error-model separators](https://github.com/quantumlib/Stim/blob/main/doc/file_format_dem_detector_error_model.md).
