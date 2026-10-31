# B9 R210 Characteristic-Zero Lift: Second CRT Shard

## Question

Can the R209 bounded reconstruction plan absorb a second complete prime shard
without support drift, arithmetic disagreement, or premature promotion of the
partial CRT representatives?

## Result

R210 completes the second planned three-minor shard at prime `536870879`.
Together with the two classification primes and the R209 shard at `536870909`,
the incremental reconstruction now uses four primes.

| Quantity | R210 result |
|---|---:|
| completed planned primes | `2/14` |
| completed new determinant artifacts | `6/42` |
| remaining new determinant artifacts | `36` |
| combined modulus | `154742904286161782771953694404859` |
| combined modulus bit length | `107` |
| worst uniqueness threshold | `428` bits |
| primary CRT round trips | `206460/206460` |
| independent CRT round trips | `206460/206460` |
| independent matrix replays | `24/24` |
| independent `D^44` recompositions | `24/24` |

The partial modulus remains too small to determine unique integer
coefficients. R210 therefore advances the finite execution ledger but does not
cross the characteristic-zero gate.

## Second Prime Shard

The three new `37x37` determinant artifacts reproduce the frozen support sizes
from R209:

| Minor | Determinant terms | Degree-96 quotient terms | Modular division |
|---:|---:|---:|---|
| 4 / R204 | 5,997 | 1,113 | exact `D^44` |
| 5 / R206 | 6,555 | 1,363 | exact `D^44` |
| 6 / R208 | 5,309 | 821 | exact `D^44` |

Each artifact replays the four frozen public points directly against its source
matrix and recomposes the determinant from the quotient and `D^44`.

## Independent Audit

The R210 audit does not trust a total replay count alone. For every completed
new-prime artifact it requires exactly the four frozen points, validates the
complete `(minor, prime)` artifact grid, checks file and sparse-payload hashes,
rebuilds the source matrix, and recomputes determinants with custom modular
Gaussian elimination.

For the coefficient lift it uses `sympy.ntheory.modular.crt`, rather than the
project-owned incremental CRT routine. All three 17,205-slot homogeneous
lattices agree with the primary replay on nonzero counts, maximum symmetric
residues, payload hashes, and all `206460` residue round trips.

## Claim Boundary

This is an exact second modular shard and an independently replayed partial CRT
state. It is not a bounded integer reconstruction, characteristic-zero
`D^44` certificate, rational Nullstellensatz identity, global-rank theorem,
Quantum PCP or NLTS result, quantum-hardware result, scientific promotion, or
new credit. The frozen `J=127/128,131/128` holdouts remain sealed.

## Next Gate

Compute minors 4, 5, and 6 at the third planned prime `536870869`, rerun both
CRT implementations over five total primes, and keep partial symmetric
representatives non-promotable until the combined modulus exceeds twice every
proved coefficient bound.
