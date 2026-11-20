# B2/B7/#023 explicit 16-bit reweight adjudication v2

## Decision

Accepted classification: `sixteen_bit_explicit_reweight_semantic_pass_hardware_write_path_absent`.

The producer emitted `sixteen_bit_explicit_reweight_semantic_pass_hardware_write_path_absent` and the independent recomputation confirms that label. V2's executable `semantic_pass` includes the frozen all-window equality clause.

## What passed

All 2,048 final candidate frames equal the high-precision online and full-block references. Every commit and final residual count is zero. All base and implied stored weights are even and fit unsigned sixteen-bit storage.

## Window-exact result

X has `0` syndrome and `0` output mismatches among `167936` windows. Z has `0` syndrome and `0` output mismatches. All four cells are zero, so the semantic veto passes.

## Claim boundary and next gate

The 16-bit representation is admitted only as a strict software semantic bridge. No Micro Blossom dynamic-write RTL, cycle, FPGA, p99, full B2, scalable #023, or B7 credit is supported. The next gate is the missing hardware write path followed by exact replay and measured p99 cycles.

Independent audit checks: `19/19`. A fresh-subprocess replay passes `13/13` and reproduces the result, report, and producer Discussion draft byte-for-byte. Audit ID: `e9d1e1c51b3217bb24370564ea1a84028539967c803ab737ee940d0faaccfa2b`; replay ID: `d9e908e7c6f60693ae88a4b65bc037a6077ffc2a90d6e0b2bca2ed8513e258c0`.
