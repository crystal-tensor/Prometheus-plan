# B9 R205 Sextic Full-Matrix Rank Classification

Date: 2026-10-31

## Research question

R204 added a fifth independent maximal minor. It removed the two rational
fivefold components found by R203, but the five quotient minors still shared
the homogeneous `b=0` sextic

```text
768*a^6-256*a^5*c-7227*a^4*c^2+5120*a^3*c^3
+7227*a^2*c^4-256*a*c^5-768*c^6.
```

Does that sextic describe a genuine rank drop of the complete engineering
matrix, or another component created only by an insufficient selection of
maximal minors?

## Exact algebraic component

On the affine chart `c=1`, write `t=a/c`. The sextic becomes

```text
f(t) = 768*t^6-256*t^5-7227*t^4+5120*t^3
       +7227*t^2-256*t-768.
```

Exact factorization over `QQ` proves that `f` is irreducible. Its discriminant
is nonzero, and an exact Sturm isolation returns six simple real roots. Their
numerical locations are approximately

```text
-3.0905582268, -0.6002233368, -0.4092129847,
 0.3235661413,  1.6660465174,  2.4437152229.
```

The coefficient of `a^6` is nonzero, so no point on this component has `c=0`.
Every real projective point can therefore be written `[t:0:1]`, where
`D=t^2+1>0`.

## Good-reduction rank certificate

R205 does not estimate six floating-point ranks. It treats the full matrix as
a matrix over the exact number field `QQ[t]/(f)`.

Two primes are selected for which the sextic remains irreducible:

```text
p1 = 1,000,117
p2 = 1,000,121
```

The project-owned extension-field path works in `GF(p)[t]/(f)`. It selects one
37-row set per representation at `p1`, then reuses exactly the same row set at
`p2`. A nonzero determinant after good reduction proves that the corresponding
characteristic-zero determinant is not divisible by `f`. Because `f` is
irreducible over `QQ`, that determinant cannot vanish at any of the six
conjugate roots.

| Representation | Full shape | Specialized nonzero entries | Selected-row SHA-256 |
|---|---:|---:|---|
| Pauli-word source matrix | `238x37` | `629` | `9c7ac1a00aa08913b0895cf6be433d2146c3cd99f5292f920d8030f74661b0f6` |
| Dense Kronecker/Hermitian matrix | `256x37` | `1,977` | `d3dde08315a45b7be4c113ec0d5affbe5697018f6b4dd3bd1d0d90aac88057cc` |

Both selected minors are nonzero in both extension fields. Their determinant
residue hashes are:

| Representation | Prime | Residue SHA-256 |
|---|---:|---|
| Pauli | `1,000,117` | `c62bb42dfd1978e96efda0b2fdf8ebc0508c69967901fa5fae4822c48f40fb34` |
| Pauli | `1,000,121` | `1600c9198e052c20333c31ca16c8755b3d0e59ac9a152f1db4f2aaeabe6a1e93` |
| Dense | `1,000,117` | `90a23398a175ccd0e44c52737d8c766d878f4de8e156a7bc3bd058ed7399af4e` |
| Dense | `1,000,121` | `51a26bbbc7bb29936324b22461de5952d34e5ef980e2c7e5c9e78f19610a6ccc` |

## Independent arithmetic replay

The main certificate uses a project-owned six-coefficient finite-extension
implementation. A separate audit imports none of that field implementation.
It rebuilds the selected matrices and uses SymPy `Poly.rem`, `Poly.invert`, and
an independent Gaussian elimination path.

The audit reproduces all `4/4` six-coefficient determinant residues exactly:
two matrix representations times two primes. It also independently confirms
that both modular sextics are irreducible.

## Result

All six real points of the R204 sextic component have full column rank 37 in
both complete matrix representations. The component is therefore another
selected-minor artifact, not a full-matrix rank-drop component.

This closes every component exposed so far on the exact `b=0` slice:

- R203 classified the two rational linear components as full-rank artifacts;
- R205 classifies the remaining irreducible sextic as a full-rank artifact.

## Claim boundary

R205 does not prove global full rank on the complete projective parameter
space. It does not show that the current five-minor saturated ideal is the unit
ideal, and it is not a characteristic-zero Nullstellensatz certificate.
Components outside the `b=0` slice may remain.

No `J=127/128,131/128` holdout was evaluated. No Quantum PCP, NLTS,
integrability, hardness, BQP, hardware, scientific-promotion, or new-credit
claim is made.

## Next gate

Use the R205 Pauli selected-row set as a sixth maximal minor. Compute its full
degree-184 polynomial over both R204 fields, remove `D^44` exactly, append the
new degree-96 quotient, and rerun the saturated-ideal classification. If the
six-minor ideal remains nonunit, extract its next component before opening any
frozen scientific holdout.
