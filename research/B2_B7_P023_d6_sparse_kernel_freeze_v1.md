# B2/B7/#023 Distance-6 Sparse Kernel Freeze v1

Last updated: 2026-11-20

Status: **preregistered before every nonzero-corpus candidate prediction and candidate timing outcome**

## Heuristic question

If the decoder already lives in C++, is Python asking it the wrong question?

The prior attribution localizes the first tail failure to the correlated matching call and the second visible pressure to per-edge component lookup. This freeze changes neither graph nor decoding decision. It changes only how a syndrome enters the same PyMatching graph and how returned edges find their committed components.

## Known structural evidence

Across 164 windows per basis, the X graphs contain `488,257` merged edges and the Z graphs `488,247`. Exactly `169,918` X edges and `169,908` Z edges carry one fault ID; every other edge carries none, and no edge carries more than one. This graph-only fact was observed before the freeze and makes an exact preindex possible.

No sparse-preindexed prediction on the nonzero frozen corpus, timing vector, speedup, tail verdict, or classification has been observed.

## Frozen candidate

The baseline retains the public dense-syndrome `decode_to_edges_array` call and a `get_edge_data` query for each selected edge.

The candidate:

1. extracts sparse detection-event indices with `numpy.flatnonzero`;
2. sends those indices to the same two-pass correlated C++ matching graph;
3. maps each returned normalized edge through a dictionary constructed before timing;
4. performs the unchanged correction propagation, logical-frame update, and residual checks.

The diagnostic uses PyMatching `2.4.0`'s private `_matching_graph.decode_to_edges_array` entry point. That is intentionally a hard boundary: even a pass is not a supported production integration.

## Frozen semantic veto

- candidate X/Z must each equal all `1,024/1,024` frozen full-block predictions;
- baseline X/Z must each equal all `128/128` timed predictions;
- both paths must agree on every timed row;
- committed and final residual failures must remain zero;
- every preindexed edge must reproduce its graph fault-ID mapping.

## Frozen timing and classification

Baseline and candidate alternate first position across 128 timed shots per basis. Candidate raw vectors separate detection-event extraction, C++ correlated matching, preindexed mapping, propagation, and total response.

After the semantic veto, the first failing stage sets the classification:

1. C++ correlated matching;
2. preindexed edge mapping;
3. candidate direct end-to-end;
4. otherwise the candidate host proxy passes.

Each stage retains p99 `<=1 µs` per committed layer and misses `<=1%`. The X/Z baseline-p99/candidate-p99 ratios receive a geometric mean only after correctness passes; relative improvement cannot waive the absolute gate.

## Hard boundary

This is a same-host, version-locked private-API diagnostic. Hardware deadline, full B2, scalable #023 memory, and B7 credit remain false regardless of the result.
