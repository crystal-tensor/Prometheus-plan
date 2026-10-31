# B9 R208: Seventh Minor and Two-Prime Unit-Ideal Preflight

## Question

Can the cross-branch maximal minor found in R207 remove all four remaining
false rank drops and turn the selected-minor system into a unit-ideal route?

R208 answers this bounded modular question positively at both classification
primes. It does not yet provide the characteristic-zero certificate needed for
a global theorem.

## Exact seventh-minor bridge

R208 reuses the fixed 37-row Pauli certificate selected on the positive `b`
branch in R207. The row-list hash is
`9cd1569d47859421d2f7d6ed2caf6c2f896c9b77df3c0c2b9a1749cc0df1388b`.
The complete source matrix is rebuilt before the determinant is computed.

At `GF(1,000,003)` and `GF(536,870,723)` independently:

- the selected `37x37` determinant has total degree 184 and 5,309 terms;
- factorization and sparse recomposition verify exact division by
  `D^44=(a^2+b^2+c^2)^44`;
- the remaining homogeneous quotient has degree 96 and 821 terms;
- the quotient support hash is
  `3e0a3f7bffe3ecd274378f59553c0760680707a843d021a74cf0738f115d1ac2`;
- four direct integer-matrix replays agree with polynomial evaluation and
  `D^44` recomposition.

The two fields have the same monomial support. Their coefficients are retained
separately; two residues are not treated as an integer reconstruction.

## Seven-minor saturated ideal

The new quotient is appended to the four R201 quotients, the R204 fifth
quotient, and the R206 sixth quotient. Singular `slimgb` then classifies

```text
<q0,q1,q2,q3,q4,q5,q6,1-u*(a^2+b^2+c^2)>
```

at both declared primes. Each run returns a one-element basis `[1]` and
`reduce(1,G)=0`. The `b=0` normalized slice gcd remains 1. The full selected
seven-minor saturated ideal is therefore the unit ideal in both tested finite
fields.

The R207 chart is checked separately by adding the seventh quotient to

```text
169*a^2 + 407
169*b^2 - 576
c - 1
```

and is also the unit ideal at both primes. Thus the new minor removes all four
algebraic points classified by R207, including both signs of `a` and `b`.

## Independent radical-route audit

An independent audit uses Singular `std` only on the complete R207 radical
chart plus the seventh quotient. Before the quotient is added, both chart
quotients have vector-space dimension 4 and are nonunit. After it is added,
both have basis `[1]`, membership remainder 0, and vector-space dimension 0.

This is a different logical route from the full seven-generator `slimgb`
calculation: R207 establishes that the radical chart covers the six-minor
zero set, and the independent audit proves the seventh quotient has no zero on
that chart. A direct full seven-generator `std` run was also attempted, but it
did not finish within a useful interactive interval and was terminated. It is
not counted as evidence.

## What changed

R206 left a nonunit off-slice component. R207 showed that component consisted
of four false rank drops and selected one minor that was nonzero on all four.
R208 now turns that witness into a complete degree-96 generator and closes the
selected-minor ideal at two finite-field primes.

This changes the next task. Searching for an eighth minor is no longer the
priority. The next gate is a characteristic-zero certificate route:

1. reconstruct the R204, R206, and R208 quotients over `ZZ` with proved CRT
   bounds and exact `D^44` division;
2. construct an explicit `QQ` Nullstellensatz identity for the seven
   quotients and the saturation equation;
3. verify that identity with a separate sparse-polynomial implementation;
4. only then open the sealed `J=127/128,131/128` holdouts and decide whether
   the bounded engineering result generalizes.

## Claim boundary

- No quantum processor or hardware backend was used or needed for this
  algebraic certificate preflight.
- No frozen `J=127/128,131/128` holdout was evaluated.
- No characteristic-zero or rational Nullstellensatz certificate was
  produced.
- No global full-rank theorem over all couplings was proved.
- No Quantum PCP, NLTS, BQP, scientific-promotion, or new-credit claim is
  made.

The result is protected by exact source-row binding, two independent modular
determinants, exact `D^44` recomposition, two full saturated-ideal
classifications, and an independent `std` radical-elimination route. These
checks establish the bounded modular result; they do not turn a classical
symbolic computation into quantum-hardware evidence.
