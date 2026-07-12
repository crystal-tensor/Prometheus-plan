# B4/B8 R130 Route-Signature Candidate Expansion

## Result

- Enumerated mappings: `30240`
- Available route signatures: `6720`
- Retained candidates: `312`
- Retained unique signatures: `282`
- Candidate training compilations: `2496`
- Total same-condition compilations: `2724`
- Selectors changed from R129: `2` / `6`
- Groups with positive unseen lower-20% delta: `1` / `6`
- Groups winning at least 8/10 unseen seeds: `1` / `6`
- Route-expansion unseen-seed gate passed: `False`
- Acceptance holdout executed: `False`
- New credit delta: `0`

## Per-Group Evidence

- `FakeJakartaV2` / `private_bundle_ghz_n6`: selected static rank `5` from `static_top10`, signature `53e7dfaff86c0cbc`; unseen lower-20%/mean/wins `-0.0159` / `-0.0175` / `0/10`; R129 unseen mean/wins `-0.0175` / `0/10`; selector changed `False`.
- `FakeJakartaV2` / `private_bundle_graph_n6`: selected static rank `1` from `static_top10`, signature `4c8d2e36572f3989`; unseen lower-20%/mean/wins `-0.0037` / `-0.0011` / `3/10`; R129 unseen mean/wins `0.0011` / `3/10`; selector changed `True`.
- `FakeLagosV2` / `private_bundle_ghz_n6`: selected static rank `241` from `route_signature_champion`, signature `a081c8a6c571175b`; unseen lower-20%/mean/wins `-0.0001` / `0.0116` / `5/10`; R129 unseen mean/wins `0.0048` / `3/10`; selector changed `True`.
- `FakeLagosV2` / `private_bundle_graph_n6`: selected static rank `1` from `static_top10`, signature `759e65fe731f82b1`; unseen lower-20%/mean/wins `0.0057` / `0.0074` / `10/10`; R129 unseen mean/wins `0.0074` / `10/10`; selector changed `False`.
- `FakeOslo` / `private_bundle_ghz_n6`: selected static rank `9` from `static_top10`, signature `4f9c7a923f8d88d8`; unseen lower-20%/mean/wins `-0.0032` / `-0.0019` / `0/10`; R129 unseen mean/wins `-0.0019` / `0/10`; selector changed `False`.
- `FakeOslo` / `private_bundle_graph_n6`: selected static rank `2` from `static_top10`, signature `2752091a409e4d0e`; unseen lower-20%/mean/wins `0.0000` / `0.0012` / `3/10`; R129 unseen mean/wins `0.0012` / `3/10`; selector changed `False`.

R130 enumerates every injective six-to-seven mapping. It retains the static
Top-10, then the best mapping from each route signature ordered by proxy route
length and static exposure, then uses static fill only when fewer than 50 rows
remain. A signature binds routed directed-edge multiplicities, proxy route
steps, and the excluded physical qubit. The 52 retained rows per group are
trained on eight new seeds; ten disjoint seeds are opened only after selection.

## Gate

Every group must have positive unseen mean and lower-20% exposure deltas and
win at least eight of ten unseen seeds. This remains compiler-design validation,
not the verifier acceptance holdout or evidence of protocol soundness.

## Requirements

- `P1` PASS: R129 source is hash-bound before candidate expansion
- `P2` PASS: all 30,240 injective mappings are enumerated
- `P3` PASS: 52 candidates are retained per snapshot/task group
- `P4` PASS: route signatures bind route steps, excluded qubit, and edge multiplicity
- `P5` PASS: all expanded candidates are compiled on eight training seeds
- `P6` PASS: ten disjoint validation seeds cover selected, default, and R129 layouts
- `P7` PASS: all 60 validation QASM artifacts preserve measurement order
- `P8` PASS: route-expansion gate is evaluated on all six groups
- `P9` PASS: verifier holdout, current calibration, and hardware remain excluded
- `P10` PASS: no soundness, advantage, BQP, or new credit is claimed

## Claim Boundary

Supported: deterministic route-signature expansion and disjoint-seed validation
over frozen historical snapshots. Not supported: verifier holdout performance,
readout mitigation, current calibration, provider access, hardware execution,
protocol soundness, quantum advantage, BQP separation, or new B10 credit.
