# B2/B7/#023 Distance-6 Latency Attribution v1

As of 2026-11-20. Scope is exactly #021/B7, #022/B2, and #023.

## Heuristic question

What if removing transport buys only nine percent—and the clock still loses?

Public freeze: `7d0e19d98b0d9d274f4431d6c9e42c4ab90f3623` and Discussion #331.

| basis | matching p99 us/layer | direct p99 | sync p99 | direct semantic rows | first-stage passes (match/direct/sync) |
|---|---:|---:|---:|---:|---|
| X | 4.597167 | 8.291667 | 9.173667 | 1024/1024 | False/False/False |
| Z | 4.673667 | 8.368000 | 9.055500 | 1024/1024 | False/False/False |

Classification: **matching_kernel_tail_bottleneck**.

The matching call alone has X/Z median `1.924/1.875 µs` and p99 `4.597/4.674 µs` per committed layer, missing the one-microsecond window in `92.71%/91.61%` of observations. It consumes `51.78%/51.89%` of direct-path time by summed nanoseconds. Edge-to-component mapping is the next visible boundary at p99 `2.660/2.653 µs` and roughly `50.41%/47.27%` deadline misses.

## Kaggle-inspired score boundary

The semantic veto is `True`: direct X/Z each reproduce `1024/1024` frozen predictions, the paired sync subsets each reproduce `128/128`, both paths agree on all timed rows, and every committed/final residual remains zero. Only after that pass is the X/Z sync-to-direct p99 geometric mean reported: `1.094198`. Removing packing/socket/feedback therefore buys only about nine percent at p99; the relative number cannot override the absolute one-microsecond p99 and one-percent miss gates.

## Boundary

Both paths remain same-host Python measurements. Hardware deadline, full B2, scalable #023 memory, and B7 resource credit remain false.

Formal checks: **13/13**. The independent auditor passes **19/19** after regenerating 8 source chunks, replaying 2,304 prediction rows, and recomputing 22 raw timing vectors; the subprocess replay passes **12/12** and rebuilds the audit byte for byte. Evidence ID: `5aabec7f51db5fcc3d3df81d8bbc1073aff7f8fb385f8fef4d0dbab85434c5e4`.

## Next gate

Preregister a native or parallel window kernel that first targets correlated matching while exposing edge-to-component mapping separately. Retain exact window semantics, raw per-window tails, and the absolute deadline; batching alone must not be allowed to recreate the already rejected offline-throughput proxy.
