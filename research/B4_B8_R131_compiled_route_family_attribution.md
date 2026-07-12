# B4/B8 R131 Compiled Route-Family Attribution

## Result

- Diagnostic recompilations: `120`
- Python hash seed: `0`
- Selected QASM replay matches: `60` / `60`
- Selected route-exposure families: `9`
- Automatic-layout route-exposure families: `33`
- Groups with selected family invariant: `4` / `6`
- Groups with automatic family switching: `6` / `6`
- Groups whose outcome instability is attributed to automatic-family switching: `4` / `6`
- Diagnostic rows matching R130 deltas: `60` / `60`
- Acceptance or selection performed: `False`
- New credit delta: `0`

## Per-Group Evidence

- `FakeJakartaV2` / `private_bundle_ghz_n6`: selected/default route-exposure classes `3/7`; family pairs `8`; selected invariant `False`; default switches `True`; wins/ties/losses `0/0/10`; outcome-varying default families `0`; baseline-switch attribution `False`.
- `FakeJakartaV2` / `private_bundle_graph_n6`: selected/default route-exposure classes `2/4`; family pairs `7`; selected invariant `False`; default switches `True`; wins/ties/losses `1/5/4`; outcome-varying default families `3`; baseline-switch attribution `False`.
- `FakeLagosV2` / `private_bundle_ghz_n6`: selected/default route-exposure classes `1/7`; family pairs `7`; selected invariant `True`; default switches `True`; wins/ties/losses `3/5/2`; outcome-varying default families `0`; baseline-switch attribution `True`.
- `FakeLagosV2` / `private_bundle_graph_n6`: selected/default route-exposure classes `1/4`; family pairs `4`; selected invariant `True`; default switches `True`; wins/ties/losses `8/2/0`; outcome-varying default families `0`; baseline-switch attribution `True`.
- `FakeOslo` / `private_bundle_ghz_n6`: selected/default route-exposure classes `1/7`; family pairs `7`; selected invariant `True`; default switches `True`; wins/ties/losses `0/4/6`; outcome-varying default families `0`; baseline-switch attribution `True`.
- `FakeOslo` / `private_bundle_graph_n6`: selected/default route-exposure classes `1/4`; family pairs `4`; selected invariant `True`; default switches `True`; wins/ties/losses `3/7/0`; outcome-varying default families `0`; baseline-switch attribution `True`.

A route-exposure family binds the directed physical CX-edge multiset, CX count,
and compiled combined exposure. Cross-process QA found that exact ordered CX
sequences and measurement maps can drift even with the same transpiler seed;
R131 therefore does not claim exact ordered-route reproducibility. It recompiles
the selected and automatic layouts on the already-used R130 validation seeds,
without opening a new seed block, tuning a selector, or running the verifier holdout.

## Requirements

- `P1` PASS: R130 source is hash-bound and its exact seed block is reused
- `P2` PASS: process hash seed is fixed and both layouts are recompiled for all rows
- `P3` PASS: all selected recompilations byte-match stored R130 QASM
- `P4` PASS: all exposure deltas match the R130 ledger
- `P5` PASS: route-exposure families bind CX edge multisets and compiled exposure
- `P6` PASS: every group has a complete ten-seed route-family ledger
- `P7` PASS: all 60 automatic-layout QASM observations are frozen
- `P8` PASS: diagnostic reuse opens no new seed block and performs no selection
- `P9` PASS: verifier holdout, mitigation, current calibration, and hardware remain excluded
- `P10` PASS: no soundness, advantage, BQP, or new credit is claimed

## Claim Boundary

Supported: post-hoc attribution of R130 compiler-seed outcomes to reproducible
route-exposure equivalence classes with byte-level selected-QASM replay. Not supported: causal
hardware claims, new selector acceptance, verifier holdout performance, readout
mitigation, current calibration, provider access, hardware execution, protocol
soundness, quantum advantage, BQP separation, or new B10 credit.
