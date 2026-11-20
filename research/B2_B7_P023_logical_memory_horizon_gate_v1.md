# #021/B7 · #022/B2 · #023 Logical-Memory Horizon Gate v1

**Decision:** `logical_memory_horizon_gate_ready_short_memory_calibration_only_p023_b2_b7_credit_closed`.

## Can seven rounds of memory justify the word scalable?

No. The local B2 baseline contains 30 Stim/PyMatching configurations, 3,000 shots each, and only 3, 5, or 7 correction rounds. This packet preserves those rows as useful short-memory calibration, but gives them zero direct evidence at the frozen 10, 100, 1,000, and 1,000,000-round horizons.

The stationary independent-flip projection is calculated only to expose how quickly a short-run upper bound compounds. It cannot upgrade a projection into observed lifetime evidence, and it earns no #023, B2, or B7 credit.

## Evidence ladder

| Level | Evidence | Credit |
|---|---|---|
| local_simulator_calibration | B2 Stim/PyMatching baseline | short-memory calibration only |
| hardware_memory_denominator | Willow and IBM primary reports | external denominator only; not locally reproduced |
| low_overhead_protocol_denominator | qLDPC Nature protocol | external protocol/simulation denominator only |
| scalable_memory_acceptance | frozen P023 direct-horizon gate | closed |
| B7 resource credit | B2/B7 calibrated dependency gate | zero |

## Frozen horizon result

At the shortest requested horizon (10 rounds, total failure target 1%), `3` paired X/Z settings pass only the diagnostic projection and `0` pass direct evidence. All longer direct horizons also have zero passes because the longest local source run is seven rounds.

| Requirement | Result |
|---|---|
| Direct X and Z evidence at 1,000 rounds | fail |
| Direct X and Z evidence at 1,000,000 rounds | fail |
| Same-condition candidate-code gain >=25% | not executed |
| Decoder timing plus drift/correlation stress | absent locally |
| Existing B7 calibrated-credit gate | closed |
| #023 scalable-memory readiness | false |
| B2 low-overhead claim credit | false |
| B7 memory-derived resource credit | 0 |

## How expensive is honest resolution?

A zero-failure direct experiment needs at least 381 shots before a two-sided Wilson 95% upper bound alone falls below 1%; a 0.1% target needs 3,838. At one million rounds, even the distance-3 local circuit (26 physical qubits) therefore implies at least `9,906,000,000` physical-qubit-cycles per basis, or `19,812,000,000` across X and Z, before decoder, reset, drift, leakage, or layout overhead is added.

This is a planning lower bound, not a hardware runtime forecast.

## Why the external denominators matter

The Willow hardware report supplies a below-threshold surface-code memory, real-time decoding, and runs up to one million cycles, while also exposing correlated-error floors. The 2024 qLDPC protocol supplies a low-overhead multi-logical-qubit memory target under an explicit circuit-noise assumption. The October 2026 IBM preprint reports cloud-hardware distance suppression but also a weakening distance advantage in longer memories. These are denominator classes, not interchangeable rows and not local reproductions.

## Next falsifier

Build one source-bound memory-run manifest that records basis, distance, physical qubits, exact rounds, shots, failures, decoder, latency/throughput, calibration window, drift/leakage treatment, and immutable trace hashes. The next executable gate must first reproduce both X and Z at 1,000 rounds; only then may a 1,000,000-round plan or a candidate-code overhead comparison be opened.

## Reproducibility and claim boundary

Formal checks pass `17/17` over four hash-bound local inputs and three normalized text captures. The captures preserve official-origin semantics through a text relay but make no raw-publisher-byte identity claim.

No new code, threshold, scalable-memory result, hardware result, production decoder, B7 resource credit, or quantum-advantage claim is made.

## Primary sources

- [Quantum error correction below the surface code threshold](https://www.nature.com/articles/s41586-024-08449-y)
- [High-threshold and low-overhead fault-tolerant quantum memory](https://www.nature.com/articles/s41586-024-07107-7)
- [Logical error suppression on a cloud-accessible IBM processor](https://arxiv.org/abs/2610.23840)
