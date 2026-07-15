# B1/B7 Cone01 R118 Randomized Channel Fingerprint Gate

## Summary

- Target: `T-B1-004hp/T-B7-016y`
- Upstream target: `T-B1-004ho/T-B7-016x`
- Method: `b1_b7_cone01_r118_randomized_channel_fingerprint_gate_v0`
- Status: `cone01_r118_randomized_channel_fingerprint_160_probe_accepted`
- Source/Candidate CX: `762 -> 528`
- Probe families: `{'basis': 32, 'haar': 64, 'product': 32, 'ghz_endpoint': 16, 'biased': 16}`
- Candidate probes: `160/160`
- Maximum fidelity deficit: `2.4424906541753444e-15`
- Negative-control failures: `16/16`
- B7 credit: `0`

R118 uses the independent NumPy gate engine, not Qiskit compilation, to
fingerprint the R116 source/candidate pair over basis, Haar-like, product,
endpoint-entangled, and biased input states. A deliberately modified candidate
is required to fail the same harness, preventing a vacuous all-pass result.

This is stronger finite numerical evidence, not a symbolic or formal proof of
arbitrary-input unitary equality. It does not establish mid-circuit
measurement semantics, hardware layout improvement, T-resource reduction, or
B7 credit.

## Requirements

- `P1` PASS: accepted R116 artifact is the input
- `P2` PASS: independent NumPy engine is used without Qiskit compilation
- `P3` PASS: candidate has a nonzero two-qubit reduction
- `P4` PASS: cross-type probe set has the declared 160 rows
- `P5` PASS: all candidate fingerprint probes pass
- `P6` PASS: candidate fingerprint stays within tolerance
- `P7` PASS: negative control is detected by the same harness
- `P8` PASS: source terminal measurement map is preserved
- `P9` PASS: fingerprint and negative-control artifacts are materialized
- `P10` PASS: B7 credit remains zero
- `P11` PASS: claim boundary excludes formal arbitrary-input proof
- `P12` PASS: source and candidate have the same qubit count

## Claim Boundary

Supported: R116 survives a 160-probe cross-type independent NumPy channel
fingerprint and the negative control is detected. Not supported: an exact
arbitrary-input theorem, hardware evidence, T-resource reduction, or B7
ledger credit.
