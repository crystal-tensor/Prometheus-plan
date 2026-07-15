# B4/B8 R170 Near-Tie Complete-Candidate Replay

- Status: `new_input_candidate_replay_complete`
- Classification: `new_input_candidate_replay_complete`
- Profiles / replays: `3` / `192`
- Yielded complete candidates: `576`
- Source-return matches: `192` / `192`
- Payload hash: `1af733839bbd9e0617256f11781c4721582531ddd92a96535a7a5dc46c2fff51`

## Research Question

Does a target-compatible OpenQASM 3 interaction graph with near-tied candidates expose arithmetic-policy instability?

## Method

R170 runs the hash-bound candidate instrumentation on a five-active-qubit target-compatible tree input over FakeNairobiV2. The design preflight identified a one-ULP source-score gap between the best two candidates for this graph family. The replay retains every complete VF2 candidate and applies source binary64, compensated `math.fsum`, exact retained-binary64 leaves, and 1-ULP tie-aware selection without changing the search traversal.

## Result

Across `3` profiles and `192` calls, `576` candidates were yielded, source-return validation matched `192/192`, and policy-change counts were `{'source_f64': 0, 'compensated_fsum': 192, 'exact_binary64_leaf': 192, 'tie_aware_1ulp': 192}`.

## Claim Boundary

This is one near-tie target-compatible input candidate-level result. It does not establish cross-input generality, a production mapping change, an alternate search path, a confirmed Qiskit bug, hardware relevance, route advantage, quantum advantage, BQP separation, solved B4/B8/B10, or new credit.
