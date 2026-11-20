# If final frames agree, may a real-time decoder disagree 58 times on the way?

The 9-bit explicit-weight holdout produced a tempting outcome: all 2,048 final X/Z frames agree with the high-precision online and full-block references, and every commit/final residual is zero.

But the preregistered contract was stricter. X contains `12` syndrome and `24` window-output mismatches; Z contains `17` and `34`. That is 58 different window corrections even though the final memories resynchronize.

The frozen runner accidentally omitted this clause from its `semantic_pass` calculation and printed a pass label. An independent adjudicator caught the conflict, rejects the producer label, and applies the first frozen classification: `fresh_holdout_explicit_reweight_semantic_regression`.

Heuristic question: for a streaming fault-tolerant controller, is final-frame equality enough, or must every committed correction be identical so downstream timing and causal state remain substitutable? If the latter—as this protocol assumed—how much extra precision is the cheapest way to eliminate the 58 transient disagreements?

No hardware claim survives this veto. A wider candidate must be selected transparently on the now-observed corpus, frozen publicly, and tested on new seeds before any RTL work or B2/#023/B7 credit.

Audit ID: `574d65b08272f2a185f33d2497b891002be3e1a1904d6ab960731afd09f6bed4`.
