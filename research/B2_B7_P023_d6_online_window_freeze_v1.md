# B2/B7/#023 Distance-6 Online Window Freeze v1

Last updated: 2026-11-20

Status: **preregistered before every online-window prediction and latency outcome**

## Heuristic question

Can a decoder be called real time when its median keeps pace but its tail misses the next syndrome?

The accepted 71-active-qubit distance-6 memory result used offline 1,000-round block decoding. This freeze replaces that execution shape with sequential overlapping recovery before observing any new window prediction, residual syndrome, socket-path latency, p99, or deadline miss.

## Frozen online algorithm

- distance `d=6`;
- detection window `3d=18` syndrome layers;
- commit stride `d=6` layers and future buffer `2d=12` layers;
- independent-MWPM control and two-pass correlated-matching primary arm;
- only correction components touching the oldest six layers are committed;
- their detector endpoints and logical-frame flips are propagated into later windows;
- the final window consumes and commits every remaining layer.

This is the overlapping-recovery construction: buffer corrections remain tentative, while committed corrections alter the syndromes seen by later windows.

## Frozen semantic gate

For both X and Z, the correlated online arm must:

1. reproduce the exact frozen detector corpus;
2. leave every committed region and the final syndrome with zero residual;
3. equal all `1,024/1,024` already frozen full-block correlated predictions.

Anything less fails the online software proxy even if it is fast.

## Frozen timing gate

The timed response begins before detector-bit packing and ends only after logical-frame feedback acknowledgement. It includes an in-process Unix-socket kernel path, decoding, correction propagation, and reverse feedback. Sampling and graph construction are excluded.

The correlated arm must pass in both bases:

- nearest-rank p99 end-to-end time `<=1 microsecond` per committed layer;
- deadline-miss fraction `<=1%`;
- the semantic gate above.

There are `128` timed shots per basis and decoder, one outcome-bearing warmup after publication, and `164` windows per shot. Raw total nanoseconds will be retained as base64 little-endian `uint64` values for arithmetic audit.

## Zero-outcome structural preflight

Before publication, the runner observed no stochastic shot and no online prediction outcome. It compiled the real DEMs and decoded only the all-zero syndrome:

| basis | detectors | windows | max nodes | max edges | components | all-zero independent/correlated |
|---|---:|---:|---:|---:|---:|---|
| X | 35,001 | 164 | 788 | 3,730 | 1,372,487 | 0 / 0 |
| Z | 34,999 | 164 | 787 | 3,725 | 1,372,431 | 0 / 0 |

The final window spans at most `4d-1=23` layers, so graph depth remains `O(d)` rather than growing with the 1,000-round experiment.

## Hard boundary

Even a pass remains a host-local online software proxy. The transport is a synchronous same-process socketpair, not a QPU, measurement stack, controller, asynchronous queue, cryogenic interconnect, or hardware feedback path. Hardware deadline, full B2, scalable #023 memory, and B7 resource credit therefore remain closed regardless of the result.

## Execution order

1. publish the protocol and runner in a public commit;
2. publish the heuristic Discussion and record its number;
3. execute only with both public identifiers;
4. retain failures and boundary violations rather than retuning the frozen window or thresholds.

Sources: [parallel window decoding](https://arxiv.org/abs/2209.08552); [sandwich/sliding-window decoder](https://doi.org/10.1103/PRXQuantum.4.040344); [1 microsecond per-round context](https://www.nature.com/articles/s41467-025-66773-x); [Willow real-time context](https://www.nature.com/articles/s41586-024-08449-y).
