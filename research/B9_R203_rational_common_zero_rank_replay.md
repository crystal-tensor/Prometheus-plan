# B9 R203 Rational Common-Zero and Full-Matrix Rank Replay

Date: 2026-10-31

## Research question

R202 showed that four selected primitive quotient minors do not generate the
unit ideal in two finite fields. Is that signal caused by a genuine rank drop
of the complete engineering matrix, or only by an insufficient choice of four
maximal minors?

R203 answers this question at two exact characteristic-zero points. It does
not infer a rank from the four minors. It rebuilds the complete matrix through
two separate implementations and emits a nonzero exact integer maximal minor
for each implementation and point.

## Exact rational witnesses

Restricting the four R201 primitive degree-96 quotients to `b=0` gives the
exact common gcd

```text
(a-2*c)^5*(2*a+c)^5
*(768*a^6-256*a^5*c-7227*a^4*c^2+5120*a^3*c^3
  +7227*a^2*c^4-256*a*c^5-768*c^6).
```

The two rational linear factors produce the normalized projective points

```text
[a:b:c] = [2:0:1]
[a:b:c] = [1:0:-2]
```

Both have `D=a^2+b^2+c^2=5`. At each point, all four primitive quotients
evaluate exactly to zero. Taking `u=1/5` also satisfies `1-uD=0`. The R202
nonunit signal therefore has explicit rational witnesses; it is not merely a
bad-prime possibility.

## Full-matrix replay

The rank check uses two separate matrix constructions:

- the `256x37` dense matrix uses the Kronecker/Hermitian-coordinate route;
- the independent `238x37` Pauli matrix uses the Pauli-word route.

For each point and route, all rows are deterministically ordered using a
third prime, `1,000,037`. The selected `37x37` submatrix is then evaluated over
the integers. A nonzero exact determinant proves rank 37 over `QQ`; modular
ranks and determinant residues at `1,000,003`, `536,870,723`, and `1,000,037`
provide additional replay pressure.

| Point | Route | Shape | Exact rank | Determinant bits | Determinant SHA-256 |
|---|---|---:|---:|---:|---|
| `[2:0:1]` | dense | `256x37` | 37 | 581 | `89a13edd7c4556d1a7202a654bb5905ae559577469251b5dad33e9027adbcf03` |
| `[2:0:1]` | source | `238x37` | 37 | 344 | `a48de512995f0c692affe81ec8ff474bd26a84d4755e1af5eba30e15ba7e1f32` |
| `[1:0:-2]` | dense | `256x37` | 37 | 589 | `a244359c46507ec1499119f6e4f01f5fa82a1c543d5714adaff023ec024d5af6` |
| `[1:0:-2]` | source | `238x37` | 37 | 340 | `6051622288746c81bdffb1e01c434fe7dec7ac1f0f71077c5bfec261e773488c` |

Every exact determinant and full selected-row list is stored in
`results/B9_R203_rational_common_zero_rank_replay_v0.json`. All four
determinants are nonzero under all three audit primes.

## Result

The two rational common zeros are **four-minor selection artifacts**. The four
R201 quotient minors vanish, but the complete engineering matrix remains full
column rank in both representations.

This is a concrete correction to the certificate strategy:

- R201's exact determinant reconstruction and gcd statements remain valid;
- R202's nonunit classification remains valid;
- the current four selected minors are not sufficient to characterize the
  full rank-drop locus;
- a unit-ideal certificate must include additional independently selected
  maximal minors or use a different full-rank certificate construction.

## Claim boundary

R203 does not prove that the complete matrix has full rank at every
projective point. It classifies two rational components exposed on the `b=0`
slice. The degree-six factor in the restricted gcd remains unresolved, as do
other components outside that slice.

No `J=127/128,131/128` holdout was evaluated. No Quantum PCP, NLTS,
integrability, hardness, BQP, scientific-promotion, or new-credit claim is
made.

## Next gate

Select additional maximal minors using an independent row rule that does not
reuse the four R201 row sets. Require at least one new minor to be nonzero at
each R203 witness, append those minors to the exact saturated ideal, and rerun
the unit-ideal classification. In parallel, classify the degree-six `b=0`
factor and verify the complete matrix at any resulting algebraic point.
