# B9 R204 Expanded-Minor Saturated-Ideal Preflight

Date: 2026-10-31

## Research question

R203 found two exact rational common zeros of four selected maximal minors, but
the complete `256x37` dense matrix and independently constructed `238x37`
Pauli matrix both retained rank 37. Can one additional maximal minor, selected
from the complete source matrix rather than the original four R201 row sets,
repair the certificate route?

R204 answers two narrower questions:

1. Does the new minor exclude both known rational artifacts?
2. Do the five quotient minors generate the unit ideal after saturation by
   `D=a^2+b^2+c^2` in the two preregistered finite fields?

## Added maximal minor

The new `37x37` row set is the source-matrix full-rank witness selected in
R203 at `[2:0:1]`. Its row-set hash is
`4b1858933538516ceb01954ac165db81b6bdd5a4cb4095a8ba32df3d6c1cc484`.
It is independent of the four R201 minor row sets and is rebuilt from the
Pauli-word source implementation.

Singular computes its homogeneous determinant separately over
`GF(1,000,003)` and `GF(536,870,723)`. In both fields:

- determinant total degree: `184`;
- determinant nonzero terms: `5,997`;
- exact common factor removed: `D^44`;
- quotient total degree: `96`;
- quotient nonzero terms: `1,113`;
- sparse factor recomposition: exact.

The factorization is not treated as exact until the nonzero scalar omitted by
monic finite-field factors is restored and every sparse coefficient equals the
original determinant. This check caught and corrected a scalar-normalization
failure during development.

## Known-artifact exclusion

The source maximal minor has the same nonzero exact integer determinant at the
two R203 points. Its SHA-256 is
`a48de512995f0c692affe81ec8ff474bd26a84d4755e1af5eba30e15ba7e1f32`.

| Prime | Point | Determinant mod p | Quotient mod p | Excluded |
|---:|---|---:|---:|---|
| `1,000,003` | `[2:0:1]` | `531467` | `537593` | yes |
| `1,000,003` | `[1:0:-2]` | `531467` | `537593` | yes |
| `536,870,723` | `[2:0:1]` | `285026561` | `141855713` | yes |
| `536,870,723` | `[1:0:-2]` | `285026561` | `141855713` | yes |

At each point `D=5`, and the determinant equals the quotient times `D^44`
modulo the declared prime. The fifth quotient therefore excludes both known
rational four-minor artifacts.

## Slice contraction

Before the fifth minor, the exact `b=0` gcd had degree 16:

```text
(a-2*c)^5*(2*a+c)^5
*(768*a^6-256*a^5*c-7227*a^4*c^2+5120*a^3*c^3
  +7227*a^2*c^4-256*a*c^5-768*c^6).
```

After appending the fifth quotient, both finite fields return the same
normalized degree-six, seven-term residual factor. The two fivefold linear
components are gone. The fifth minor removes ten degrees of known artifact
multiplicity but leaves the exact R203 degree-six component.

## Saturated-ideal classification

The expanded ideal is

```text
<q0,q1,q2,q3,q4,1-u*(a^2+b^2+c^2)>.
```

Each Singular `slimgb` run has a 600-second timeout and 8192-MiB RSS watchdog.
The unit and nonunit controls classify correctly in both fields.

| Prime | Old basis size | Five-minor basis size | `reduce(1,G)` | Unit ideal |
|---:|---:|---:|---|---|
| `1,000,003` | `43` | `10` | `1` | no |
| `536,870,723` | `43` | `10` | `1` | no |

The five-minor basis degree/term-count summary is identical across the two
fields, with SHA-256
`23beb23a5cf653ed00ea92de764528cf9f96fe5e1ef982035bb640d56394daa8`.

## Result

One independently selected minor materially improves the certificate system:
it excludes both known rational artifacts, removes their ten degrees of slice
multiplicity, and contracts the modular standard basis from 43 elements to 10.
It is still insufficient. The degree-six component survives, and both expanded
finite-field ideals remain nonunit.

This is a useful negative result. It replaces the vague instruction "add more
minors" with a concrete remaining algebraic component that can be attacked
directly.

## Claim boundary

R204 does not prove that the degree-six component contains a rational or real
full-matrix rank drop. It does not prove failure over `QQ`, and it is not a
characteristic-zero Nullstellensatz certificate. A selected-minor common zero
can still be a full-rank artifact.

No `J=127/128,131/128` holdout was evaluated. No Quantum PCP, NLTS,
integrability, hardness, BQP, hardware, scientific-promotion, or new-credit
claim is made.

## Next gate

Resolve the degree-six component directly. Isolate its real and algebraic
projective roots, evaluate the complete `238x37` and `256x37` matrices over the
corresponding exact algebraic extensions, and emit either a nonzero maximal
minor or an explicit nonzero kernel vector. If all roots remain full rank,
select another independent maximal minor that excludes this component and
repeat the saturated-ideal classification.
