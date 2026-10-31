# B9 R202 Modular Saturated-Ideal Preflight

Date: 2026-10-31

## Research question

After R201 proved that four exact degree-184 minors share only the expected
`D^44` factor over `QQ[a,b,c]`, do the four primitive degree-96 quotients
generate the unit ideal on the projective patch
`a^2 + b^2 + c^2 != 0`?

This is a stricter question than polynomial gcd. Several multivariate
polynomials can have gcd one and still vanish simultaneously. The desired
certificate is an identity of the form

```text
A0*p0 + A1*p1 + A2*p2 + A3*p3 + B*(1-u*(a^2+b^2+c^2)) = 1
```

over `QQ[u,a,b,c]`.

## Inputs and normalization

- Source: `results/B9_R201_integer_reconstruction_v0.json`.
- The four exact quotient payloads are divided by their signed integer
  contents before reduction modulo a prime. This removes coefficient-domain
  units without changing the zero set over `QQ`.
- Primitive quotient term counts are `2401`, `464`, `590`, and `450`.
- The saturation generator is `1-u*(a^2+b^2+c^2)`.
- Singular uses `dp(u,a,b,c)` and `slimgb`.
- Every prime run includes a unit control `<a,b,c,1-uD>` and a nonunit
  control `<a,b,1-uD>` before the engineering ideal is classified.

## Result

Both finite-field runs completed within the declared 600-second and 8192-MiB
per-prime limits.

| Prime | Controls | Engineering basis size | `reduce(1,G)` | Unit ideal |
|---:|---|---:|---:|---|
| 1,000,003 | pass | 43 | 1 | no |
| 536,870,723 | pass | 43 | 1 | no |

The two engineering bases have the same degree/term-count summary hash,
`b2788d887a92f14a9620d6055bf4a3a3e8966810f047675a2d5881f91bbb236a`.
The first run took about 42.5 seconds and peaked near 602 MiB RSS; the second
took about 42.5 seconds and peaked near 600 MiB RSS. Runtime and RSS are
recorded as operational metadata, while a separate stable classification hash
binds only the source, normalized generators, toolchain, primes, controls, and
classification outputs.

## Interpretation

The current four-minor unit-certificate route is not supported. The exact
gcd-one statement from R201 remains true, but it was never sufficient to
exclude a common projective zero. Two independently sized finite fields now
produce the same nonunit classification under passing controls.

This is useful negative progress. It prevents an invalid transition from
"gcd one" to "no common zero" and redirects the work before the unseen
scientific couplings are opened.

## Claim boundary

The modular result does **not** prove any of the following:

- a rational or real common projective zero;
- a common zero over `QQ` or its algebraic closure;
- a rank drop in the full `238x37` source matrix;
- failure of every possible maximal-minor certificate;
- a Quantum PCP, NLTS, integrability, hardness, or BQP result.

One or both primes could still be exceptional for the characteristic-zero
ideal. No rational Nullstellensatz multiplier has been emitted. The frozen
`J=127/128,131/128` holdouts remain unopened, scientific promotion remains
false, and new credit remains zero.

## Next gates

1. Extract a modular associated component or maximal ideal from the 43-element
   standard basis for each prime.
2. Produce a common-zero witness over the prime field or a declared extension
   field, then independently evaluate all four primitive quotients.
3. Evaluate the complete engineering matrix at that witness and determine
   whether the four-minor zero is a genuine full-matrix rank drop or merely an
   insufficient-minor artifact.
4. Compare components across primes and attempt rational or algebraic
   reconstruction only if their structure agrees.
5. If the full matrix stays rank 37, select additional independent maximal
   minors and rerun the saturated-ideal test. If a real/projective rank-drop
   candidate appears, verify it exactly before any holdout decision.
6. Before any future holdout execution, create a new preregistration commit
   that binds the certificate tools, primitive quotient hashes, pre-source
   audit result, and mutation suite. The older boolean-only holdout executor
   is not sufficient for this transition.
