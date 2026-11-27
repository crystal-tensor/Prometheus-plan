# Can one bus request launch a decoder query and return the right result?

Date: 2026-11-27

Scope: #021/B7, #022/B2, #023 only

## Change and ordering contract

The [packed status experiment](B2_B7_P023_d6_axi_packed_status_v1.md) still required a `FindObstacle` write and a separate status read. The new opt-in address `0x038` is an explicit query command: an accepted AR queues one `FindObstacle`, and its R beat contains the packed status once the core result has been captured. Bit 31 is conflict-valid; bits 30:0 hold the zero-extended length. Conflict details, correction snapshot generation, and the existing registers are unchanged. The plain `0x034` status address remains a side-effect-free read. The new command is disabled in split and packed modes.

The address is staged rather than decoded into a combinational READY path from live AXI inputs. A pending query lets an older partial write finish and waits for that write to commit; a manager must supply the missing half independently of the query response. The query need not wait for its B response to retire: the B and R latches are independent. Ordinary reads still allow inspection of committed state with a partial write buffered. These are local ordering choices layered on the [Arm AXI transport requirements, §A3](https://documentation-service.arm.com/static/602a9df190ee6824a1e02b98), not a full protocol certificate.

In both generated endpoints, all eight AXI outputs were traced through continuous assignments to rising-edge registers without a live AXI input in those paths. This structural check is specific to the generated wrappers; it does not establish board timing.

Use the side-effecting query only from a deliberate, serialized manager; no speculative or replaying CPU MMIO path is qualified. The manager drains associated detail reads before its next result. An already accepted R beat is protected from later state changes, but independent detail registers do not implement an overlapping multi-result protocol. Physical interface reset with an outstanding request is outside this test.

## Gates

- Compare the same fixed X shots 0 and 15 and Z shots 0–7 to the archived packed-status READY-high runs, with the same inputs, simulator, seed and untimed probes. Preserve each retained write's old logical ordinal and its AW/W skew by reserving the removed query's ordinal.
- For each window, expand the query R into its original `FindObstacle` write and packed status read. Require equal ordered digests against both the packed and split representations, and byte-identical direct RTL outputs, including correction vectors and final frames.
- Sample the actual fused core issue edge and its command. Require one issue per accepted query AR, one returned status, and no RVALID before the result capture edge. In the three-vertex test, stress AW-first and W-first writes and hold both responses, then hold a conflicting R beat across later commands.
- Deliberately [retain a consumed request](../tools/microblossom/d6_phase_axi_fused_query_duplicate_control_v1.patch) and deliberately [assert R before capture](../tools/microblossom/d6_phase_axi_fused_query_early_r_control_v1.patch) in separate negative controls. Both must fail their intended assertions.

For the serialized READY-high test with one core pipeline wait cycle, the old query takes a four-cycle write plus that write's address/data skew and a two-cycle status read. The candidate takes four sampled cycles: accept AR, issue, capture, return R. Thus the predicted delta per query is two fixed cycles plus the skew of the removed write. The solve-write bucket should shrink while the read bucket absorbs the core wait; all other buckets must match. This is tested per window, not assumed from a pooled mean. The audit also reports the counterfactual obtained by subtracting each path's measured skew. That arithmetic is not a separate zero-skew replay.

## Result

All 1,640 paired windows pass. The core-edge monitor records 20,368 accepted requests, 20,368 actual issues and 20,368 responses, with no RVALID before the checked capture boundary. The expanded packed and split transaction digests match for every window; raw direct RTL output is byte-identical with 16,752 occupancy checks and zero commit residual, final residual or final-frame failures. The small-graph result matches all three managers; both deliberate faults fail the expected check.

| Basis | Query path | Paired windows | Total sampled cycles | p50 | p95 | p99 | Max |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| X | packed | 328 | 125,299 | 359 | 705 | 865 | 1,029 |
| X | fused | 328 | 110,758 | 317 | 609 | 759 | 913 |
| Z | packed | 1,312 | 517,607 | 371 | 724 | 886 | 1,327 |
| Z | fused | 1,312 | 457,425 | 327 | 637 | 778 | 1,161 |

The total drops from 642,906 to 568,183 cycles (74,723 fewer, 11.6% under this schedule). There are 40,736 fixed cycles removed and 33,987 fewer cycles from the eliminated writes' deliberate AW/W skew. The audit and an independent raw-log recount agree on each term and on the nearest-rank quantiles. Subtracting measured skew in both paths gives 493,826 to 453,090 cycles by arithmetic; this is not a zero-skew simulation run.

The [joint replay evidence](../results/B2_B7_P023_d6_axi_fused_query_evidence_v1.json) has ID `3f38672465eba3065cf11eae83fc3b59d3b704c08d33482609b636a3614e9fee`.

## Reproduce

Use the [recorder](../tools/b2_b7_p023_d6_axi_fused_query_record_v1.py) on the pinned Micro Blossom archive and the accepted timing/packed-status patches. It applies the [fused-query patch](../tools/microblossom/d6_phase_axi_fused_query_v1.patch) in an isolated tree. Verilator 5.040 and Java 17 run the X/Z replays. The three-vertex gate uses Icarus Verilog with the host C++/Boost headers.

```sh
for qec_basis in x z; do
  python3 tools/b2_b7_p023_d6_axi_fused_query_record_v1.py \
    --basis "$qec_basis" --artifact-dir "$qec_artifacts" --archive "$qec_archive" \
    --build-parent "$qec_scratch" --java-home "$qec_jdk17" --verilator-prefix "$qec_verilator"
done
python3 tools/b2_b7_p023_d6_axi_fused_query_record_v1.py \
  --smoke --artifact-dir "$qec_artifacts" --archive "$qec_archive" \
  --build-parent "$qec_scratch" --java-home "$qec_jdk17"
python3 tools/b2_b7_p023_d6_axi_fused_query_audit_v1.py --artifact-dir results
```

## Limits

Sampled bus cycles exclude host software, transport and board timing. A pass does not establish full AXI coverage, multi-context ordering, CDC, FPGA utilization or clock rate, an end-to-end decoder deadline, full B2, scalable #023 or B7 resource credit. The 120-qubit/depth-7,000 question stays outside acceptance.

**Next test:** Run the same paired cohorts without forced AW/W gaps to test the counterfactual. Then evaluate the controller's command/retry contract and clock-rate/resource changes on a common target before interpreting the cycle saving as hardware acceleration.
