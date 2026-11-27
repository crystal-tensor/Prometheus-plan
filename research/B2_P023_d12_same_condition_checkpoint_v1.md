# #022/B2: 287 active qubits clear the short gate; the million-round test starts

Date: 2026-11-27

The distance-12 challenger passed four independent **1,000-round** cohorts: **0/1,024** logical failures per X/Z basis with nominal and paired readout noise. Each Wilson 95% upper bound is 0.374%. The candidate keeps the same noise, the same matching/commit rule, the same 128-round commit stride and 30-round look-ahead, and the same seven circuit ticks per round as the distance-15 reference.

**Conditional resource delta:** 287 instead of 449 active qubits, or 287,000,000 instead of 449,000,000 active-qubit-rounds per million-round trajectory. The 36.08% reduction is a ledger comparison, not earned B2 credit. The d=15 reference's four million-round cohorts each have 0/256 failures in this snapshot. The first d=12 nominal million-round shards are running and paired readout follows; no candidate long shard is complete.

## What makes this a like-for-like comparison?

- **Cost:** The circuits use 7,000 ticks at 1,000 rounds and 7,000,000 at one million, with every CNOT checked against local neighboring sites. The active sites are counted from the actual CNOT targets and checked against the circuit coordinates; we do not use the padded index range as a qubit count. d=13 has 337 active qubits, so it misses the original 25% reduction by a fraction of a percentage point. d=12 is the largest square rotated patch that meets the raw resource rule against d=15.
- **Noise and decoder:** The four circuit-level probabilities stay at 0.001. The stress keeps the same extra 0.0001 probability per eligible check and period of flipping consecutive ancilla results jointly. Decoding retains nominal weights, the same matching graph construction and commit policy, and equal *absolute* look-ahead: d=12 is not given extra future rounds.
- **Even-distance boundaries:** The initial and terminal check layers have 72 detectors in X and 71 in Z, for 143,001 and 142,999 detector positions at 1,000 rounds. The guard covers 4,290 detectors and is not byte-aligned. The runner masks only padding, keeps the final partial byte, and carries the valid syndrome and correction bits across cuts. No virtual quantum round or physical detector is inserted.

Across all four control cells, running the new code at d=15 with the same seed reproduced the original packed stream and correction output exactly. The d=12 runner replays its actual fault flags through the monolithic model to check every syndrome and logical bit. Omitting either inter-window carry or truncating the final detector byte fails the corresponding negative control. The burst geometry is independently checked by injecting deterministic pairs of ancilla errors into the original circuit.

## Evidence and credit

| Distance | Rounds | Nominal X/Z | Paired readout X/Z | Eligibility |
| ---: | ---: | --- | --- | --- |
| 12 | 1,000 | 0/1,024 each | 0/1,024 each | All four short cells pass |
| 15 | 1,000 | 0/1,024 each | 0/1,024 each | All four short cells pass |
| 12 | 1,000,000 | Running | First tranche staged | Not qualified |
| 15 | 1,000,000 | 0/256 each | 0/256 each | Partial; not qualified |

The long gate still needs both X/Z bases and both noise arms at a fixed 1,024 shots per cell, at most three failures per cell. A partial cohort earns no pass; the two distances and their random streams are never pooled. In the first 128-shot d=15 million-round shard per arm, the grouped implementation took 108–109 seconds in the sampler versus 625–642 seconds in the earlier implementation, and about 36–37% less combined sampler-and-decode time. These runs were on the same host with distinct seeds and load, not an isolated performance benchmark and not a controller measurement.

The [original gate](../benchmarks/B2_B7_P023_logical_memory_horizon_gate_v1.json) remains controlling. Even a comparable simulator pass supplies no calibrated leakage, hardware deadline or B7 resource credit. The 120-qubit/depth-7,000 acceptance proposal remains out of scope.

## Reproduce

See the [candidate manifest](../benchmarks/B2_P023_d12_same_condition_v1.json), [same-fault controls](../results/B2_P023_d12_controls_v1/), and [combined audit and disjoint receipts](../results/B2_P023_d12_checkpoint_v1/checkpoint.json). The candidate freeze `f81f11d9af1f76cfae4cef1f151d804aaf74d389` was committed before drawing its qualification salt. Use the pinned dependencies and kernel build from the [d=15 grouped sampler](P023_grouped_sampler_checkpoint_v1.md).

```sh
export OPENBLAS_NUM_THREADS=1
qec_d12_freeze=f81f11d9af1f76cfae4cef1f151d804aaf74d389
qec_d12_salt=9f05baa8bae7862cee870bed704aa9ccafd778a76bbce8b0b7617f4f57c2545c
qec_d15_salt=e1703a7ad3fbe655bcc0a1a8e81f3afa62a9bcc7b3283cd84a5742424b2f7b5a
qec_d12_data=$(mktemp -d)
python3 -B tools/b2_p023_d12_gate_v1.py --mode qualification --basis x --arm nominal \
  --rounds 1000 --shards 0 --kernel "$qec_kernel" --artifact-dir "$qec_d12_data" \
  --freeze "$qec_d12_freeze" --salt "$qec_d12_salt"
python3 -B tools/b2_p023_d12_audit_v1.py \
  --artifact-dir results/B2_P023_d12_checkpoint_v1/candidate \
  --reference-dir results/B2_P023_d12_checkpoint_v1/reference \
  --freeze "$qec_d12_freeze" --salt "$qec_d12_salt" --reference-salt "$qec_d15_salt"
```
