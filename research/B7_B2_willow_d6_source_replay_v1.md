# #021/B7: 400,000 real Willow shots replay; the leakage join is still missing

Date: 2026-11-27

The November 2026 [Google Quantum AI Willow release](https://doi.org/10.5281/zenodo.24142014) includes a distance-6 X/Z memory patch. We reconstructed all 400,000 selected shots from its raw measurement bits, shot-specific sweep bits and ideal circuit. **Every detector byte and actual logical-flip byte equals the provider's version.** This advances the real-input side of the B2/B7 replay, but it neither qualifies the local 71-qubit schedule on hardware nor clears the calibrated leakage gate.

## What replayed

Before scoring, the protocol fixed the sole published d=6 memory patch, `d6_0+0j`, at six rounds in both bases. Each cell has 200,000 shots and 77 listed qubit coordinates. The circuit defines 246 measurement bits, 36 sweep bits, 211 X or 209 Z detector bits, and one logical observable. Absolute acquisition time and leakage labels are not fields in the selected memory files. A wrong packed shot count was rejected; dropping the supplied per-shot sweep bits changed the detector vector or logical output in every row.

| Basis | Binary trace and truth replay | Local independent matching failures | Local correlated matching failures | Publisher failures | Local correlated predictions differing from publisher |
| --- | ---: | ---: | ---: | ---: | ---: |
| X | 200,000/200,000 | 4,327 | 3,145 | 3,090 | 847 |
| Z | 200,000/200,000 | 4,137 | 2,690 | 2,699 | 777 |

Both local policies use the **same supplied detector error model**, rather than regenerating it from the different noise settings in the example noisy circuit. This is an untuned paired comparison on public rows: correlation reweighting recovered 2,268 X / 2,369 Z cases and introduced 1,086 X / 922 Z failures (net reductions of 27.3% / 35.0%). It is not the publisher's exact decoder output, nor a test of a leakage flag. The replicate result file was byte-identical.

The replay uses bounded HTTP partial-content requests, ZIP member CRCs and per-file SHA-256 digests. The [range and result receipts](../results/B7_B2_willow_d6_source_replay_v1/) identify the 18 relevant circuit/data members; we did not download or independently hash the full 42.9 GB archive. The [primary paper](https://arxiv.org/abs/2611.21578) describes both memory and stability experiments; this replay uses the memory files, not the stability subsamples.

## Why the calibrated gate still does not pass

[Sycamore's published prepared-state IQ clouds](https://doi.org/10.5281/zenodo.7302032) do have four classes. With a fixed Gaussian classifier fit to the first half of each cloud, the held-out prepared `0/1` and `2/3` groups each contain 3,000 observations per site. Qubit 57 has 2 false leakage flags and 133 missed flags; qubit 58 has 8 and 88. Full four-by-four counts are archived. These are prepared-state calibration measurements on other hardware, not Willow per-shot flags.

[Ankaa-2's fast-feedback archive](https://zenodo.org/records/15364358) supplies timestamped binary calibration for qubit 50, with confusion rows `[9672,328]` and `[534,9466]` for prepared 0 and 1. It has no prepared 2/3 labels in that calibration group. Neither reference can be joined to the Willow shots.

To submit the original T5 packet, we still need a documented join from acquisition/calibration window and physical qubit to shot and readout index, explicit leakage flags or equivalent labeled IQ, confusion data for that acquisition, and matched binary syndromes and logical labels. The accepted challenge denominator or a reviewed replacement must be fixed before comparing decoders. A calibrated holdout comparison must then improve and meet non-regression. **K4–K6 are not accepted; B7 credit remains zero.** No new device run or hardware timing result is claimed.

## Reproduce

Use the [frozen protocol](../benchmarks/B7_B2_willow_d6_source_replay_v1.json), Python 3.12.6, Stim 1.16.0, PyMatching 2.4.0, NumPy 2.4.6, and the h5py version in the receipt. Preserve the published ZIP member names and case:

```sh
export OPENBLAS_NUM_THREADS=1
qec_src=$(mktemp -d)
for qec_basis in X Z; do
  qec_lower=$(printf '%s' "$qec_basis" | tr 'XZ' 'xz')
  qec_prefix="stability_paper_data/memory/d6_0+0j/$qec_basis/r006"
  mkdir "$qec_src/d6$qec_lower"
  python3 -B tools/b7_public_qec_zip_intake_v1.py --archive willow_stability_2026 \
    --budget-mib 28 --out "$qec_src/willow_d6${qec_lower}_range.json" \
    --member-dir "$qec_src/d6$qec_lower" --member "$qec_prefix/circuit_ideal.stim" \
    --member "$qec_prefix/circuit_noisy_si1000.stim" --member "$qec_prefix/metadata.json" \
    --member "$qec_prefix/measurements.b8" --member "$qec_prefix/sweep_bits.b8" \
    --member "$qec_prefix/detection_events.b8" --member "$qec_prefix/obs_flips_actual.b8" \
    --member "$qec_prefix/decoding_results/sparse_blossom_with_si1000_prior/error_model.dem" \
    --member "$qec_prefix/decoding_results/sparse_blossom_with_si1000_prior/obs_flips_predicted.b8"
done
curl -fLsS 'https://zenodo.org/records/7302032/files/readout_clouds.zip?download=1' -o "$qec_src/readout_clouds.zip"
curl -fLsS 'https://zenodo.org/records/15364358/files/fast_feedback_raw_data.h5?download=1' -o "$qec_src/fast_feedback_raw_data.h5"
python3 -B tools/b7_b2_willow_d6_source_replay_v1.py --input "$qec_src" \
  --out "$qec_src/replay.json" --freeze a142ab3b34281c0bbb33cb434859e6e51a30a1ec
```

The independent [million-round simulation progress](B2_P023_d12_same_condition_checkpoint_v1.md#million-round-follow-up) does not count as calibrated trace evidence.
