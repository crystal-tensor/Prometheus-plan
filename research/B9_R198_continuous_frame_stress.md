# B9 R198 Continuous XZ-Frame Stress

- Status: `checked_continuous_xz_frame_boundary`
- Protocol hash: `7ab964fa0224fe960f0a7764427e6709fdf89202ef990d11a4acae61b7f32586`
- Payload hash: `eb8fc1597cdefc709137f8864f129585a38d0ff2ac5b1945c2c829df900b571d`
- Public preregistration commit: `21e68f5198b19b347b4aa0f01f18e782ee8638c3`
- Continuous symbolic rows: `4/4`
- Exact maximal-minor determinants: `20`
- Finite real common roots after adaptive factor pressure: `0`
- Rational-frame rows: `432/432`
- Largest candidate pool / commutator nonzeros: `211` / `122753`
- Requirements: `12/12`
- Independent audit: `pass`
- Independent continuous certificate matches: `4/4`
- Independent third-prime full-rank grid rows: `432/432`
- Independent audit errors: `0`
- Scientific promotion: `false`
- New credit delta: `0`

## Research Question

Can a continuously rotated XZ-plane Jordan-Wigner parity frame reveal an extra exact quadratic-Majorana conserved operator missed by the five R197 frames?

## Method

For `n=4,5`, every scaled commutator entry is an exact integer polynomial in the Pythagorean parameter `t`. Initial maximal minors are selected at frozen anchors `0,1,2,4`. Any real-root factor shared by those minors is attacked by a new row basis selected over the exact quotient field. Zero real roots in the final common divisor, plus a full-rank projective-infinity endpoint, certifies the whole declared real projective line.

For `n=6,8,10`, the protocol separately checks 72 exact Pythagorean frames at both holdout couplings under two prime fields.

## Continuous Rows

| J | n | columns | determinants | final gcd degree | real roots | infinity full rank |
|---:|---:|---:|---:|---:|---:|:---:|
| 89/128 | 4 | 37 | 5 | 88 | 0 | true |
| 89/128 | 5 | 56 | 5 | 130 | 0 | true |
| 101/128 | 4 | 37 | 5 | 88 | 0 | true |
| 101/128 | 5 | 56 | 5 | 130 | 0 | true |

## Claim Boundary

R198 closes only the declared XZ-plane continuous quadratic-Majorana-plus-parity family at `n=4,5` and the frozen 72-frame grid at `n=6,8,10`. It does not exclude general Bloch-sphere frames, nonlinear frame mixtures, cubic or quartic Majorana charges, nonlocal dualities, interacting integrability, larger-size drift, nonintegrability, quantum chaos, spectral hardness, Quantum PCP, NLTS, BQP separation, hardware relevance, or a solved frontier.

## Independent Audit

A separate sparse symplectic-bit implementation imports none of the R193-R198
construction modules. It independently reconstructs the polynomial Pauli
matrices, all 20 selected maximal minors, their primitive gcds and exact
real-root counts, all four projective endpoints, and all 432 rational-frame
operator and commutator matrices. Every continuous certificate matches. All
432 frozen grid rows remain full column rank under independent prime
`1,000,037`; the solvable control retains nullity `37` and all six explicit
onsite witnesses. Audit errors: `0`.

## Next Gate

Attack a second Bloch-sphere chart, quartic Majorana charges, or one explicit
nonlocal duality under a new public freeze. The present result must not be
promoted beyond its declared XZ-plane quadratic family.
