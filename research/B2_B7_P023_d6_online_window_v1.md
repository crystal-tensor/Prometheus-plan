# B2/B7/#023 Distance-6 Online Window Decoder v1

As of 2026-11-20. Scope is exactly #021/B7, #022/B2, and #023.

## Heuristic question

What survives when windowing preserves every correction but misses almost every deadline?

Public freeze: `057989cb707498d968a8d91bb44023c2a245a505` and Discussion #329.

| basis | decoder | prediction rows equal full block | prefix failures | p50 us/layer | p99 us/layer | deadline misses | online semantics + tail |
|---|---|---:|---:|---:|---:|---:|---|
| X | independent_mwpm | 1024/1024 | 14 | 4.333 | 9.368 | 99.97% | False |
| X | two_pass_correlated_matching | 1024/1024 | 5 | 4.708 | 9.035 | 99.97% | False |
| Z | independent_mwpm | 1024/1024 | 14 | 4.181 | 7.917 | 99.95% | False |
| Z | two_pass_correlated_matching | 1024/1024 | 2 | 4.792 | 9.375 | 99.96% | False |

All four online arms reproduce their frozen full-block predictions exactly: **4096/4096** prediction rows match, with zero committed-region or final residual-syndrome failures. The primary correlated online host proxy is nevertheless **False**. The frozen line is 1 microsecond per committed syndrome layer at nearest-rank p99, at most 1% deadline misses, exact prediction equality, and zero residual syndrome; latency alone vetoes acceptance.

## What was actually timed

Each sequential overlapping-recovery window spans `3d=18` syndrome layers and commits the oldest `d=6`. The timed response starts before bit packing, crosses an in-process Unix socket, performs the window decode and correction propagation, sends the logical-frame feedback through the reverse socket, and ends after acknowledgement. Sampling and graph construction are excluded.

## Boundary

This is a host-local synchronous socket emulator, not a QPU/controller integration. Hardware decoder deadline passed remains **False**; full B2, scalable #023 memory, and B7 resource credit remain closed.

Formal checks: **13/13**. An independently implemented auditor passes **18/18**, and a subprocess replay passes **12/12** while reproducing the audit artifact byte for byte. The audit covers 8 source chunks, 4 online arms, and 4096 prediction rows. Evidence ID: `56c09cbc2e1a29d12428d48de636b9000b8021cd77d545d2cedc3cca215401ab`.

## Next gate

The semantics survived, so the next preregistered experiment should isolate decoder time from Python packing, synchronous per-window socket transport, commit propagation, and acknowledgement. A preallocated/native or asynchronous path may test whether the missed clock is an implementation boundary rather than a decoder boundary. Hardware, full B2, #023, and B7 remain open either way.
