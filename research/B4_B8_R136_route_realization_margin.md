# B4/B8 R136 Route-Realization Lower-Tail Margin

## Result

- R135 residual losses: `7`
- R135 loss-margin range: `0.00002775` to `0.00563632`
- Top mapping/policy candidates per group: `8`
- Realization seeds per candidate: `16`
- Route-realization compilations: `1536`
- New automatic validation compilations: `120`
- Groups improved over R135 selected exposure: `8` / `12`
- Selected-QASM replay: `12` / `12`
- Wins/ties/losses vs automatic layout: `116/4/0`
- No-loss groups: `12` / `12`
- Automatic-baseline no-loss gate: `True`
- New credit delta: `0`

## Validation Evidence

- `FakeJakartaV2` / `dense_validation_complete_ising_n6`: selected `[1, 3, 0, 2, 5, 6]` / `selected_o3_default` / seed `13610`; improvement vs R135 `+0.016730`; validation wins/ties/losses `10/0/0`; replay `True`.
- `FakeJakartaV2` / `dense_validation_inverse_qft_n6`: selected `[0, 1, 2, 6, 3, 5]` / `selected_o3_default` / seed `13601`; improvement vs R135 `+0.000000`; validation wins/ties/losses `10/0/0`; replay `True`.
- `FakeJakartaV2` / `dense_validation_scrambled_qft_n6`: selected `[5, 0, 3, 6, 2, 1]` / `selected_o3_default` / seed `13601`; improvement vs R135 `+0.000000`; validation wins/ties/losses `8/2/0`; replay `True`.
- `FakeJakartaV2` / `dense_validation_xy_network_n6`: selected `[0, 1, 3, 2, 5, 6]` / `selected_o3_default` / seed `13601`; improvement vs R135 `+0.000000`; validation wins/ties/losses `10/0/0`; replay `True`.
- `FakeLagosV2` / `dense_validation_complete_ising_n6`: selected `[5, 3, 6, 4, 1, 0]` / `selected_o3_default` / seed `13610`; improvement vs R135 `+0.003359`; validation wins/ties/losses `10/0/0`; replay `True`.
- `FakeLagosV2` / `dense_validation_inverse_qft_n6`: selected `[4, 5, 2, 0, 3, 1]` / `selected_o3_default` / seed `13610`; improvement vs R135 `+0.005989`; validation wins/ties/losses `10/0/0`; replay `True`.
- `FakeLagosV2` / `dense_validation_scrambled_qft_n6`: selected `[1, 6, 5, 0, 4, 3]` / `selected_o3_default` / seed `13603`; improvement vs R135 `+0.005069`; validation wins/ties/losses `9/1/0`; replay `True`.
- `FakeLagosV2` / `dense_validation_xy_network_n6`: selected `[6, 4, 5, 3, 1, 0]` / `selected_o3_default` / seed `13609`; improvement vs R135 `+0.003837`; validation wins/ties/losses `10/0/0`; replay `True`.
- `FakeOslo` / `dense_validation_complete_ising_n6`: selected `[1, 3, 2, 0, 5, 4]` / `selected_o3_default` / seed `13610`; improvement vs R135 `+0.018890`; validation wins/ties/losses `10/0/0`; replay `True`.
- `FakeOslo` / `dense_validation_inverse_qft_n6`: selected `[4, 5, 0, 2, 3, 1]` / `selected_o3_default` / seed `13610`; improvement vs R135 `+0.018890`; validation wins/ties/losses `10/0/0`; replay `True`.
- `FakeOslo` / `dense_validation_scrambled_qft_n6`: selected `[5, 0, 1, 4, 2, 3]` / `selected_o3_default` / seed `13603`; improvement vs R135 `+0.001576`; validation wins/ties/losses `9/1/0`; replay `True`.
- `FakeOslo` / `dense_validation_xy_network_n6`: selected `[2, 0, 5, 4, 1, 3]` / `selected_o3_lookahead` / seed `13601`; improvement vs R135 `+0.000000`; validation wins/ties/losses `10/0/0`; replay `True`.

R136 consumes only the R135 portfolio ledger while choosing candidates. The top
eight mapping/policy rows in each group are recompiled under sixteen new route
realization seeds. The minimum historical exposure realization is frozen before
the disjoint automatic validation seeds are opened. No R135 validation loss row
or R136 validation baseline is used during selection.

## Requirements

- `P1` PASS: R135 source and its seven residual losses are hash-bound
- `P2` PASS: top-eight candidate contract is complete for all groups
- `P3` PASS: realization and validation seed blocks are fresh and disjoint
- `P4` PASS: all 1,536 route realizations are materialized
- `P5` PASS: selection reads neither R135 loss rows nor R136 validation baselines
- `P6` PASS: all 12 groups have complete ten-seed validation ledgers
- `P7` PASS: all 12 selected QASM files replay in a fresh process
- `P8` PASS: automatic-baseline no-loss verdict is evaluated without promotion
- `P9` PASS: verifier acceptance, mitigation, calibration, and hardware remain excluded
- `P10` PASS: no soundness, advantage, BQP, or new credit is claimed

## Claim Boundary

Supported: route-realization lower-tail evidence for the seven residual R135
compiler losses under a validation-blind selection contract. Not supported:
verifier acceptance, causal hardware performance, current calibration,
mitigation, protocol soundness, quantum advantage, BQP separation, or new B10 credit.
