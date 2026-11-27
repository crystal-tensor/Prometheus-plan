# Does an AXI stall split one quantum-decoder result into two versions?

Date: 2026-11-27

Scope: #021/B7, #022/B2, #023 only

## Experiment

The completed X/Z denominator exercises the same phase-banked `DistributedDual` core through direct simulator access. This pilot puts a single-clock, single-context AXI4-Lite32 endpoint between the unchanged Rust primal/feedback path and that core. Each write address and write datum can arrive separately. A successful write response fences the underlying operation; a read response owns its registered data until it is consumed. These are bounded functional tests of the channel handshakes described in [Arm's AXI specification, §A3.2](https://developer.arm.com/documentation/ihi0022/h/), not an AXI compliance certificate.

The endpoint accepts reset, opening/steady/closing phase selection, defect/solver instructions, resident weight selectors, correction clear and XOR-edge commands, and a correction snapshot. The host reads the obstacle registers through AXI and assembles the correction from little-endian 32-bit words with a phase, width, and snapshot generation check. The sole direct observation in the ordinary trajectory is the existing non-driving vertex occupancy assertion. The X closing vector has 789 bits, the Z closing vector 788; each uses 25 bus words.

| Condition | Fixed test |
| --- | --- |
| Address/data decoupling | Observe AW first, W first, and simultaneous acceptance. Balance AW, W, and B counts; balance AR and R. |
| Write response stall | Hold the next command VALID while the current B is pending. Require the next phase change to complete only after the prior response retires. |
| Read response stall | Hold a nonzero correction word while switching phase and publishing a new, zero correction snapshot. Require the older R beat to retain its data and the new snapshot to report the new phase. |
| Rejected operations | Six invalid writes (including invalid phase, partial strobe, edge range, unaligned address and bare sideband opcode) and two invalid reads receive SLVERR. Recheck the phase and every correction word after rejection. |
| Semantic parity | Compare every opening, steady and closing case, including selected subgraph and correction bits, with the accepted direct RTL run on the same input. Check occupancy, residuals and final frames. |

During development, the stall monitor was also checked against a local small-graph variant in which correction reads tapped the mutable snapshot rather than the registered R beat. That variant failed on a changing R response. It is not part of the X/Z denominator.

## Result

Both complete pilot runs pass. The two raw JSON files are byte-identical to their respective direct baselines, and the audit independently reconciles every start and solve event with its window row.

| Basis | Frozen shots | Matched windows | Occupancy checks | Write transactions | Read transactions | Correction words |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| X | 0, 15 | 328 | 3,254 | 17,427 | 17,323 | 2,658 |
| Z | 0–7 | 1,312 | 13,498 | 72,057 | 71,132 | 10,632 |
| Total | 10 | 1,640 | 16,752 | 89,484 | 88,455 | 13,290 |

All commit-residual, final-residual, and final-frame failure counts are zero. The measured acceptance order covers 29,826 AW-first, 29,826 W-first, and 29,832 simultaneous writes. There are 223,711 stalled B sampling cycles and 265,390 stalled R sampling cycles; these count the injected simulation schedule, not hardware latency. Transaction totals include the directed probes and their expected error responses.

The replayable [joint evidence](../results/B2_B7_P023_d6_axi_lite32_pilot_evidence_v1.json) has ID `b6f25afc00c1ad39e68f51504c2438d5aadc0b5cd5b8a3b34cae8d5ca7e40a32`.

## Reproduce

From the repository root, use the [replay/audit tool](../tools/b2_b7_p023_d6_axi_lite_replay_v1.py). It extracts the [pinned source archive](https://api.github.com/repos/yuewuo/micro-blossom/tarball/a3530d9e58ff790dafc93d56c9a2769ceac84731) into an isolated directory, verifies the original closed-loop patch hash, and applies the additive AXI host patch. The experiment uses Java 17, SpinalHDL 1.9.3, Verilator 5.040, and the frozen selector environment (Python 3.12, Stim 1.16.0, PyMatching 2.4.0). The [compiler compatibility patch](../tools/microblossom/verilator_5_040_darwin_compat_v1.patch) resolves an overload ambiguity in the Verilator build on the tested Darwin toolchain; it does not change the decoder source.

```sh
python3 tools/b2_b7_p023_d6_axi_lite_replay_v1.py replay \
  --artifact-dir "$qec_artifacts" --archive "$qec_archive" --build-parent "$qec_scratch" \
  --java-home "$qec_jdk17" --verilator-prefix "$qec_verilator"
python3 tools/b2_b7_p023_d6_axi_lite_replay_v1.py audit --artifact-dir results
```

For a short preflight, place [the three-vertex smoke fixture](../tools/microblossom/D6PhaseAxiSmoke.scala) in `src/fpga/microblossom/` in the prepared source tree and run `sbt -batch 'runMain microblossom.D6PhaseAxiSmoke'` with Icarus Verilog. That fixture also forces bit 31 high in a 32-bit word to catch sign extension or word-order errors, and issues an independent read while a write address is waiting for its datum.

The normal replay records the generated endpoint hash before Rust removes its simulator directory. The initial X capture was finalized after that cleanup; its unchanged capture is linked to a separate observation of the actual RTL file, made and hashed before the X replay exited.

## What this cannot establish

The pilot does not establish full AXI coverage of the frozen X/Z corpora, multi-context ordering, clock-domain crossing, FPGA timing or utilization, measured decoder p99/miss rate, full B2, scalable #023, or B7 resource credit. The 120-qubit/depth-7,000 capacity question is outside the acceptance design. Host simulation elapsed time and AXI simulated-clock counts are not hardware latency.

The next performance experiment should freeze separate no-stall and backpressure schedules and record per-window cycle boundaries for command, solve, and readout. The 25 data words in each closing snapshot exclude metadata and obstacle responses. Measure what drives the tail before choosing a packed correction path or a less serialized obstacle readout.
