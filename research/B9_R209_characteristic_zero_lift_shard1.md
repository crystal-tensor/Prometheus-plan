# B9 R209 Characteristic-Zero Lift: Bound and First CRT Shard

## Question

Can the two-prime seven-minor unit-ideal signal from R208 be lifted toward a
characteristic-zero certificate without treating modular residues as integer
coefficients?

## Result

R209 fixes an unconditional reconstruction budget for the three additional
degree-184 determinants introduced in R204, R206, and R208, then completes the
first planned three-minor prime shard.

The determinant coefficient bounds are:

The three selected bounds are 417, 418, and 427 bits, respectively.

| Minor | Source | Selected bound | Twice-bound threshold |
| --- | --- | ---: | ---: |
| 4 | R204 | 417 bits | 418 bits |
| 5 | R206 | 418 bits | 419 bits |
| 6 | R208 | 427 bits | 428 bits |

The proof uses the polynomial L1 norm, the Leibniz determinant expansion, and
four independent permanent upper bounds derived from the exact `37x37`
entry-L1 matrices. Every source entry is an integer polynomial, every nonzero
entry is column-homogeneous, and all three column-degree sums are 184. The
common column-level `D` exponent is zero in every column set, so direct CRT of
the degree-96 modular quotients would be circular. The degree-184 determinants
must be reconstructed first.

Starting from the two R208 classification primes, the deterministic plan needs
14 additional primes below `2^29`, or 42 new determinant artifacts. The final
planned modulus has 455 bits; the modulus before the final prime is below the
proved uniqueness threshold.

## First Prime Shard

The first added prime is `536870909`. All three planned determinant artifacts
are complete:

| Minor | Determinant terms | Quotient terms | Modular `D^44` |
| --- | ---: | ---: | --- |
| 4 | 5,997 | 1,113 | exact |
| 5 | 6,555 | 1,363 | exact |
| 6 | 5,309 | 821 | exact |

Each determinant has total degree 184. Removing `D^44` leaves a degree-96
quotient. Four direct integer-matrix point replays per minor match the stored
modular determinant, and all 12 quotient recompositions match.

Combining the two classification primes with the first added prime produces a
78-bit partial modulus. The replay covers 17,205 homogeneous coefficient slots
per determinant and passes `154845/154845` coefficient-slot-prime round trips.
All three determinant supports are identical across the three primes.

The partial symmetric representatives are not integer coefficients: 78 bits is
far below the 428-bit worst-case uniqueness threshold. The execution ledger is
therefore `3/42` new artifacts complete, with 39 artifacts remaining.

## Independent Audit

The independent audit imports neither the primary CRT combiner nor its finite
field determinant routine:

- a custom modular Gaussian-elimination determinant reproduces `12/12` matrix
  point values;
- all `12/12` modular `D^44` recompositions pass;
- `sympy.ntheory.modular.crt` independently reproduces all `154845` round trips,
  nonzero counts, maximum symmetric residues, and payload hashes.

## Claim Boundary

This is a proved coefficient budget plus one incremental modular shard. It is
not a bounded integer reconstruction, characteristic-zero `D^44` certificate,
`QQ` Nullstellensatz identity, global-rank theorem, Quantum PCP or NLTS result,
hardware result, scientific promotion, or new credit. The frozen
`J=127/128,131/128` holdouts remain sealed.

## Next Gate

Compute the second planned three-minor shard at prime `536870879`, rerun both
CRT implementations over four total primes, and keep every partial symmetric
representative non-promotable until the combined modulus exceeds twice every
proved coefficient bound.
