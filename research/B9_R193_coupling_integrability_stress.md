# B9 R193 Coupling and Integrability Stress

## Verdict

- Status: `checked_holdout_spectral_crossover_candidate`
- Requirements: `17/17`
- Protocol hash: `dadb6c6ca406e87ea59fa4acdb951d55e49a22e4be9f4b20dbb4dfef3fe2fe54`
- Payload hash: `804704276e368ad9d8d9471068ae0849261c79ffe63fe34e339cfca4dea4d9fd`
- Transcript hash: `facc611e38cae188d17cc81732014d26f6c2cf01729f2d386d4107ec98acf078`
- Scoped holdout crossover candidate accepted: `true`
- Scientific promotion accepted: `false`
- New credit delta: `0`

## Honest Pilot/Holdout Boundary

The pilot grid was observed before this protocol was frozen. It is
therefore reported as exploratory evidence only and contributes
`zero` acceptance decisions. The confirmatory decision uses only the
six previously unopened rational holdout couplings.

## Holdout Coupling Summary

| J | rows | simple | tail median r | reference closer | norm-gap ratio range |
|---:|---:|---:|---:|---|---:|
| 3/16 | 5 | 5 | 0.446041 | poisson_like_reference_closer | 0.8024..0.8119 |
| 5/16 | 5 | 5 | 0.461109 | goe_like_reference_closer | 0.6753..0.6926 |
| 7/16 | 5 | 5 | 0.485233 | goe_like_reference_closer | 0.5547..0.5809 |
| 9/16 | 5 | 5 | 0.510468 | goe_like_reference_closer | 0.4429..0.4786 |
| 11/16 | 5 | 5 | 0.533591 | goe_like_reference_closer | 0.3416..0.3871 |
| 7/8 | 5 | 5 | 0.533209 | goe_like_reference_closer | 0.2138..0.2712 |

- Nonzero holdout simple-spectrum rows: `30/30`.
- Weak holdout Poisson-like classifications: `1/1`.
- Strong holdout GOE-like classifications: `4/4`.
- Holdout normalized-gap improvements over R191: `0/30`.

The transition coupling is displayed but excluded from every
acceptance count. The GOE/Poisson labels are finite-size reference
comparisons, not a quantum-chaos theorem.

## Exact Local-Charge Adversary

For each declared row, the search spans identity plus every Pauli word whose minimal contiguous support interval has length at most four. The commutator matrix is integer-valued.

- Nonzero holdout exact-nullity-two rows: `30/30`.
- Zero-coupling extensive-control rows: `5/5`.
- Every nonzero holdout row contains the explicit identity and Hamiltonian kernels. Rank `ncols-2` modulo both declared primes certifies that no third rational conserved operator exists inside the complete range-four ansatz.
- At `J=0`, identity plus `n` independent tilted-site blocks are verified exact rational kernels, so the adversary detects the known integrable control.

## Standard Jordan-Wigner Axis Obstruction

- Tilted field vector: `(-1, 0, 3/4)`.
- Ising coupling axis: `(0, 0, 1)`.
- Exact dot product: `3/4`.
- Exact squared alignment: `9/25`.
- Lean proves that every dot-product-preserving on-site rotation preserves this nonzero overlap. It therefore cannot make the field axis orthogonal to the coupling axis, the declared necessary condition for a standard parity-preserving quadratic Jordan-Wigner alignment.

This does not exclude nonlocal dualities, higher-range quasi-local
charges, interacting Bethe-ansatz structure, auxiliary-mode
fermionizations, or any other integrability mechanism outside the
declared route.

## Supported

- A pilot/holdout split with acceptance based only on unopened holdout couplings
- Exact independent matrix agreement and reflection-sector reconstruction
- Simple full spectra on every nonzero holdout size
- Exact range-four local-charge nullity two on every nonzero holdout row
- An extensive exact local-charge family at the J=0 control
- A Lean-checked standard Jordan-Wigner axis-alignment obstruction
- A finite-size weak-to-strong symmetry-resolved crossover candidate
- Zero normalized-gap improvements over the R191 denominator

## Not Supported

- This is not an all-n spectrum theorem.
- This does not exclude every integrability mechanism.
- This is not a nonintegrability or quantum-chaos theorem.
- This is not a spectral-hardness theorem.
- This is not quantum-hardware evidence.
- This is not a Quantum PCP or NLTS theorem.
- This is not a BQP separation or solved frontier.

## Next Gate

Attack the holdout crossover with range-five/six and quasi-local
charge searches, site-dependent/nonlocal duality candidates, and
larger-size sparse shift-invert spectra. A nonintegrability or
quantum-chaos claim remains forbidden unless those independent
escape routes and finite-size drift are closed.
