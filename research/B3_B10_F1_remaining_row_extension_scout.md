# B3/B10 F1 Remaining Row Extension Scout

- Target: `T-B3-024/T-B10-015k`
- Method: `b3_b10_f1_remaining_row_extension_scout_v0`
- Status: `f1_remaining_row_extension_scout_blocked_zero_credit`
- Extension scout hash: `0f2e416cd0acfcb0326663667e33f0c0cd09a0db6ce509c4450d440714d2c414`

## Result

The scout identifies the three remaining F1 row-extension targets from the cross-molecule pressure run. It passes 7/10 requirements and intentionally fails ['P8', 'P9', 'P10'] because the LiH/H2O/N2 rows are bounded pressure previews, not acceptable full compiled-state covariance rows.

## Remaining Rows

| molecule | pilot groups | max rel err | optimizer shots lower bound | blocked reasons |
|---|---:|---:|---:|---|
| lih_bond_stretch | 1 | 0.033126631853785865 | 475043013690000 | full_compiled_state_covariance_not_computed, bounded_high_coefficient_subset_not_full_pauli_cover, one_parameter_seed_not_converged_multi_parameter_state, no_same_access_denominator_win |
| h2o_symmetric_oh_stretch | 24 | 0.50293717180872 | 79665679020000 | full_compiled_state_covariance_not_computed, bounded_high_coefficient_subset_not_full_pauli_cover, one_parameter_seed_not_converged_multi_parameter_state, no_same_access_denominator_win |
| n2_bond_stretch | 8 | 0.08567232375979089 | 458402151950000 | full_compiled_state_covariance_not_computed, bounded_high_coefficient_subset_not_full_pauli_cover, one_parameter_seed_not_converged_multi_parameter_state, no_same_access_denominator_win |

## Requirement Results

- `P1` PASS: Cross-molecule pressure source is valid
- `P2` PASS: Prior H2 F1 pilot candidate remains valid
- `P3` PASS: Four row-aligned molecules are identified across prior candidate and pressure scout
- `P4` PASS: Remaining LiH/H2O/N2 extension rows are enumerated
- `P5` PASS: Each remaining row has sampled pressure preview evidence
- `P6` PASS: Each remaining row keeps optimizer-loop cost pressure charged
- `P7` PASS: No reaction-dynamics, denominator-win, quantum-advantage, or B10 credit claim is made
- `P8` FAIL: Remaining rows satisfy F1 full-covariance acceptance requirements
- `P9` FAIL: F1 has four acceptable row candidates
- `P10` FAIL: Four-row F1 artifact is submitted and accepted

## Claim Boundary

- Supported: The remaining LiH, H2O, and N2 row-extension targets are identified from cross-molecule pressure evidence, with sampled preview and optimizer-cost ledgers.
- Not supported: The remaining rows are not acceptable F1 rows because they use bounded subset pressure rather than full compiled-state covariance, are not converged multi-parameter states, and do not beat same-access denominators.
- Next gate: For each remaining molecule, compute full compiled-state covariance over the full QWC cover, preserve replay hashes, then resubmit the four-row F1 artifact.

This scout does not claim a reaction-dynamics solution, quantum advantage, B3 reopen credit, B10-T1 credit, or BQP separation.

## Validation

- validation_error_count: `0`
