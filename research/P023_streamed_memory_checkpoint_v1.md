# #023: the million-round run rejects d=7; d=15 advances to the full cohort

Date: 2026-11-27

The first 128 complete, continuous **1,000,000-round** trajectories of the nominal distance-7 arm had **57 X failures and 61 Z failures**. The predeclared 1,024-shot gate permits at most **3** per basis. Even if all unrun shots succeeded, neither basis could pass. This rejects the tested d=7 circuit and streaming decoder at this noise level, not every d=7 decoder or hardware setting.

The distance-15 alternative has **0/1,024** failures in each of its four 1,000-round cohorts (X/Z, nominal/paired readout). Each two-sided Wilson 95% upper bound is 0.374%, below the 1% target. The four d=15 million-round qualification cohorts have started; none is counted as passed in this checkpoint. The earlier direct d=7 thousand-round experiment used a different cohort and full-block decoder. Its pass does not confer long-horizon credit.

## Direct outcomes

| Distance | Rounds | Noise arm | X failures / shots | Z failures / shots | Decision |
| ---: | ---: | --- | ---: | ---: | --- |
| 7 | 1,000 | Nominal | 2 / 1,024 | 5 / 1,024 | Fails this pair |
| 7 | 1,000 | Paired readout | 2 / 1,024 | 4 / 1,024 | Fails this pair |
| 7 | 1,000,000 | Nominal | 57 / 128 | 61 / 128 | Both already exceed the fixed-cohort cap |
| 15 | 1,000 | Nominal | 0 / 1,024 | 0 / 1,024 | Passes this pair |
| 15 | 1,000 | Paired readout | 0 / 1,024 | 0 / 1,024 | Passes this pair |
| 15 | 1,000,000 | Both | Not yet complete | Not yet complete | No acceptance credit |

The d=7 million-round stress arm was not started after nominal disqualification. Failure fractions from truncated rows are descriptive, not a complete-cohort confidence interval. The frozen criterion requires a single distance to pass **both** horizons, **both** bases, and **both** noise arms.

## How the full trajectory fits

We retain the [original physical-noise parameters](../benchmarks/B2_B7_P023_direct_1k_memory_v1.json). We sample segments of the **same** folded detector error model, with one initialization and one final logical measurement in the underlying circuit. Within a mechanism, every affected detector and logical flip is sampled together; a syndrome contribution past a segment's end is XORed into the next one. This follows [Stim's DEM semantics](https://github.com/quantumlib/Stim/blob/main/doc/file_format_dem_detector_error_model.md#semantics), rather than concatenating independent short memories.

The independent matching decoder commits edges whose earliest real endpoint is in the oldest 128-round region, with the next two distances in rounds available as a guard. Future-only corrections remain tentative; endpoints beyond the committed region and the logical frame carry forward. This is a [window-decoding](https://arxiv.org/abs/2209.08552)-inspired policy, not a guarantee of minimum weight over the whole trajectory. d=15 uses at most **35,392** matching nodes in a window, versus **224,000,000** detector positions across a million-round trajectory (7,813 windows). That is a graph width comparison, not a measured peak-RSS ratio.

The synthetic stress adds a 0.01% probability per eligible check and folded period of flipping two consecutive ancilla results together. The middle detector cancels, leaving two time-separated detector events at the same spatial position. The decoder keeps its nominal model. This is one correlated readout stress, not a calibration or a claim against arbitrary bursts and leakage.

Eight control cells replay the **same fault flags** against the whole DEM and check the resulting detector and logical vectors bit by bit. Correction parity is checked at every committed boundary in these controls. Deliberately dropping either cross-boundary transfer is rejected in all eight cells. The control also inserts deterministic pairs of physical ancilla flips into the original circuits at representative check positions and verifies their predicted detector geometry.

## Throughput and reproducibility

In the two completed d=7 million-round shards, sampling took about 130 seconds each and decoder/stitch work took 62.2 seconds for X and 59.2 seconds for Z for a batch of 128 trajectories. These are host compute measurements, not feedback deadlines. The independent auditor recomputes the Wilson cutoff, checks the circuit and DEM identities, and recounts the logical XOR failure bits. See the [frozen protocol](../benchmarks/P023_streamed_memory_v1.json), [runner](../tools/p023_streamed_memory_v1.py) and [raw receipts and audit](../results/P023_streamed_memory_checkpoint_v1/checkpoint.json).

Freeze `91398ae931b2fb268e30fc1d8ef5f16bf87b7389` was committed locally before the random salt or acceptance sampling. Replaying requires that commit and Python 3.12.6, Stim 1.16.0, PyMatching 2.4.0, and NumPy 2.4.6:

```sh
export OPENBLAS_NUM_THREADS=1
qec_freeze=91398ae931b2fb268e30fc1d8ef5f16bf87b7389
qec_salt=5799635e79308a9d6f14ffb1eba754cf4bb22cba40b43552d279463ee6fc0ec7
qec_replay_dir=$(mktemp -d)
for qec_basis in x z; do
  python3 -B tools/p023_streamed_memory_v1.py --mode qualification \
    --distance 7 --basis "$qec_basis" --arm nominal --rounds 1000000 --shard 0 \
    --freeze "$qec_freeze" --salt "$qec_salt" --artifact-dir "$qec_replay_dir"
done
python3 -B tools/p023_streamed_memory_audit_v1.py \
  --artifact-dir results/P023_streamed_memory_checkpoint_v1 --freeze "$qec_freeze" --salt "$qec_salt"
```

The next decision is whether the 449-active-qubit d=15 arm meets the fixed million-round criterion, not whether it can pass another short test. No hardware/controller deadline, full #023 readiness, full #022/B2 or B7 resource credit is claimed; the 120-qubit/depth-7,000 question remains out of scope.
