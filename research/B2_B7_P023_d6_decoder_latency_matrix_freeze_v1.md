# B2/B7/#023 Distance-6 Decoder Latency Matrix Freeze v1

As of 2026-11-20. Scope is exactly #021/B7, #022/B2, and #023.

## Heuristic question

Can the correlation-aware decoder still keep pace when its 256-shot batch advantage is removed?

## What is already known

The publicly verified distance-6 result is not hidden: the two-pass correlated decoder passed both strict X/Z correctness gates at 71 active qubits and earned a physical-memory score of `97/71 = 1.366197x`. Its 102,400-shot, batch-256 timing was about `4.15x` the independent-MWPM timing.

Those observations motivate this test; they are not treated as new or blinded.

## What is frozen before the new measurement

- exact corpus: the first four 256-shot chunks from each strict X/Z run, for 1,024 shots per basis;
- same detector corpus for independent MWPM and two-pass correlated matching;
- batch sizes: `1, 4, 16, 64, 256`;
- one warmup plus nine timed repetitions per basis/decoder/batch row;
- round-robin timing order, rotated each repetition and reversed on odd repetitions;
- graph construction and sampling excluded from timed regions;
- all source chunk hashes and every decoder prediction hash must reproduce;
- primary software backlog proxy: correlated matching at batch 1 must have median time `<=1 microsecond/round` in both X and Z.

The 1 microsecond/round line is grounded in published real-time decoder work, but it is only a host-local software proxy here.

## Hard boundary fixed in advance

`hardware_decoder_deadline_passed` is fixed to `false` regardless of the timing result. This runner decodes complete offline 1,000-round blocks and excludes communication, control, feedback, online `O(d)` windowing, and end-to-end tail latency. Full B2, scalable #023 memory, and B7 resource credit therefore remain closed.

## Post-publication execution rule

The runner refuses to execute without an explicit public freeze commit and Discussion number, and it verifies that its protocol and source bytes match that public commit.
