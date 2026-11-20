# B2/B7/#023 Distance-6 Latency Attribution Freeze v1

Last updated: 2026-11-20

Status: **preregistered before every direct-path and fine-phase timing outcome**

## Heuristic question

If removing transport does not save the clock, where is the missing microsecond hiding?

The online-window experiment already established an unusual split: all `4096/4096` frozen predictions survive bounded recovery with zero residual failures, yet correlated X/Z p99 latency is `9.035/9.375 µs` per committed layer and nearly every window misses the declared deadline. This freeze localizes that failure without changing the decoder, window, corpus, or acceptance line.

## What is already known

The public online result exposes only three coarse phases. In the correlated arms, decode-plus-commit has median/p99 `23.333/49.417 µs` per X window and `23.625/50.917 µs` per Z window. Those values are known before this freeze. No direct no-socket rerun or fine matching, mapping, propagation, or feedback vector has been observed.

## Frozen two-path ablation

- `sync_path`: unchanged detector packing, same-process Unix socket transport, correlated matching, correction propagation, and reverse feedback acknowledgement;
- `direct_path`: identical windows, detector bytes, matching objects, correction logic, and frame updates, but detector arrivals and feedback are passed directly without packing or sockets;
- first `128` shots per basis are timed in alternating mode order;
- the direct path also replays all `1,024` shots per basis for semantic equality;
- graph construction and syndrome sampling remain outside timing.

The direct path records raw `uint64` vectors for arrival delivery, syndrome materialization, matching, edge-to-component mapping, correction propagation/residual checking, direct feedback, and total response. Every phase must add exactly to its total.

## Frozen semantic veto

Timing receives no credit unless:

1. direct X and Z each equal all `1,024/1,024` frozen full-block predictions;
2. the sync rerun equals all `128/128` timed frozen predictions per basis;
3. both paths have zero committed-region and final residual failures;
4. both paths agree on every timed row.

## Frozen classification

After semantics pass, the first stage failing p99 `<=1 µs` per committed layer and misses `<=1%` in either basis determines the diagnosis:

1. correlated matching kernel;
2. Python window bookkeeping in direct end-to-end execution;
3. synchronous packing/socket/feedback transport;
4. otherwise, the same-host proxy is reconfirmed as passing.

Following the [Kaggle evaluation](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/overview/evaluation), correctness is a veto before cost improvement. Only after it passes will the run report X/Z `sync p99 / direct p99` ratios and their geometric mean. Relative acceleration never overrides the absolute deadline.

## Hard boundary

This remains a same-host Python attribution experiment. Even a direct-path pass is not a QPU/controller deadline. Hardware deadline, full B2, scalable #023 memory, and B7 resource credit remain false.
