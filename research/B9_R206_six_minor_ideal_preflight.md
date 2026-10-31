# B9 R206: Six-Minor Saturated-Ideal Preflight

## Heuristic question

Can one exact maximal minor close every known point on a slice while a global
rank-drop candidate still survives outside that slice?

## What R206 computes

R205 identified a fixed 37-row Pauli minor that remains nonzero at all six
roots of the R204 residual sextic. R206 promotes that row set into a full
projective determinant rather than using only its algebraic-root residues.
At both `GF(1,000,003)` and `GF(536,870,723)`, the determinant has total degree
184 and 6,555 terms. Exact sparse division removes `D^44` and leaves a
degree-96 quotient with 1,363 terms. The quotient support is identical across
the two fields.

The bridge also recomputes the previous five-minor `b=0` gcd directly. It is
the same degree-six R204 residual at both primes. The new quotient has gcd 1
with that sextic. The sixth minor alone still vanishes at the two earlier R203
rational points, but the fifth and sixth minors exclude the rational and
sextic components together. Nonzero integer controls at `(1,1,1)` and
`(3,2,1)` independently verify determinant evaluation, quotient evaluation,
and `D^44` recomposition.

## Saturated-ideal result

R206 appends the sixth quotient to the five R204 generators and saturates by
`1-u(a^2+b^2+c^2)` in degree-reverse-lexicographic order.

| Check | `1,000,003` | `536,870,723` |
| --- | ---: | ---: |
| Six-minor `b=0` gcd degree | 0 | 0 |
| Normalized slice gcd | 1 | 1 |
| Standard-basis size (`slimgb`) | 7 | 7 |
| `reduce(1,G)` | 1 | 1 |
| Unit ideal detected | no | no |

The old slice degree falls from 6 to 0, so every component currently known on
`b=0` is excluded. The full saturated ideal nevertheless remains nonunit at
both primes. The standard basis contracts from 10 elements in R204 to 7 in
R206, but it does not contain 1.

## Independent algorithm audit

The complete two-prime calculation was repeated with Singular `std` after the
primary `slimgb` run. Both algorithms agree on the source bindings, primes,
slice gcd, basis size, unit-membership remainder, unit/nonunit counts, and
scientific classification. They emit different noncanonical standard-basis
summaries, which is expected and is recorded rather than hidden. The
algorithm-independent conclusion is unchanged: the known slice is closed,
and at least one modular component remains outside `b=0`.

## Claim boundary

This is a two-prime modular preflight, not a rational Nullstellensatz
certificate. It does not prove a characteristic-zero common zero, global rank
loss, global full rank, Quantum PCP, NLTS, or BQP separation. No
`J=127/128,131/128` frozen holdout was evaluated. Scientific promotion and new
credit remain zero.

## Next gate

Do not add a seventh minor blindly. Extract or parameterize the component
represented by the seven-element off-slice standard basis, then replay the
complete `238x37` and `256x37` matrices on exact witnesses. A full-rank witness
must select another excluding minor; a true rank drop must emit an exact
nonzero kernel vector. Only after that classification should the ideal be
expanded again.
