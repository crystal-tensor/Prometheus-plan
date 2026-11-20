# B2/B7/#023 Qubit-Index Invariance Audit v1

As of 2026-11-20. Scope is exactly #021/B7, #022/B2, and #023.

## Heuristic question

If the physical circuit is unchanged, should replacing sparse qubit identifiers with 0..96 earn a resource improvement? The answer must be no; otherwise the score rewards serialization rather than hardware.

## Finding

The strict distance-7 Stim circuits report `num_qubits=118`, but only 97 distinct qubit identifiers occur in operational instructions. The other 21 positions are holes in the identifier span. Therefore the previous `118×1,000` resource proxy was label-sensitive and is regraded; its correctness evidence is unchanged.

| basis | index span | active operational qubits | holes | old cost | corrected cost | canonical circuit | DEM | 8,192-shot replay |
|---|---:|---:|---:|---:|---:|---|---|---|
| X | 118 | 97 | 21 | 118,000 | 97,000 | exact | exact | exact |
| Z | 118 | 97 | 21 | 118,000 | 97,000 | exact | exact | exact |

Compaction changes raw circuit bytes and raw-byte-derived seeds, but the canonical compact circuit, detector error model, fixed-seed detector/observable samples, MWPM predictions, and failure vectors are exact matches in both bases.

## Corrected baseline

The verified reference is now `Q_active×H = 97×1,000 = 97,000` active-qubit-rounds per basis and 194,000 for the X/Z pair. Its normalized score remains 1.0.

A relabeled copy would appear to score 1.216494845 under the old label-sensitive count, but correctly scores 1.0 and earns no B2 improvement under v2.

For a symmetric 1,000-round candidate, `Score_QEC>=1.25` now requires at most 77 active operational qubits, plus strict X/Z correctness and no weakened assumptions.

## Verifier rule v2

1. Count distinct qubits targeted by operational instructions; ignore QUBIT_COORDS-only identifiers.
2. Canonically order active qubits by unique QUBIT_COORDS tuples before resource hashing and challenge binding; reject missing or duplicate bindings.
3. Treat `circuit.num_qubits` only as an index-span diagnostic.
4. Give index-only transformations score 1.0, never resource credit.
5. Keep correctness as a hard gate before the corrected cost score.

## Claim boundary

This corrects the resource baseline; it does not change the strict 1,000-round logical-error result. It does not establish a new code, B2 improvement, scalable #023 memory, hardware performance, or B7 credit.

Formal checks: **30/30**. Run ID: `8e71bd695f1abd895ce369740fb9a25a185f56876075d6434cdafbf1f794f6b5`.

## Next falsifier

Freeze and strictly verify a same-condition candidate before salt reveal; a symmetric 1,000-round candidate needs at most 77 active operational qubits to reach Score_QEC>=1.25.
