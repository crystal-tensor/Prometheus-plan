# Can one status word remove a decoder round trip without losing a result?

Date: 2026-11-27

Scope: #021/B7, #022/B2, #023 only

## Change

The [paired cycle profile](B2_B7_P023_d6_axi_cycle_profile_v1.md) found that solve commands and obstacle reads dominated the measured slow windows. This candidate adds a read-only AXI4-Lite32 word at `0x034`: bit 31 is `ConflictValid`, and bits 30:0 contain the zero-extended `Growable` length. The tested 26-bit I/O length, including its all-ones sentinel, is preserved. The two legacy read addresses are still available. The three detailed conflict words, solver instructions, phase banks, and correction-generation check are unchanged.

Both fields already come from registers captured on the same completed `FindObstacle`. The packed word uses the existing R response latch at AR acceptance; it has no extra state register of its own. The solver manager still waits for the command's B response before reading status and finishes any conflict-detail reads before issuing the next query. This contract does not allow an arbitrary manager to mix detail reads from overlapping results.

For X, the old generated Verilog was verified against the archived RTL SHA-256 and compared byte-for-byte with the candidate starting at `module DistributedDual`. The core and all subsequent generated modules matched; this static check is not a synthesis/resource measurement.

## Acceptance test

The baseline is the archived split-register READY-high Verilator replay: 328 windows from X shots 0 and 15 and 1,312 from Z shots 0–7. The candidate replays those exact inputs with the same simulator binary and seed, AW/W skew, and untimed directed warm-up. It keeps BREADY/RREADY high for measured transactions. Backpressure is checked separately; comparing the old transaction-indexed stall policy after removing a read would reindex the schedule.

For each window, the meter logs both the physical transaction digest and a logical digest that expands each packed response into the original length read followed by the original valid read. The audit requires the logical digest to match the baseline, and checks that each `FindObstacle` now consumes one packed read instead of the two common status reads. All other transaction counts and cycle stages must match. Every read removed must account for two measured cycles. Syndrome, selected subgraph, correction, occupancy, commit residual, and final frame are checked against the accepted direct RTL outputs.

## Result

All 1,640 window pairs pass the expanded transaction comparison. The candidate's raw outputs are byte-identical to the direct RTL baseline, with 16,752 occupancy checks and zero commit-residual, final-residual, or final-frame failures. X removes 3,964 reads and 7,928 cycles; Z removes 16,404 reads and 32,808 cycles. Every window reconciles to exactly two cycles per eliminated read. The combined READY-high sample falls from 683,642 to 642,906 sampled cycles (40,736 fewer, or 6.0%). Independent recounting from the run logs reproduces both the totals and quantiles.

| Basis | Status path | Paired windows | Total cycles | p50 | p95 | p99 | Max |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| X | split | 328 | 133,227 | 381 | 757 | 921 | 1,095 |
| X | packed | 328 | 125,299 | 359 | 705 | 865 | 1,029 |
| Z | split | 1,312 | 550,415 | 395 | 775 | 946 | 1,419 |
| Z | packed | 1,312 | 517,607 | 371 | 724 | 886 | 1,327 |

Quantiles are nearest-rank by basis. The median paired saving is 22 cycles for X and 24 for Z. Removing a read changes neither writes, measured response stalls, nor the AW/W skew. This is a measured improvement in this serialized bus path, not a device or end-to-end latency result.

The [joint replay evidence](../results/B2_B7_P023_d6_axi_packed_status_evidence_v1.json) has ID `d24dc869a4020f81dfa24d44ff09230f6d1a79ae712cba5285c8fc6bbea91a34`.

## Held-response stress case

On the three-vertex Icarus fixture, the legacy and packed managers find exactly the same conflict, including the detailed fields. Keep the packed R response from query A unaccepted while reset and query B both complete their writes. The original beat stays at `0x80000000`; a fresh read returns B's `0x03ffffff`, including every sentinel bit. An intentionally [unlatched-response mutation](../tools/microblossom/d6_phase_axi_packed_status_negative_control_v1.patch) reaches the same conflict, then fails the held-R invariant as B changes the live state. This tests an accepted bus beat across a later query, not a multi-register result protocol for overlapped clients.

## Reproduce

Use the [recording tool](../tools/b2_b7_p023_d6_axi_packed_status_record_v1.py) with the same pinned Micro Blossom archive, Java 17, Verilator 5.040, and selector environment as the previous replay. The tool applies the [packed-status patch](../tools/microblossom/d6_phase_axi_packed_status_v1.patch) on top of the accepted AXI and timing patches in an isolated tree. The separate smoke run uses Icarus Verilog and its host C++/Boost headers. It applies the negative control only after the positive regressions.

```sh
for qec_basis in x z; do
  python3 tools/b2_b7_p023_d6_axi_packed_status_record_v1.py \
    --basis "$qec_basis" --artifact-dir "$qec_artifacts" --archive "$qec_archive" \
    --build-parent "$qec_scratch" --java-home "$qec_jdk17" --verilator-prefix "$qec_verilator"
done
python3 tools/b2_b7_p023_d6_axi_packed_status_record_v1.py \
  --smoke --artifact-dir "$qec_artifacts" --archive "$qec_archive" \
  --build-parent "$qec_scratch" --java-home "$qec_jdk17"
python3 tools/b2_b7_p023_d6_axi_packed_status_audit_v1.py --artifact-dir results
```

## Limits

These are sampled RTL bus cycles, excluding host software and transport time. The bounded pilot does not demonstrate full AXI coverage, a multi-context or CDC implementation, FPGA timing or resources, end-to-end p99/miss rate, full B2, scalable #023, or B7 resource credit. The 120-qubit/depth-7,000 question remains outside acceptance.

**Next test:** Can one request issue FindObstacle and return its status without an extra write/read round trip? Require exactly one execution per accepted request, no early result, and a held response that remains stable even as other legal bus activity proceeds. Keep the expanded transaction and raw-output checks before comparing cycles.
