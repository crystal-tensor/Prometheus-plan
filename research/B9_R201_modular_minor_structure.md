# B9 R201 Eight-Minor Two-Prime Structure Replay

- Date: `2026-10-31`
- Track: `B9`
- Status: `public modular structure replay verified; characteristic-zero certificate incomplete`
- Characteristic-zero engineering certificate verified: `false`
- Ideal-membership certificate verified: `false`
- Frozen holdouts executed: `false`
- Readiness blocker closed: `false`
- Scientific promotion: `false`
- New credit: `0`

## Question

Can four degree-184 engineering minors be reduced to a smaller exact lifting target without mistaking repeated finite-field structure for a characteristic-zero theorem?

## Eight Bound Artifacts

The public `J=13/32`, `n=4` matrix supplies four frozen `37x37` row sets. Each determinant was computed over both `GF(1,000,003)` and the safe prime `GF(536,870,723)`, where `536,870,723 = 2 * 268,435,361 + 1`.

The eight artifacts retain total degree `184`. Their nonzero term counts are stable across both primes:

| Minor | Frozen row hash | Terms |
| --- | --- | ---: |
| 0 | `25251233...` | 8,649 |
| 1 | `636ee939...` | 4,468 |
| 2 | `7d38cb52...` | 4,770 |
| 3 | `b421e430...` | 2,760 |

The complete artifact bundle hash is `fa4925cde2b9e4903381f15635720561757b62ba6092dfd1b09f42d8b3206398`.

## Independent Replay

`tools/b9_r201_modular_minor_structure.py` does not trust the bridge artifact's `checked` field. For every artifact it:

1. reconstructs the bound source matrix and frozen row set;
2. evaluates the stored polynomial at five public deterministic points;
3. independently evaluates the `37x37` matrix at the same points;
4. computes each modular determinant with project-owned Gaussian elimination;
5. asks Singular only for finite-field factor discovery;
6. multiplies every normalized factor back with project-owned sparse arithmetic;
7. checks row, matrix, candidate-label, bridge-tool, term, and artifact hashes.

All `40/40` point replays match. Every minor has at least three nonzero replay points. All `8/8` factorizations multiply back to the original polynomial exactly, and all artifact bindings are clean.

## Stable Structure

The factor degree/multiplicity pattern is identical at both primes for every minor. More importantly, the greatest common factor across all four minors is exactly `D^44 = (a^2 + b^2 + c^2)^44`:

```text
D^44 = (a^2 + b^2 + c^2)^44
```

at both primes. It has degree `88`. Removing it leaves four degree-`96` residuals with term counts:

| Minor | Residual degree | Residual terms |
| --- | ---: | ---: |
| 0 | 96 | 2,401 |
| 1 | 96 | 464 |
| 2 | 96 | 590 |
| 3 | 96 | 450 |

This exposes a smaller quotient after characteristic-zero divisibility is proved, but it does not yet reduce the unconditional CRT target. Two agreeing primes cannot replace an integer coefficient bound, exact determinant reconstruction, and exact division over `ZZ[a,b,c]`.

## What This Does and Does Not Validate

This is evidence about classical symbolic representations of a quantum many-body commutator problem. It does not require quantum hardware because it does not claim hardware behavior. Trust comes from exact algebra, two independent execution paths, hash-bound inputs, public replay points, factor-product reconstruction, and explicit rejection of stronger conclusions.

The result does not verify the characteristic-zero determinants, emit an ideal-membership certificate, certify either frozen coupling, exclude higher-order charges or nonlocal dualities, prove interacting nonintegrability, establish Quantum PCP or NLTS, separate BQP, claim hardware relevance, solve the frontier, promote the result, or add credit.

## Next Gate

1. Prove an unconditional coefficient bound for each degree-184 integer determinant.
2. Add enough preregistered primes that the CRT modulus exceeds twice the bound.
3. Reconstruct the integer determinants and replay each identity independently.
4. Verify exact `D^44` division and compute the characteristic-zero gcd.
5. Emit the `J=13/32` ideal-membership certificate and bind its generators to the frozen dense minors.
6. Run the pre-source reconstruction in an isolated filesystem before changing holdout permissions.
