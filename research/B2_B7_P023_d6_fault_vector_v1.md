# B2/B7/#023 Distance-6 Public Fault Vector v1

As of 2026-11-20. Scope is exactly #021/B7, #022/B2, and #023.

## Heuristic question

What if the decoder returned the correction instead of the path?

Public freeze: `b500f8394d7288339e5129834cccf9aa85a419d7` and Discussion #335.

| basis | public decode p99 us/layer | vector apply p99 | candidate total p99 | sparse baseline p99 | candidate semantic rows |
|---|---:|---:|---:|---:|---:|
| X | 6.951500 | 0.451500 | 8.076500 | 8.076333 | 1024/1024 |
| Z | 6.305667 | 0.861167 | 8.250000 | 8.993000 | 1024/1024 |

Classification: **public_fault_vector_decode_tail_bottleneck**.

## Verification before speed

The semantic veto is `True`. The X/Z sparse-baseline-to-public-candidate p99 geometric mean is `1.044049`; it cannot waive the absolute tail gate.

## Boundary

The candidate uses the supported public PyMatching API and graph-equivalent correction-bit fault IDs, but it remains a same-host software diagnostic. Hardware deadline, full B2, scalable #023 memory, and B7 credit remain false.

Formal checks: **15/15**. Evidence ID: `8c39e11b5b2be6eb2c1731038e08535d23e4a4e6d64b3aea2b21e86f8ef328c4`.

## Independent reproduction

An auditor that does not import the fault-vector producer passes **20/20** checks. It regenerates all 8 frozen source chunks, reparses both detector error models, rebuilds all 328 graph-equivalent correction-bit matchers and output maps, replays 2,048 candidate plus 256 timed-baseline prediction rows, and recomputes 16 raw timing vectors. A fresh subprocess replay passes **12/12** checks and recreates the audit artifact byte for byte.

## Next gate

Preregister an alternate maintained matching kernel or controller-native implementation under the identical graph and single-stream contract.

