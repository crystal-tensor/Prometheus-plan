# B2/B7/#023 8-bit Micro Blossom admission freeze v1

## Question

Can an 8-bit fixed-point, correlation-preserving window graph pass a fresh exact-semantic holdout and expose a bounded controller update payload before any Micro Blossom latency or resource credit is claimed?

## Why this route

The public correction-vector experiment moved correction application and residual checking inside the frozen line, but the correlated matching call still missed the one-microsecond p99 gate. Two post-outcome route-selection diagnostics now close the obvious interface shortcuts: zero or single-edge caching covers only `4.97%/4.95%` of X/Z windows, and a size-one `decode_batch` call still records p99 `4.035/4.014 µs` per committed layer with `59.84%/57.11%` deadline misses.

The maintained Micro Blossom source instead exposes a real architecture boundary: arbitrary static graphs, unsigned dynamic edge-weight storage, and external weight loading. Its published latency is not imported as this project's result. The frozen experiment tests only whether the present graph and correlated semantics can be admitted to an 8-bit controller representation.

## Frozen representation

- Each decomposed error probability `p` becomes `q=max(1, round(16*log((1-p)/p)))` and `p_q=1/(1+exp(q/16))`.
- `q` must fit unsigned 8-bit storage.
- All graph endpoints, detector/observable correction maps, decomposed correlation groups, 18-round windows, 6-round commits, and 12-round look-ahead remain fixed.
- X and Z each have three static graph classes; the 630-vertex, 2,973-edge steady graph repeats in `162/164` windows.
- PyMatching 2.4.0 caps correlation-conditioned probability at `0.5`, so second-pass implied weights are nonnegative and only lower affected edges. This is compatible with an unsigned dynamic-weight interface, but no RTL implementation is claimed.

## Allowed preflight

The preflight reconstructs all 328 real window graphs and uses only all-zero syndromes. It observes zero fresh stochastic samples and zero fresh nonzero predictions.

- X: `164/164` topologies and output maps match; quantized group weights span `86..154`; the steady relation table has 2,973 causal keys and 15,610 directed relations.
- Z: `164/164` topologies and output maps match; quantized group weights span `82..154`; the same steady relation-table geometry is retained.
- Both all-zero reference and candidate paths return a zero logical frame with zero commit and final residuals.

## Fresh holdout and veto

After this freeze is public and its Discussion exists, the runner derives separate X/Z uint64 seeds from the public commit, Discussion number, namespace, and basis. It samples 1,024 new 1,000-round shots per basis.

The 8-bit candidate receives no geometry or controller-payload credit unless, in both bases:

1. all `1024/1024` candidate frames equal the unquantized online reference;
2. all `1024/1024` online-reference frames equal the full-block correlated reference;
3. every committed and final residual is zero;
4. all 164 window topologies and correction maps remain exact; and
5. every quantized group weight fits eight unsigned bits.

Only after that veto does the run report first-pass selected edges, unique potentially affected correlation edges, and the upper-bound payload encoded as a 12-bit edge index plus an 8-bit replacement weight.

## Claim boundary

An admission pass is not generated RTL, cycle-accurate execution, FPGA execution, timing closure, LUT/BRAM evidence, or a decoder-deadline pass. The existing p99 `<=1 µs` and miss-fraction `<=1%` gates remain open. Full B2, scalable #023 memory, and B7 resource credit remain false/zero regardless of this result.

Protocol: `benchmarks/B2_B7_P023_d6_microblossom_admission_v1.json`  
Runner: `tools/b2_b7_p023_d6_microblossom_admission.py`

