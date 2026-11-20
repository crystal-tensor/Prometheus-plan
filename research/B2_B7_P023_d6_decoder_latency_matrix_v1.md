# B2/B7/#023 Distance-6 Decoder Latency Matrix v1

As of 2026-11-20. Scope is exactly #021/B7, #022/B2, and #023.

## Heuristic question

Does a correlation-aware decoder still keep pace when the 256-shot batch advantage is removed?

Public freeze: `6882dfeed3c48623585d5676dce91d7644b6fc41` and Discussion #327.

| basis | decoder | batch | median s | median us/round | memory-rounds/s | correlated / independent |
|---|---|---:|---:|---:|---:|---:|
| X | independent_mwpm | 1 | 0.150433 | 0.146907 | 6807021 | 1.000x |
| X | independent_mwpm | 4 | 0.145802 | 0.142384 | 7023245 | 1.000x |
| X | independent_mwpm | 16 | 0.148135 | 0.144663 | 6912608 | 1.000x |
| X | independent_mwpm | 64 | 0.144865 | 0.141470 | 7068654 | 1.000x |
| X | independent_mwpm | 256 | 0.144967 | 0.141570 | 7063664 | 1.000x |
| X | two_pass_correlated_matching | 1 | 0.533355 | 0.520854 | 1919922 | 3.545x |
| X | two_pass_correlated_matching | 4 | 0.529273 | 0.516868 | 1934730 | 3.630x |
| X | two_pass_correlated_matching | 16 | 0.527031 | 0.514679 | 1942960 | 3.558x |
| X | two_pass_correlated_matching | 64 | 0.530751 | 0.518311 | 1929342 | 3.664x |
| X | two_pass_correlated_matching | 256 | 0.525988 | 0.513660 | 1946812 | 3.628x |
| Z | independent_mwpm | 1 | 0.149295 | 0.145795 | 6858925 | 1.000x |
| Z | independent_mwpm | 4 | 0.145051 | 0.141651 | 7059580 | 1.000x |
| Z | independent_mwpm | 16 | 0.143169 | 0.139814 | 7152363 | 1.000x |
| Z | independent_mwpm | 64 | 0.143664 | 0.140296 | 7127763 | 1.000x |
| Z | independent_mwpm | 256 | 0.142802 | 0.139456 | 7170745 | 1.000x |
| Z | two_pass_correlated_matching | 1 | 0.528205 | 0.515826 | 1938640 | 3.538x |
| Z | two_pass_correlated_matching | 4 | 0.519905 | 0.507720 | 1969591 | 3.584x |
| Z | two_pass_correlated_matching | 16 | 0.519402 | 0.507229 | 1971498 | 3.628x |
| Z | two_pass_correlated_matching | 64 | 0.521157 | 0.508943 | 1964858 | 3.628x |
| Z | two_pass_correlated_matching | 256 | 0.524873 | 0.512572 | 1950946 | 3.676x |

Batch-1 software backlog proxy pass: **True**. Batch-256 throughput proxy pass: **True**. The declared line is 1 microsecond per syndrome round.

## Boundary

This is an offline host-local block-decoding proxy. It excludes communication, control, feedback, online O(d) windowing, and tail response time. Hardware decoder deadline passed remains **False**; full B2, #023, and B7 remain closed.

Formal checks: **13/13**. Deterministic ID: `d818abd1ed0f73653fabee058d319f35338da6dfe2dc84f3659828e5ed415b2c`. Timing evidence ID: `cd59350da60f3d17b59f36cdaf300c2b2a62923cdbdb73f14e9e054c578c99b5`.

## Next gate

Implement and time an online O(d) sliding-window decoder with communication, control, feedback, and tail latency before any hardware deadline, full B2, #023, or B7 claim.
