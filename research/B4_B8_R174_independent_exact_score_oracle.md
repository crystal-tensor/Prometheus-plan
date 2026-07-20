# B4/B8/B10 R174 Independent Exact-Score Oracle

- Status: `independent_exact_score_oracle_complete`
- Classification: `independent_fraction_reproduction_of_fixed_grid_comparator`
- Requirements: `10/10`
- Payload hash: `2c7e5c4f3499e32f6ab322ed150b47bc2311ded0d99c2889e96380dfd2432018`

## Result

A standard-library `Fraction` implementation, without importing Qiskit or the R174 comparator, reproduces `576/576` row records and `1728/1728` candidate totals. It also passes `3456/3456` permutation checks and the R160 4/4 tie plus 28/28 non-tie guardrail.

## Claim Boundary

This independently validates the frozen replay arithmetic and selection semantics. It is not an integrated source patch, production performance result, confirmed Qiskit bug, hardware result, quantum advantage, BQP separation, solved frontier, or new credit.
