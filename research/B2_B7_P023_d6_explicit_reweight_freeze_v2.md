# B2/B7/#023 explicit 16-bit reweight freeze v2

## Question

Can a preregistered unsigned 16-bit even-weight decoder, selected only after the public 9-bit regression, reproduce every fresh X/Z window syndrome, window output, final frame, and residual exactly?

## Why this is a new experiment

The public v1 holdout preserved all `2048/2048` final X/Z frames and every commit/final residual, but it failed the frozen streaming contract: X had `12` syndrome and `24` output mismatches, while Z had `17` syndrome and `34` output mismatches. The producer's pass label was rejected because its `semantic_pass` accidentally omitted the all-window clause.

V2 does not reinterpret that failure. It copies the decoder into a new runner and makes exact window syndrome and output equality part of the executable semantic veto. A negative fresh result is still emitted and classified instead of being lost as a formal-check exception.

## Disclosed post-outcome route selection

Every scale below reused the already-public failed v1 corpus. These rows can choose a later candidate but are not acceptance evidence.

| half-weight scale | stored width | X syndrome/output mismatches | Z syndrome/output mismatches |
|---:|---:|---:|---:|
| 16 | 9-bit | 12 / 24 | 17 / 34 |
| 24 | 9-bit | 4 / 8 | 7 / 14 |
| 30 | 9-bit | 1 / 2 | 1 / 2 |
| 31 | 9-bit | 3 / 6 | 4 / 8 |
| 32 | 10-bit | 3 / 6 | 5 / 10 |
| 48 | 10-bit | 2 / 4 | 6 / 12 |
| 1024 | 15-bit | 0 / 0 | 1 / 2 |
| 2048 | 16-bit | 0 / 0 | 0 / 0 |
| 65536 | 21-bit | not tested | 0 / 0 |

The selected candidate is scale `2048`, the first tested power of two above `1024` that clears both bases. This rule avoids selecting an arbitrary lucky integer after inspecting outcomes. The committed scout result is explicitly marked post-outcome and binds the public v1 corpus hashes.

## Zero-sample preflight

The preflight reconstructs all `328` real windows without sampling a fresh stochastic shot. Both bases expose three graph images and three rule images, with the steady image repeated in `162/164` windows. X base weights span `18348..33706`; Z spans `18068..33706`; implied weights span `0..20966`. All are even and fit unsigned 16-bit storage.

All `164/164` all-zero window syndromes and outputs agree in each basis, both frames are zero, every residual is zero, and the pinned explicit-rule adapter is active. Fresh stochastic samples observed: `0`.

## Fresh holdout and veto

Only after this commit and its GitHub Discussion are public may the runner derive independent X/Z seeds from the public commit, Discussion number, v2 namespace, and basis. It then samples `1024` new 1,000-round shots per basis.

The candidate passes only if, in both bases:

1. candidate, online-reference, and full-block final frames agree on `1024/1024` shots;
2. all `167936/167936` window syndromes agree;
3. all `167936/167936` window outputs agree;
4. every commit and final residual is zero; and
5. every base and implied stored weight is even and fits unsigned 16-bit storage.

Only after this verification veto may the result discuss the actual strict-lowering payload, encoded as `12-bit edge index + 16-bit weight`. X and Z are judged separately; no average can hide a failed basis.

## Claim boundary

The pinned Micro Blossom dynamic-weight write path is still TODO/commented. No candidate RTL, cycle-accurate execution, FPGA execution, timing closure, LUT/BRAM result, decoder-deadline pass, full B2 credit, scalable #023 claim, or B7 resource credit follows from this freeze. The p99 `<=1 us` and miss-fraction `<=1%` gates remain mandatory and unmeasured.

Protocol: `benchmarks/B2_B7_P023_d6_explicit_reweight_v2.json`  
Runner: `tools/b2_b7_p023_d6_explicit_reweight_v2.py`  
Route scout: `tools/b2_b7_p023_d6_explicit_reweight_scale_scout.py`  
Selected-scout result: `results/B2_B7_P023_d6_explicit_reweight_scale_scout_v1.json`
