# #023: faster direct million-round sampling without changing the noise law

Date: 2026-11-27

For the distance-15 memory, grouping equal-probability faults made the warmed 128-shot sampler **8.1–9.7× faster** and reduced measured sample-plus-decode time to **50–55%** of the prior path in the four 1,000-round benchmark cells. The X and Z single-trajectory million-round timing draws went from roughly 567 seconds to about 15 seconds of measured sample-plus-decode work. Their load and seeds differed; use the interleaved 128-shot comparison for the benchmark claim. The single trajectories are not acceptance samples.

## What changed

The earlier stream generated one independent Bernoulli outcome per [Stim detector error model](https://github.com/quantumlib/Stim/blob/main/doc/file_format_dem_detector_error_model.md#semantics) mechanism and trajectory. It still does. In the grouped version, exactly equal input probabilities share a call to [Stim's packed Bernoulli generator](https://github.com/quantumlib/Stim/releases/tag/v1.15.0). Each output bit is still assigned to precisely one mechanism and trajectory. Only the call layout and application of sparse hits changed. We never round or average probability classes, and sampling a correlated multi-target mechanism still flips all of its targets together. The compact C++ routine applies the already drawn flags by XOR; it does not draw randomness. The circuit, detector error model (DEM), decoding windows, matching weights and boundary rules stay fixed.

At distance 15, a steady nominal segment has 672,896 fault mechanisms in 46 exact probability classes. The paired-readout stress segment has 687,232 in 47. The verifier re-enumerated the DEM and checked that every mechanism belongs to exactly one group with unchanged probability. In all four X/Z and nominal/paired-readout cells, replaying the native path's exact flags in the whole Stim DEM reproduced detector and logical vectors bit for bit. Committed correction parity matched. Deliberately dropping either physical spill or correction carry was rejected in every cell.

## What was measured

The diagnostics warmed both paths and alternated execution order. Steady medians use 24 calls per implementation at 128 shots. Pipeline medians use three complete 1,000-round runs per implementation at 128 shots and include sampler calls and decoder/stitch work. Compilation, logging outside these timers, and non-timed bookkeeping are not included.

| Basis | Noise | Steady sampler old → grouped | 1,000-round pipeline old → grouped |
| --- | --- | ---: | ---: |
| X | Nominal | 86.33 → 8.93 ms | 1128.53 → 622.63 ms |
| X | Paired readout | 85.07 → 9.46 ms | 1210.22 → 645.91 ms |
| Z | Nominal | 81.28 → 9.08 ms | 1149.51 → 577.40 ms |
| Z | Paired readout | 82.67 → 10.26 ms | 1225.39 → 630.49 ms |

For the unbatched **million-round** timing runs, the audit checked the same circuit, sampling and decoder DEM hashes for each pair, one shot and all 7,813 windows. These are separate nominal X/Z draws timed on the same host under different contention. No throughput ratio from them is applied to a 128-shot qualification shard.

| Basis | Sampler time old → grouped | Decoder and stitch time old → grouped |
| --- | ---: | ---: |
| X | 560.86 → 7.19 s | 6.27 → 7.88 s |
| Z | 560.56 → 7.61 s | 6.15 → 7.50 s |

These are host software measurements, without a controller or the physical wait for the look-ahead. They do not establish a real-time decoder deadline.

## Original acceptance stays fixed

The [admission gate](../benchmarks/P023_grouped_sampler_gate_v1.json) was frozen before measuring the realistic benchmark. Only replay correctness and speed were used to admit the sampler. The [grouped qualification](../benchmarks/P023_streamed_memory_grouped_v2.json) was then locally frozen at `d51146380aba2c20357d70f6f6576b07f5509b63` before creating its independent salt. The original 1% Wilson upper limit, 1,024 shots per cell, maximum 3 failures, both bases, both arms and both horizons remain in force. No old shots are pooled into the new run.

All four new, independent 1,000-round cohorts have **0/1,024** failures (upper bound 0.374% each). The **million-round** qualification is still running; incomplete cohorts have no credit. The [previous 1,000,000-round d=7 rejection](P023_streamed_memory_checkpoint_v1.md) stands. No full #023 result, calibrated device claim, #022/B2 or #021/B7 credit, or 120-qubit/depth-7,000 criterion is asserted here.

## Reproduce

See the [admission receipts](../results/P023_grouped_sampler_v1/) and [qualification and timing audit](../results/P023_grouped_sampler_checkpoint_v1/checkpoint.json) for exact timing vectors, outcome bitsets, model hashes, cohort membership and the replay scripts.

Using the same pinned wheel versions as the [original benchmark](P023_streamed_memory_checkpoint_v1.md) and Apple clang 21.0.0 (clang-2100.1.1.101), macOS SDK 26.5, this build was checked byte for byte. Its install name is written into the Mach-O and affects the hash; use the recorded string as a linker label even if that directory does not exist.

```sh
export OPENBLAS_NUM_THREADS=1
qec_sdk=$(xcrun --sdk macosx --show-sdk-path)
qec_build=$(mktemp -d)
qec_label=/tmp/qec-p023-grouped.QcjMCKw1/p023_grouped_fault_scatter_v1.so
qec_kernel="$qec_build/p023_grouped_fault_scatter_v1.so"
clang++ -isysroot "$qec_sdk" -isystem "$qec_sdk/usr/include/c++/v1" \
  -std=c++17 -O3 -shared -fPIC -Wall -Wextra -Werror \
  -Wl,-install_name,"$qec_label" tools/p023_grouped_fault_scatter_v1.cc -o "$qec_kernel"
shasum -a 256 "$qec_kernel"
# expected 64ff47fb2694e77ff1c939268c05050b7ac36a67c0de7b8b0b5823568e75a355
qec_freeze=d51146380aba2c20357d70f6f6576b07f5509b63
qec_salt=e1703a7ad3fbe655bcc0a1a8e81f3afa62a9bcc7b3283cd84a5742424b2f7b5a
qec_run=$(mktemp -d)
python3 -B tools/p023_streamed_memory_grouped_v2.py --basis x --arm nominal \
  --rounds 1000000 --shards 0 --artifact-dir "$qec_run" --kernel "$qec_kernel" \
  --freeze "$qec_freeze" --salt "$qec_salt"
python3 -B tools/p023_streamed_memory_grouped_audit_v2.py \
  --artifact-dir results/P023_grouped_sampler_checkpoint_v1 \
  --timing-dir results/P023_grouped_sampler_checkpoint_v1 \
  --freeze "$qec_freeze" --salt "$qec_salt"
```
