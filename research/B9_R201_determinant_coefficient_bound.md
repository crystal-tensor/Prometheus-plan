# B9 R201 Integer Determinant Bound and CRT Budget

- Date: `2026-10-31`
- Track: `B9`
- Status: `unconditional determinant coefficient bound proved; CRT execution open`
- Integer coefficient bound proved: `true`
- Bounded CRT integer reconstruction complete: `false`
- Characteristic-zero `D^44` divisibility verified: `false`
- Characteristic-zero engineering certificate verified: `false`
- Frozen holdouts executed: `false`
- Scientific promotion: `false`
- New credit: `0`

## Question

How many finite-field determinant artifacts are sufficient to turn the public R201 engineering minors into unique integer polynomials without assuming that the observed two-prime factorization already holds in characteristic zero?

## Unconditional Bound

All `4 x 37 x 37 = 5,476` entries of the four frozen matrices are integer polynomials. Every nonzero entry in a fixed column is homogeneous of the same degree. The 37 column degrees sum to `184`, so every determinant is a homogeneous degree-184 polynomial over `ZZ[a,b,c]` with a complete reconstruction lattice of `17,205` monomials.

For the entry matrix `M`, define `A_ij = ||M_ij||_1`, the sum of absolute integer coefficients. Polynomial L1 norm is submultiplicative, so the Leibniz formula gives

```text
max_coefficient_abs(det(M)) <= ||det(M)||_1 <= permanent(A).
```

The verifier does not compute the permanent. It records four independent upper bounds on it:

```text
product(row sums)
product(column sums)
37! * product(row maxima)
37! * product(column maxima)
```

and safely selects the smallest value for each minor.

| Minor | Selected bound | Bits | Digits | Method |
| --- | ---: | ---: | ---: | --- |
| 0 | `17998835336780001801622225633941331080137544851485011097232279418427150711447823327609745881124640032957276717318144000000000000` | 423 | 128 | column-sum product |
| 1 | `75563759753441879752905345759069953792878733868880114156418419691122899643217317124271589689428519812876112632914347714150400000` | 425 | 128 | row-sum product |
| 2 | `135883488767919802081805959734473531942782774597943994379184884286550998572489318864226131387733260403643856940950312011694080000` | 426 | 129 | row-sum product |
| 3 | `6228380766783066580898728405091589640101992327508549450422852502373356624914619223718017690312932643151485851402240000000` | 402 | 121 | row-sum product |

The largest bound is the 426-bit minor-2 value. Unique symmetric reconstruction therefore requires a combined modulus strictly greater than its 427-bit doubled bound.

## Why the Degree-96 Shortcut Is Not Yet Valid

The previous two-prime step found `D^44`, with `D=a^2+b^2+c^2`, in every finite-field determinant. The new verifier checks whether this factor is already visible as a product of common column factors. It is not: all 37 common column `D` exponents are zero for every minor.

That negative result matters. Directly reconstructing the degree-96 modular quotients would assume the characteristic-zero `D^44` divisibility that the reconstruction is supposed to prove. The accepted order is now:

1. reconstruct each complete degree-184 integer determinant;
2. replay the reconstructed determinant against the public matrix;
3. verify exact division by `D^44` in `ZZ[a,b,c]`;
4. only then use or factor the degree-96 integer quotient.

## Exact Prime Budget

The existing primes produce modulus

```text
1,000,003 * 536,870,723 = 536,872,333,612,169
```

which has only 49 bits. Applying the deterministic rule "descending distinct primes below `2^29`" requires 14 additional primes:

```text
536870909, 536870879, 536870869, 536870849,
536870839, 536870837, 536870819, 536870813,
536870791, 536870779, 536870767, 536870743,
536870729, 536870717
```

After the first 13 planned primes, the modulus is still below `2B`. Adding the 14th yields a 455-bit modulus and closes the uniqueness inequality. The execution packet therefore requires `14 x 4 = 56` new determinant artifacts. Combined with the existing eight, the complete CRT set contains 64 minor-prime artifacts.

## Claim Boundary

This result proves an unconditional integer coefficient bound and an exact finite prime budget. It does not compute the 56 new determinants, reconstruct an integer determinant, prove characteristic-zero `D^44` divisibility, compute a characteristic-zero gcd, emit the ideal-membership certificate, open either frozen coupling, establish Quantum PCP or NLTS, separate BQP, claim hardware evidence, promote the science result, or add credit.

## Next Gate

1. Compute all 56 planned finite-field determinant artifacts.
2. Replay their row, matrix, term, and point-evaluation bindings.
3. Reconstruct all 17,205 homogeneous degree-184 coefficient slots for each minor by symmetric CRT.
4. Verify the reconstructed integer determinant identities independently.
5. Divide by `D^44` exactly over `ZZ[a,b,c]`, then continue to the ideal-membership certificate.
