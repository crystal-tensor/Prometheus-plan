# What makes a correct decoder window slow?

Date: 2026-11-27

Scope: #021/B7, #022/B2, #023 only

## Paired test

The [AXI4-Lite32 pilot](B2_B7_P023_d6_axi_lite32_pilot_v1.md) established correctness under a deliberately stalled bus. This test asks how much of the observed cycle count came from that schedule. The X and Z graphs are the same distance-6 graphs as before; each basis uses its own unchanged generated endpoint and direct RTL reference. The paired sample is 328 windows (X shots 0 and 15) and 1,312 windows (Z shots 0–7), replayed once under each policy.

- `legacy_hold`: the prior response schedule; hold BVALID for 1–4 sampled cycles before acceptance and RVALID for 1–5, rotating by the absolute transaction index.
- `ready_high`: assert BREADY before issuing a write and RREADY before issuing a read for every measured transaction. The serialized transaction order, AW/W skew schedule, inputs, simulator seed and directed probes are unchanged. The probes intentionally still exercise backpressure but are excluded from the timed windows.

The meter starts at the reset before each opening, steady, or closing window. It ends with the second snapshot-generation read, which verifies that the correction did not tear. It counts only the driver's sampled RTL bus cycles. Python selection, Rust primal and feedback work, socket time, startup and termination are outside the clock count.

| Bucket | Operations counted |
| --- | --- |
| Ingress | Reset, phase, defects, and resident selectors |
| Solve commands | Solver register writes, including issuing FindObstacle |
| Obstacle reads | Status and conflict registers returned by FindObstacle |
| Correction writes | Clear, XOR-edge commands, and latch |
| Correction reads | Two generation reads, metadata, and all vector words |

A stage counts bus cycles while issuing and accepting its operations; it does not measure compute-only cycles. For this serialized driver and registered endpoint, each completed write costs four base cycles plus its AW/W skew; each read costs two base cycles. Every additional measured cycle must reconcile to BVALID or RVALID being held without READY. This arithmetic was checked per window and per bucket, not inferred from differences in run totals.

## Result

All 1,640 pairs match in ordered transaction content and reproduce their direct RTL output byte-for-byte, with 16,752 occupancy checks per policy and zero commit-residual, final-residual, or final-frame failures. RTL and compiled model hashes match between policies within each basis. In every window and every bucket, the exact cycle difference is the measured B plus R holds.

| Basis | Policy | Windows | Total cycles | p50 | p95 | p99 | Max |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| X | legacy_hold | 328 | 228,614 | 653 | 1,285 | 1,562 | 1,859 |
| X | ready_high | 328 | 133,227 | 381 | 757 | 921 | 1,095 |
| Z | legacy_hold | 1,312 | 943,803 | 678 | 1,319 | 1,609 | 2,407 |
| Z | ready_high | 1,312 | 550,415 | 395 | 775 | 946 | 1,419 |

The injected response holds account for 95,387 X cycles and 393,388 Z cycles (41.7% of the old measured totals in each basis). Median paired savings are 274 X and 284 Z cycles; p99 of the paired savings is 641 X and 664 Z cycles. The two policy p99s and the paired-delta p99 describe different distributions.

| READY-high bucket | X cycles | Z cycles |
| --- | ---: | ---: |
| Ingress | 32,504 | 133,861 |
| Solve commands | 52,003 | 216,376 |
| Obstacle reads | 27,292 | 113,058 |
| Correction writes | 14,144 | 57,984 |
| Correction reads | 7,284 | 29,136 |

Solve commands plus obstacle reads account for 59.5% (X) and 59.9% (Z) of the READY-high cycle totals. Within the windows at or above each READY-high p99, they account for 64.6% of cycles across 4 X windows and 68.3% across 14 Z windows; correction reads account for 2.2% and 2.0% there, respectively. All 18 tail windows are steady; this does not measure the tail of the closing phase separately. These are descriptive statistics for two X and eight Z trajectories, not a population estimate.

**Next test:** Combine `Growable` and `ConflictValid` into one 32-bit status read, retaining the full growable length (including its sentinel), post-command response fence, detailed conflict reads, and the correction-generation check. The measured 3,964 X and 16,404 Z obstacle queries imply a prediction of one fewer read per query, or 40,736 fewer sampled cycles (6.0%) on these READY-high replays, **if all other operations and timings stay fixed**. This is not a measured speedup. Re-use READY-high for the primary latency A/B because removing a read reindexes the legacy stall schedule; separately challenge the new status path with held responses and consecutive queries.

The [joint evidence](../results/B2_B7_P023_d6_axi_cycle_profile_evidence_v1.json) binds all four run logs and receipts (ID `cbc6dd10c1e15e1cd78aec263d057be3bc5c78fa91cd38387ae0fe98bd9badeb`).

## Reproduce

The [recorder](../tools/b2_b7_p023_d6_axi_cycle_record_v1.py) verifies the same Micro Blossom archive as the accepted pilot, applies an [additive timing patch](../tools/microblossom/d6_phase_axi_cycle_profile_v1.patch), and saves both raw outputs, logs and hash-bound receipts. The [meter](../tools/microblossom/D6PhaseAxiCycleTiming.scala) records a digest of the ordered stage, operation, address, data, strobe and response in each window. With the pilot's Java 17, Verilator 5.040 and Python selector environment:

```sh
for qec_basis in x z; do
  python3 tools/b2_b7_p023_d6_axi_cycle_record_v1.py \
    --basis "$qec_basis" --artifact-dir "$qec_artifacts" --archive "$qec_archive" \
    --build-parent "$qec_scratch" --java-home "$qec_jdk17" --verilator-prefix "$qec_verilator"
done
# Re-audit the archived measurements.
python3 tools/b2_b7_p023_d6_axi_cycle_audit_v1.py --artifact-dir results
# To build a new joint evidence file, use --artifact-dir "$qec_artifacts" --write.
```

The independent audit also replays the prior correctness audit. It aligns the ordered Rust and Scala streams by window key, checks that every result matches direct RTL byte-for-byte, and verifies that both policies used the same simulator and compiled model archive within each basis. It checks the correction and ingress transaction counts against the frozen input and output, recomputes the scheduled holds, and requires equal transaction digests between the two policies for every window. Quantiles use nearest rank within each basis. The median or p99 of a paired delta is computed from individual paired windows, not from subtracting two unrelated quantiles.

## Limits

These are cycle counts for a serialized simulation bus manager, not time on an FPGA or measured decoder p99/miss rate. The paired sample does not establish a full-corpus AXI denominator, multi-context ordering, clock-domain crossing, FPGA timing or utilization, full B2, scalable #023, or B7 resource credit. The 120-qubit/depth-7,000 question remains outside the acceptance design.
