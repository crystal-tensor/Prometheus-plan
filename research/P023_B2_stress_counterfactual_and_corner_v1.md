# #022/B2 and #023: why the 287-qubit path stopped, and what replaces it

Date: 2026-11-27

The 287-active-qubit d=12 circuit plus its nominal-model decoder is **rejected by the frozen million-round gate**. Its stressed X cell reached **6 failures in 256 completed trajectories**, already beyond the maximum of 3 in the full 1,024. Even if every remaining trajectory succeeded, this version could not earn the comparative credit. The remaining d=12 jobs were stopped; completed receipts are retained and unfinished cells do not get a result.

| Million-round cell | d=12 challenger | d=15 reference |
| --- | ---: | ---: |
| X nominal | 1/128 | 0/896 |
| X with paired readout errors | **6/256** | 2/896 |
| Z nominal | 1/128 | 0/896 |
| Z with paired readout errors | 2/256 | 0/896 |

The d=15 reference continued toward 1,024 shots per cell. The [joint audit](../results/B2_P023_d12_final_futility_v1/checkpoint.json) is a frozen snapshot, not a final d=15 decision. The original noisy conditions, 1% Wilson upper-bound rule and B2 reduction threshold were not changed.

## Does knowing the paired-readout model fix the observed failures?

We froze three already scored stressed receipts and inspected all six of their known failures and one preselected successful control per receipt. Three branches used the same packed RNG draws:

1. Original trajectories and original decoder.
2. Identical background faults and decoder with just the extra paired-readout faults removed.
3. Original stressed trajectories decoded with a graph that knows the **global** paired-readout rate, not the realized flags.

As in the [Stim detector error model](https://github.com/quantumlib/Stim/blob/v1.16.0/doc/file_format_dem_detector_error_model.md#semantics), removing an independently sampled mechanism cancels its detector contribution without redrawing other mechanisms. The projection was checked against whole-sampler fault flags and an independent Stim replay for two draws each in opening, steady and closing chunks. Over all 7,813 windows, the factual branch reproduced the archived truth, correction and failure bits for all nine selected trajectories. The logical truth bits did not change between branches.

| Selected cohort | Recovered by removing paired faults | Recovered with the pair-aware graph |
| --- | ---: | ---: |
| d=12 X, 2 original failures | 1 | 0 |
| d=12 Z, 2 original failures | 0 | 1 |
| d=15 X, 2 original failures | 1 | 0 |

The pair-aware graph recovered a different shot from either recovered by removing pairs. All three original success controls remained successful. This rules out treating a nominal weight update as a demonstrated fix for these failures. Since the sample was selected by outcomes, these counts are **not** population error rates, estimates of a decoder gain, or additional qualifying shots.

The independently [recounted result](../results/P023_B2_stress_counterfactual_v1/audit.json) retains every original receipt and both relevant start/close digests. The initial local freeze was `351f1cb24200b3f5fa7dfc2d23311de846c1969f`; `a06bb74ad712bf6ce8c70bbebd27a4b872dfd5f3` corrected only the d=12 Z input checksum before that case executed. Two earlier runners recorded the protocol digest at close; the audit proves their selected input entries and parameters did not change. The runner now holds the verified protocol bytes from startup through receipt writing.

## Structural replacement: keep nearly all of d=13

A full square d=13 uses 337 active qubits against d=15's 449, just short of the 25% reduction rule. We built a **335-active-qubit corner-shortened circuit** by removing the data site (25,25) and one of its two adjacent check ancillas. Graph-based boundary deformation is an established approach; our circuit and checks are specific to this comparison. See the [defect-adaptive surface-code study](https://www.nature.com/articles/s41534-025-01023-y) for context.

The preflight independently checks stabilizer commutation, full rank for the retained checks, one encoded logical qubit, and the **exact tick and order** of every retained CNOT. Both orientations still have seven ticks per round and only local CNOTs. On a 15-round circuit at the same four physical error probabilities, the shortest undetected *graphlike* fault witnesses have lengths:

| Circuit | Active qubits | X memory | Z memory |
| --- | ---: | ---: | ---: |
| Original square d=12 | 287 | 12 | 12 |
| Original square d=13 | 337 | 13 | 13 |
| Corner shortened, X-protected orientation | 335 | **13** | 12 |
| Corner shortened, Z-protected orientation | 335 | 12 | **13** |

The X-protected orientation is the first follow-up because X is the disqualifying cell of the 287-qubit version. It retains the X graphlike distance of d=13 while fitting the resource budget. At equal horizons the potential reduction is **25.39%**, not scored. The [circuit preflight](../results/P023_B2_stress_counterfactual_v1/corner_checked.json) contains hashes and zero statistical shots. Its result is not a general distance lower bound, long-horizon pass or calibrated hardware result. A continuous-stream implementation and independent million-round validation are still needed.

## Reproduce

Use the [counterfactual protocol](../benchmarks/P023_B2_stress_counterfactual_v1.json), archived whole-shard [input receipts](../results/P023_B2_stress_counterfactual_v1/source/) and the same [pinned kernel and toolchain](P023_grouped_sampler_checkpoint_v1.md). For a replay of one historical case, run the selected case at the exact `experiment_freeze` in its raw receipt in a separate checkout, with the archived source directory and native kernel. Recount the supplied receipts and reproduce the corner preflight:

```sh
export OPENBLAS_NUM_THREADS=1
python3 -B tools/p023_b2_stress_counterfactual_audit_v1.py \
  --artifact-dir results/P023_B2_stress_counterfactual_v1
qec_temp=$(mktemp -d)
python3 -B tools/b2_corner_shortening_preflight_v1.py --out "$qec_temp/corner.json"
cmp "$qec_temp/corner.json" results/P023_B2_stress_counterfactual_v1/corner_checked.json
```

No B2 comparable-volume or B7 resource credit is granted.
