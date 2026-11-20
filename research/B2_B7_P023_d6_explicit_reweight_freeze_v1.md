# B2/B7/#023 explicit 9-bit reweight freeze v1

## Question

Can the complete correlated online decoder, including every second-pass implied weight, be represented explicitly by one unsigned 9-bit even-integer grid without changing any fresh X/Z logical answer?

## Why the earlier 8-bit label is not enough

The prior public result remains valid for what it actually tested: quantizing each detector-error mechanism to an 8-bit log-likelihood grid preserved every frozen software answer. A pinned-source audit found that this did **not** make PyMatching's merged graph edges or correlation-conditioned implied weights 8-bit. Because those values remain non-integral, PyMatching 2.4.0 rescales them into its wide internal integer domain before decoding.

The previous `12-bit edge index + 8-bit weight` payload was therefore an upper-bound diagnostic, not a realized dynamic-weight encoding. This freeze supersedes that payload with an explicit 9-bit representation; it does not retract the earlier semantic equality result or change its zero hardware credit.

## Source-faithful explicit representation

- Each merged base edge weight `w` becomes `h=round_C++(16*w)` and stored even weight `W=2*h`.
- Joint and marginal correlation probabilities are rebuilt from the decomposed DEM with PyMatching's Bernoulli-XOR rule.
- Each replacement uses `p'=min(0.5,joint/marginal)`, `h'=round_C++(16*log((1-p')/p'))`, and `W'=2*h'`.
- Only a strictly lower replacement is applied, exactly matching the pinned `apply_reweights` rule.
- A 50-line pybind-only audit adapter inserts the already-computed integer rules. It changes no matching, discretization, reweight, or decode algorithm.

The allowed all-zero preflight reconstructs all 328 real windows. X has base even range `144..264`; Z has `142..264`; both have implied range `0..164`. Every value is even and fits unsigned 9-bit storage. Each basis has three graph images and three rule images, with the steady class repeated in `162/164` windows. All 328 all-zero window outputs agree and every residual remains zero.

## The newly explicit Micro Blossom blocker

The pinned Micro Blossom example adapter requires even weights, but its dynamic route is not functional at the pinned commit. `LoadWeightsExternal` is reserved, while `Edge.scala` still marks dynamic edge-weight update as `TODO`, external write ports are commented, `Instruction.scala` lacks an operational generator, and the embedded solver rejects nonempty `dynamic_weights`.

This freeze therefore tests a software semantic bridge only. A pass cannot be described as Micro Blossom execution.

## Fresh holdout and veto

After this freeze and its Discussion are public, the runner derives independent X/Z seeds from the public commit, Discussion number, namespace, and basis. It samples 1,024 new 1,000-round shots per basis.

The candidate receives no representation or payload credit unless, in both bases:

1. all `1024/1024` explicit-integer candidate frames equal the high-precision online reference;
2. all `1024/1024` online-reference frames equal the full-block correlated reference;
3. all `167936/167936` window syndromes and outputs agree;
4. every committed and final residual is zero; and
5. every base and implied stored weight is even and fits unsigned 9-bit storage.

Only after that veto does the result report the number of actually lowered replacement edges and a raw `12-bit index + 9-bit weight` payload.

## Claim boundary

No candidate Micro Blossom RTL has been generated or run. There is no cycle-accurate execution, FPGA execution, timing closure, LUT/BRAM evidence, or decoder-deadline pass. The existing p99 `<=1 µs` and miss-fraction `<=1%` gates remain open. Full B2, scalable #023 memory, and B7 resource credit remain false/false/zero.

Protocol: `benchmarks/B2_B7_P023_d6_explicit_reweight_v1.json`  
Runner: `tools/b2_b7_p023_d6_explicit_reweight.py`  
Adapter patch: `tools/patches/pymatching_v2.4.0_explicit_rules.patch`
