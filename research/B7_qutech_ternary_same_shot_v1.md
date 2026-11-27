# #021/B7: simply masking a measured leakage flag did not help

2026-11-27. We changed the input, not the scoring rule. [QuTech's public readout data](https://doi.org/10.4121/902d7f9e-38bf-48a2-a2f7-52bbf7aeeedf) supply a third readout class on the **same shot** as the measurements used for decoding. In the selected high-injection cell, treating class 2 as an erasure made **415 more logical errors** over 85,840 identical test shots. This rejects that particular policy; it does not reject using leakage information.

## What was compared

The [paper](https://doi.org/10.1103/y66v-988s) reports experiments with three-level readout and leakage removal. We independently replayed the original download linked from the [authors' pinned input scripts](https://github.com/MarcSerraPeralta/data-lru-integrated-with-measurement-for-qec/tree/42f374076dbb98549d4022ab468fa480668f0294): a Z-basis, distance-three repetition code, eight rounds, no active leakage-removal unit, with the archive's injection settings 0 and 3. This is a public diagnostic rather than a reproduction of their best trained decoder or a substitute for the project's three original challenge cells.

The provider's train and test files are separate. Every row gives two eight-round ternary ancilla records and three terminal data bits; the initial bit string comes from the filename. All eight initial strings and all available test shots were retained. Both policies use the same nominal model and the provider's binary projection `2 → 1`; the flag-aware policy omits only the emission at a flagged position. A third policy misaligns the same flags by one round. The exact filter sees terminal adjacent parities, not the three terminal bits or their logical parity. Swapping the latent terminal vector with its global complement leaves all supplied parities unchanged and reverses the label. A separate 64-path enumeration checks the filter update.

| Injected-leakage setting | Shots | Shots with an ancilla flag | Hard failures | Mask the actual flagged readout | Mask one round late | Recovered / introduced by aligned mask |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 (no deliberate injection) | 85,840 | 18,215 | 15,309 | 15,313 | 15,418 | 2,422 / 2,426 |
| 3 (active injection) | 85,840 | 50,141 | 24,959 | 25,374 | 25,121 | 7,310 / 7,725 |

The high-injection increase is 0.483 percentage points. Neither cell improved. The baseline's fitted data-error parameter hit the top of the frozen grid in both cells; the model is a comparison tool, not a calibration of the device. The result rules out **discarding the flagged observation in this model**. A follow-up should retain the underlying readout and estimate what the measured third state says about errors here and in subsequent rounds, on a new test cohort.

## What this unblocks — and what it doesn't

- The release does contain real, round-aligned class-2 observations with same-shot outcomes. No cross-device flag mapping or syndrome-derived proxy is needed for this diagnostic.
- The available Fig. 3 reference inspected here is named `SSRO X3`, with 10,000 IQ measurements in each of the three prepared classes. The Fig. 4 text records do not expose a join to that calibration epoch, so it is not a confusion matrix for the two memory ancilla lines.
- The original T5 still needs a calibration join accepted for its own challenge denominator, a successful held-out paired improvement, and all-challenge non-regression. The measured diagnostic is not that acceptance. **B7 resource credit remains zero.**

## Reproduce

The [result and six range/CRC receipts](../results/B7_qutech_ternary_same_shot_v1/) bind the selected files to the [prespecified test](../benchmarks/B7_qutech_ternary_same_shot_v1.json). The full 6.49 GB archive was not downloaded. The eight test files per setting each supply 10,730 rows. Use Python 3.12.6, NumPy 2.4.6 and SciPy 1.17.1:

```sh
export OPENBLAS_NUM_THREADS=1
qec_input=$(mktemp -d)
for split in train test; do
  for level in 0 3; do
    mkdir -p "$qec_input/$split/$level"
    set --
    for state in 0 1 2 3 4 5 6 7; do
      set -- "$@" --member "Data/Figure 4/measurement_outcomes/$split/no_lru_round_8_leak_${level}_state_${state}.txt"
    done
    python3 -B tools/b7_public_qec_zip_intake_v1.py --archive qutech_lru_4tu_v1 \
      --budget-mib 16 --member-dir "$qec_input/$split/$level" \
      --out "$qec_input/${split}_${level}.json" "$@"
  done
done
python3 -B tools/b7_qutech_ternary_same_shot_v1.py --artifact-dir "$qec_input" \
  --freeze 9864d47682ff793071e74149096041045fabfb9a --out "$qec_input/score.json"
```

Re-fetched range receipts can differ in the byte ranges used by the HTTP transport; compare the member SHA-256 digests and output prediction digests to the released records.
