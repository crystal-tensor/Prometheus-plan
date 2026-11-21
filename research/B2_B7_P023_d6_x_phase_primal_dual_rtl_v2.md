# B2/B7/#023 X phase-aware primal/dual RTL v2

As of 2026-11-21. Scope is exactly #021/B7, #022/B2, and #023.

## Research question

Can one X-basis Micro Blossom image switch among opening, steady, and closing phase banks, accept causal resident-weight selectors, run the Rust primal against the real SpinalHDL `DistributedDual`, and reproduce complete reference subgraphs and correction bits without corrupting syndrome loading?

## Two correctness falsifiers found before acceptance

The first long run was invalid. Phase-local edge `1401` (superset edge `1901`) had weight `12037`; the odd value made the integer dual-growth calculation round down. The repaired input scales every phase edge, resident-rule replacement, and vertex-growth bound by two. All values consumed by the Micro Blossom growth domain are now even.

The repaired weights exposed a second bug. For the opening/maximum case, selector `810` makes superset edge `940`—joining vertices `587` and `474`—zero weight. When selectors were committed before the syndrome was completely loaded, defect node `4` propagated from vertex `587` into vertex `474`; the later `AddDefect(474, 6)` then targeted an occupied vertex. The earlier apparently correct output was therefore rejected.

The accepted ordering is explicit: reset and select the phase, load every syndrome defect, commit queued resident selectors, and only then perform the first obstacle search. Both the software comb control and the real RTL path use this ordering.

## Accepted representative result

| Gate | Result |
|---|---:|
| Frozen X representatives | 12/12 |
| Phases | opening, steady, closing |
| Boundaries per phase | zero, p50, p99, maximum |
| AddDefect precondition checks | 177/177 clear |
| Syndrome checks | 12/12 pass |
| Complete corrections | 12/12 exact |
| Complete reference subgraphs | 12/12 exact |
| Maximum resolved obstacles | 21 |
| Independent comb control | 12/12 pass |
| Evidence audit | 264/264 pass |

RTL iteration counts are:

- opening: `0 / 4 / 12 / 21`
- steady: `0 / 6 / 13 / 17`
- closing: `0 / 5 / 15 / 20`

The captured run exits with code zero. Its forbidden-error list and unexpected-warning list are both empty. Two non-fatal simulator messages are classified explicitly: unused-signal pruning during Verilog generation and one startup-time Icarus `z`-to-`0` conversion. Neither occurs as an `AddDefect` failure, RTL assertion, panic, or result mismatch.

## Reproducible evidence

- Fixed input evidence ID: `486c68356642f6ed62dc163d4bcad5f7e0cd40d3ff9bfb5c66600d47d2b3e121`
- Accepted evidence ID: `e087c536009174d355f44a1b479d403781a1b77c38294209ec4dcbe99440ccbe`
- Pinned Micro Blossom commit: `a3530d9e58ff790dafc93d56c9a2769ceac84731`
- Exact 13-file source patch SHA-256: `fd53fd5f6b90751cfaf78808f91b5f95b3981c174fe55689cfa20ccc9ea59230`
- Captured RTL output SHA-256: `ed42a907557862163b45084261758bf6c0a385e82df366051041a4ce99486dbd`
- Captured log SHA-256: `55d7cb4c43cc9ccef9f86f2f73b96fa8dd6af4916f9be55b6e2aed1de581b7a2`

The source patch replays exactly against the pinned source archive. The capture metadata binds the archive, patch, input, raw output, log, exit code, warning classification, and occupancy audit.

## Claim boundary

This closes only the representative X correctness gate for the Rust-primal plus real phase-aware `DistributedDual` path. It is not a full-corpus result and the 50.9-second Icarus execution time is not hardware latency.

The following remain false or open:

- complete accepted X-corpus execution;
- independent Z phase banks and end-to-end correction;
- AXI phase control and correction readout;
- FPGA synthesis, Fmax, LUT/BRAM, routing, or measured latency;
- p99 `<= 1 us` per committed layer and miss rate `<= 1%`;
- full B2, scalable #023, and any B7 resource credit.

## Next falsifier

Run every accepted X case through the same defect-first selector-commit path. If that passes, build independent Z banks and repeat the complete subgraph/correction audit before admitting AXI or FPGA performance evidence.
