# When do four zero maximal minors fail to mean rank loss?

R202 found that four exact primitive quotient minors do not generate the unit
ideal over two finite fields. That left two very different explanations:

1. the complete engineering matrix really loses rank somewhere; or
2. the four chosen minors vanish together even though another maximal minor
   remains nonzero.

R203 now separates those possibilities at two exact rational projective
points.

On the `b=0` slice, the common gcd of the four primitive quotients contains

```text
(a-2*c)^5*(2*a+c)^5.
```

This gives `[2:0:1]` and `[1:0:-2]`. At both points, all four quotient values
are exactly zero and `D=5`, so `u=1/5` satisfies the saturation equation.
These are characteristic-zero common zeros, not numerical approximations and
not finite-field-only artifacts.

But the complete matrix refuses to lose rank.

- The dense Kronecker/Hermitian route rebuilds a `256x37` matrix and proves
  rank 37 at both points with nonzero exact integer `37x37` determinants.
- A separate Pauli-word route rebuilds a `238x37` matrix and independently
  proves rank 37 at both points.
- Every determinant remains nonzero modulo `1,000,003`, `536,870,723`, and a
  third row-selection prime, `1,000,037`.

So the R202 signal was real, but its interpretation changes: it exposes an
insufficient-minor certificate, not a full-matrix rank-drop witness.

The next contribution has a sharp target. How should we choose the smallest
additional set of maximal minors that kills these rational artifacts without
making exact ideal membership computationally intractable? A useful PR could
propose an independent row-selection rule, prove that at least one new minor
is nonzero at both witnesses, and rerun the saturated ideal with the expanded
generator set.

Claim boundary: the two rational artifacts are classified exactly, but the
degree-six factor on the `b=0` slice and all other projective components remain
open. No frozen holdout was executed, and no Quantum PCP/NLTS, BQP,
integrability, scientific-promotion, or new-credit claim is made.
