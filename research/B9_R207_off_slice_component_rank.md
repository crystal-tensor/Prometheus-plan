# B9 R207: Off-Slice Component and Complete-Matrix Rank

## Question

Can four algebraic common zeros of six selected maximal minors still be false
rank drops of the complete matrix?

R206 closed the entire `b=0` slice but left a seven-element nonunit standard
basis. R207 extracts that off-slice component before adding another minor.

## Component classification

At both `GF(1,000,003)` and `GF(536,870,723)`, Singular reduces all six
degree-96 quotient generators and the saturation equation to zero modulo

```text
169*a^2 + 407*c^2
169*b^2 - 576*c^2
2*u*c^2 - 1
```

The squares of all three displayed generators reduce to zero modulo the
original six-minor ideal. The `c=0` extension is the unit ideal, so the
component is covered by the chart `c=1`. In that chart the original quotient
has vector-space dimension 8 and the candidate radical has dimension 4.
Thus the modular component consists of four algebraic points, each with
multiplicity two:

```text
u = 1/2
a = +/- sqrt(-407)/13
b = +/- 24/13
c = 1
```

The same containment, square-membership, chart-length, and `c=0` checks pass
at both primes. This is a two-good-characteristic radical classification, not
a characteristic-zero primary decomposition.

## Complete-matrix replay

R207 rebuilds two complete representations from separate source paths:

- the `238x37` sparse Pauli-word matrix;
- the `256x37` dense Kronecker/Hermitian-coordinate matrix.

For each sign of `b`, entries are evaluated in
`QQ[s]/(s^2+407)` with `a=s/13`. A deterministic 37-row set is selected at
`GF(1,000,117)[s]/(s^2+407)` and replayed without reselection at
`GF(1,000,039)[s]/(s^2+407)`. The quadratic is irreducible at both audit
primes. All eight main determinant replays are nonzero, so both conjugate
values of `a` are covered for each sign of `b` in both complete matrices.

The selected rows from either `b` branch are also replayed on the opposite
branch. All eight cross-branch determinant replays are nonzero. Consequently,
one existing selected maximal minor can exclude all four algebraic points;
R208 does not need two branch-specific minors.

## Independent arithmetic audit

The independent audit imports none of R207's quadratic-field implementation.
It expands every committed `37x37` matrix over `x+y*s` into a `74x74` regular
representation over `GF(p)` and checks

```text
det(regular(M)) = Norm(det(M)) = x^2 + 407*y^2.
```

All four main minors and all four cross-branch minors match at both primes:
16/16 independent determinants are nonzero.

## What changed

The R206 nonunit signal is now classified as another selected-minor artifact,
not a rank drop of either complete matrix at the surviving modular points.
The next gate is concrete: promote one cross-branch Pauli minor to a seventh
degree-96 projective quotient, then rerun the saturated ideal at both
classification primes.

## Claim boundary

- No quantum processor or hardware backend was used.
- No frozen `J=127/128,131/128` holdout was evaluated.
- No characteristic-zero Nullstellensatz certificate was produced.
- No global full-rank theorem was proved.
- No Quantum PCP, NLTS, BQP, scientific-promotion, or new-credit claim is made.

The code is guarded by exact symbolic membership, two complete matrix
representations, two classification primes, two irreducible rank primes,
fixed-row replay, and a separate regular-representation determinant audit.
Those checks establish this bounded algebraic result; they do not replace
future hardware evidence where a claim actually depends on hardware.

