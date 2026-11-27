# #023 passes the direct million-round simulation gate; #022/B2 tests a shorter corner

2026-11-27. **A distance-15, 449-active-qubit rotated surface code passed the original 1% simulation gate in both bases, at both horizons and with the declared paired-readout stress.** A 335-qubit circuit that prioritises the X boundary passed the short gate. Its million-round test is independent and has started; no reduction is credited yet.

## #023: direct measurement at both horizons

Each cell contains a separate, fixed cohort of 1,024 complete trajectories. The criterion is at most three logical failures per cell (two-sided Wilson 95% upper endpoint at most 1%). The four nominal circuit-noise rates are 0.001; the stress adds a 0.0001 paired ancilla-readout flip per eligible folded period and line. The decoder in both arms uses the nominal minimum-weight perfect-matching graph. No parity-rate projection, pooling, or earlier diagnostic run supplied an outcome.

| Basis and noise | 1,000 rounds: failures | 1,000,000 rounds: failures | Million-round Wilson upper |
| --- | ---: | ---: | ---: |
| X, nominal | 0 / 1,024 | 0 / 1,024 | 0.374% |
| X, paired readout | 0 / 1,024 | 2 / 1,024 | 0.709% |
| Z, nominal | 0 / 1,024 | 1 / 1,024 | 0.551% |
| Z, paired readout | 0 / 1,024 | 0 / 1,024 | 0.374% |

That is 4.096 billion directly sampled shot-rounds across the four million-round cells. Dividing exposure by the sum of decoder application times for each cell gives **202,428–205,173 shot-rounds/second**. The shard-level p99 decode times for a 128-trajectory batch-window ranged from **140.821 to 176.293 ms**. These host compute measurements are not acquisition-to-feedback latency or a real-time hardware certificate. The [audit](../results/P023_d15_million_acceptance_v1/checkpoint.json) separately identifies unbatched probes that are not part of the qualification cohort.

The result answers the 1% question for this model and one declared stress. It does not establish a 0.1% bound, resistance to all drift or correlated noise, a hardware demonstration, or B7 credit.

## #022/B2: change the code boundary, then test against the qualified reference

The [287-qubit memory was rejected](P023_B2_stress_counterfactual_and_corner_v1.md) when stressed X reached 6 failures in 256 trials. In the next candidate we remove one data corner and one neighbouring Z check from the distance-13 layout. This keeps the existing local CNOT placement and seven ticks per round; the tested structural X/Z graphlike witness lengths remain 13/12, respectively. The compact stream agrees instruction-for-instruction with the independent 15-round projection. At a million rounds it contains 167,000,001 X or 166,999,999 Z detector bits per trajectory, with 7,813 windows and physical- and correction-parity carry. Deterministic single-pair interventions check stress placement; dropping either carry or truncating the terminal packed byte is detected by the [controls](../results/B2_P023_corner335_controls_v1/).

The [335-qubit checkpoint](../results/B2_P023_corner335_checkpoint_v1/checkpoint.json) records **0 / 1,024 failures in each of the four independent 1,000-round cells**. The four million-round cohorts are running under the same [precommitted test](../benchmarks/B2_P023_corner335_same_condition_v1.json). All eight cells must pass independently before the reduction from 449 to 335 active-qubit-rounds per round (**25.39%**) is credited. Four failures in any cell are enough to stop that verdict early. Neither a detector count nor short-horizon success certifies the reduction.

The [first two long batches in each cell](../results/B2_P023_corner335_first_million_v1/checkpoint.json) recorded 2, 1, 1 and 3 failures out of 256 each in the same order as the reference table. In particular, one more stressed-Z failure would rule out a pass. This is an audited, incomplete screening snapshot, not a confidence verdict at 1,024 trajectories.

## Recount the released evidence

From the repository root with Python 3.12.6, Stim 1.16.0, PyMatching 2.4.0 and NumPy 2.4.6:

```sh
export OPENBLAS_NUM_THREADS=1
qec_audit=$(mktemp -d)
python3 -B tools/p023_streamed_memory_grouped_audit_v2.py \
  --artifact-dir results/P023_d15_million_acceptance_v1 \
  --timing-dir results/P023_grouped_sampler_checkpoint_v1 \
  --freeze d51146380aba2c20357d70f6f6576b07f5509b63 \
  --salt e1703a7ad3fbe655bcc0a1a8e81f3afa62a9bcc7b3283cd84a5742424b2f7b5a \
  --out "$qec_audit/d15.json"
cmp "$qec_audit/d15.json" results/P023_d15_million_acceptance_v1/checkpoint.json
python3 -B tools/b2_p023_corner335_audit_v1.py \
  --artifact-dir results/B2_P023_corner335_checkpoint_v1 \
  --freeze 09187fc175bffa75b6611e7110289e2c1c89010d \
  --salt 89d2849938d1b42efbd0ca570b3ebcd435a3d7350481c4ccf1d4ca2fa2081545 \
  --out "$qec_audit/335.json"
cmp "$qec_audit/335.json" results/B2_P023_corner335_checkpoint_v1/checkpoint.json
```

Both audits were reconstructed byte-for-byte from the archived shard receipts. To reproduce the first long snapshot, copy the 32 short-horizon shards and eight first-million shards to one temporary directory and run the 335 audit on that directory with the same freeze and salt.
