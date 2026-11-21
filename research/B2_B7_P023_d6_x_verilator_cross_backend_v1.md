# Cross-backend X-corpus RTL replay: nine frozen shots

Date: 2026-11-21  
Scope: #021/B7, #022/B2, #023 only

## Question

If a faster RTL simulator reproduces the accepted Icarus result byte-for-byte, can simulator choice be removed as a correctness variable and treated only as execution cost?

## Frozen denominator

- Basis: X only.
- Corpus: 1,024 shots × 164 consecutive windows = 167,936 cases.
- Accepted corpus SHA-256: `86185652355a9197eabc0503945820837dbf497ff822812f37f47a0e26836e89`.
- Accepted prediction SHA-256: `3c9e23b747a0527ad15a042954a1cf7a6c1be31501450c7c3e0b1366360e1331`.
- No corpus, phase, selector, correction, or acceptance rule changed.

## Backend compatibility route

The pinned implementation remains Micro Blossom commit `a3530d9e58ff790dafc93d56c9a2769ceac84731`. SpinalHDL 1.9.3 generated wrappers require the legacy `WData` interface, so the compatible backend is Verilator 5.040 rather than the system Verilator 5.054. The v8 source patch adds an environment-selected phase simulator and compiles Verilator with C++14 plus `VL_TIME_CONTEXT`; the latter avoids a legacy `sc_time_stamp()` callback before SpinalHDL initializes its thread-local simulation handle.

Exact v8 patch SHA-256: `53db7a175be9938881df182f8bfbd466b9a549c5b4f0e60dd0fbb1c7cb63c767`.

## Replay-equivalence result

Shot 0 was executed through both Icarus 13.0 and Verilator 5.040. The complete output JSON files are byte-identical:

- Icarus output SHA-256: `aca01e62906d01664872ecb3e934f8ea6fa09f6e9d82b692c920436aa399a153`.
- Verilator output SHA-256: `aca01e62906d01664872ecb3e934f8ea6fa09f6e9d82b692c920436aa399a153`.
- Cases: 164/164 syndromes valid and 164/164 complete corrections bit-exact.
- Occupancy: 1,648/1,648 checks clear.
- Iterations: 946 total, 15 maximum.

This equality covers every serialized case field, including phase, shot/window identity, defects, selectors, local and superset subgraph edges, correction hex, validity flags, and iteration counts.

## Persistent eight-shot result

Shots 1–8 then ran in one Verilator-hosted process:

- Cases: 1,312/1,312 syndromes valid and complete corrections bit-exact.
- Occupancy: 12,990/12,990 checks clear.
- Selectors: 7,217.
- Iterations: 7,500 total, 18 maximum.
- Forbidden errors: 0.
- Unexpected warnings: 0.
- Formal capture gate: accepted.

Together with shot 0, the tested denominator is now 9/1,024 shots, or 1,476/167,936 cases. Exactly 1,015 shots and 166,460 cases remain.

## Software-simulation cost

- Icarus shot-0 simulation body: 439.699413 s.
- Verilator shot-0 simulation body: 7.382773 s.
- Like-for-like body speedup: 59.557×.
- Verilator eight-shot simulation body: 57.553113 s.
- Persistent body cost: 7.194139 s/shot, or 0.0438667 s/case.
- Linear 1,024-shot persistent-body projection: 2.046 h.

These durations are software-host simulation costs. They are not decoder hardware latency, FPGA timing, or evidence for the `p99 <= 1 us` target.

## Acceptance boundary

Accepted now:

- Verilator is replay-equivalent to Icarus for the complete frozen shot-0 output.
- Nine frozen X shots pass the real Rust-primal plus phase-aware DistributedDual path.
- The execution route is fast enough to make an unchanged full-X run practical.

Not accepted:

- The remaining 1,015 X shots.
- Any Z-basis phase-bank or correction result.
- AXI phase control or correction readout.
- FPGA synthesis, Fmax, LUT/BRAM, routing, or measured hardware latency.
- `p99 <= 1 us`, miss rate `<= 1%`, full B2, scalable #023, or B7 resource credit.

Machine audit evidence ID: `a197aa85dceaac69238da847b6207a49936ad10502125451945bfee63ee25538` (19/19 checks).

## Next falsifier

Execute the remaining 1,015 frozen X shots through the replay-equivalent Verilator path without changing the corpus, phase banks, selector sequence, reference corrections, or acceptance rules. Only the complete 167,936/167,936 result can close the X-corpus correctness gate.
