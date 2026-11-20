# B2/B7/#023 Distance-6 Sparse Kernel v1

As of 2026-11-20. Scope is exactly #021/B7, #022/B2, and #023.

## Heuristic question

If the decoder already lives in C++, is Python asking it the wrong question?

Public freeze: `4228242a655a89b764c176457eba4a687cc9c15d` and Discussion #333.

| basis | C++ matching p99 us/layer | preindexed mapping p99 | candidate total p99 | baseline total p99 | candidate semantic rows |
|---|---:|---:|---:|---:|---:|
| X | 4.409667 | 1.666667 | 7.284833 | 8.479167 | 1024/1024 |
| Z | 4.618167 | 1.680500 | 7.576333 | 8.701333 | 1024/1024 |

Classification: **cpp_correlated_matching_tail_bottleneck**.

## Verification before speed

The semantic veto is `True`. The X/Z baseline-to-candidate p99 geometric mean is `1.156192`; it cannot waive the absolute tail gate.

## Boundary

The candidate uses a version-locked private PyMatching C++ entry point. It is diagnostic only. Hardware deadline, full B2, scalable #023 memory, and B7 credit remain false.

Formal checks: **14/14**. Evidence ID: `e25cd66cc162fedb319eff534915a7ac961787f5b7b8cca17f557c4c708f5c8a`.

## Independent reproduction

An auditor that does not import the sparse-kernel producer passes **21/21** checks. It regenerates all 8 frozen source chunks, independently reparses both detector error models, rebuilds 164 windows and complete edge indexes per basis, replays 2,048 candidate plus 256 timed-baseline prediction rows, and recomputes 18 raw timing vectors. A fresh subprocess replay passes **12/12** checks and recreates the audit artifact byte for byte.

## Next gate

Move beyond wrapper tuning: preregister a maintained native or alternate decoder kernel with identical window semantics.
