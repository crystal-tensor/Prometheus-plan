# B2/B7/#023 Distance-6 Public Fault-Vector Freeze v1

Last updated: 2026-11-20

Status: **preregistered before every nonzero-corpus public-candidate prediction and timing outcome**

## Heuristic question

What if the decoder returned the correction instead of the path?

The prior sparse-edge experiment improved end-to-end p99 by `1.156×`, but the private C++ matching call remained the first failure. This freeze replaces neither decoder nor graph. It changes the meaning of the graph's fault IDs so the supported public `Matching.decode` API returns detector and observable correction bits directly.

## Known structural evidence

For all 164 X windows and all 164 Z windows, the candidate graph has exactly the same normalized edge endpoints, weights, and error probabilities as the frozen baseline. Only fault-ID payloads differ.

The encoding produces `40,870` X and `40,868` Z output bits across all windows, with a maximum of `789/788` bits in one window. Every all-zero decode returns an all-zero vector. No nonzero candidate prediction, candidate timing vector, speedup, tail verdict, or classification has been observed.

## Frozen candidate

Each committed component's detector and observable support is assigned contiguous fault IDs. Public correlated `Matching.decode` then returns their parity vector, which is applied to the global correction and logical frame with vectorized XOR.

The sparse private edge-return path remains the paired baseline. Both paths consume identical syndrome bytes and alternate first position across timed shots. Shot batching is forbidden.

## Frozen semantic veto

- public candidate X/Z must each equal all `1,024/1,024` frozen full-block predictions;
- sparse baseline X/Z must each equal all `128/128` timed predictions;
- both paths must agree on every timed row;
- committed and final residual failures must remain zero;
- all 328 graph signatures and output maps must verify exactly.

## Frozen timing and classification

Candidate vectors separate public fault-vector decode, vectorized correction application, commit-residual checking, and total response. The first stage failing p99 `<=1 µs` per committed layer and misses `<=1%` sets the classification.

After correctness, the X/Z sparse-baseline-p99/public-candidate-p99 ratios receive a geometric mean. Relative improvement cannot waive the absolute line.

## Hard boundary

The candidate removes the private-API dependency, but it is still same-host Python software. Hardware deadline, full B2, scalable #023 memory, and B7 credit remain false regardless of outcome.
