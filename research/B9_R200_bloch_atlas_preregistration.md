# B9 R200 Finite Projective Rational Bloch Atlas Preregistration

- Status: `publicly_preregistered_execution_pending`
- Contract SHA256: `a1208296eeaf56ed7bf51ed740b51931b7e1067cdb53d2e5e6e0d931aca356c0`
- Atlas catalog SHA256: `b168b38442f85cd7a485e6e1ea2332fab1fa994e7c13956c405384e31f59cd47`
- Projective catalog SHA256: `f64e2e63f922d691bdeef5fdf58b2e90207afe3b775d55dafc713e19b7705a2f`
- Main tool SHA256: `5639bc43f838e310cfef204e575ca4a33eac326c58169f0d431f74c51b522824`
- Independent audit tool SHA256: `7c66b8e362ff25d2d5e80dec87ee0ba1ec18b7b5d6de6d95157e50b99943c941`
- Independent pre-source seal SHA256: `ee15f20b977b790c065b281f9dfab85a1ed21194ceb2442fea576d00c4ebf1ad`
- R199 dependency SHA256: `ba7dda8f92a6deb24fb1be33f2961c0a70b6de9134adc4bd6e56597c81728231`
- R198 dependency SHA256: `c2644527c64d863005b61733a719a1f122dd65b922a4b34ae545e7d61bb0fc13`
- Requirements SHA256: `b48cbe8e5ef1382bb266ff9d39b6d225d7a0effd82cbdc873729195daae52d88`
- Engineering probe SHA256: `ff131a74ea5dad85e6aad5b491a1cfa0d1d71790042804246c22dff852aad9a5`
- Frozen holdouts executed: `false`
- Frozen acceptance decisions: `0`
- Scientific promotion: `false`
- New credit delta: `0`

## Research Question

Can a finite rational projective atlas expose an exact quadratic-Majorana
conserved operator that both the R198 XZ continuum and the R199 A-Y meridian
missed?

## Why Two Charts

A globally nonsingular continuous tangent frame on the Bloch sphere does not
exist. R200 therefore does not claim a continuous full-sphere theorem. It
freezes 31 unique projective parity axes. The 82 directed north/south frames
remain gauge-equivalence sentinels and are not double-counted as independent
scientific evidence.

For primitive integer triples `(a,b,c)`, with `c in {1,2}` and
`a,b in [-2,2]`, define `d=a^2+b^2+c^2` and the north chart

```text
P = (2ac, 2bc, c^2-a^2-b^2) / d
Q = (c^2-a^2+b^2, -2ab, -2ac) / d
R = (-2ab, c^2+a^2-b^2, -2bc) / d
```

The south chart uses `P=-P_north`, `Q=Q_north`, and `R=-R_north`.
Every row must satisfy exact unit norms, pairwise orthogonality, and
`Q x R=P`.

## Frozen Acceptance Surface

- unseen couplings: `109/128`, `113/128`;
- exact atlas rows: `82` (`41` north and `41` south);
- directed parity axes: `62`;
- projective parity axes: `31`;
- directed north/south overlap axes: `20`;
- finite sizes: `n=6,8,10`;
- frozen grid rows: `186`;
- candidate columns: `79`, `137`, and `211`;
- declared primes: `1,000,003`, `1,000,033`;
- independent audit primes: `1,000,037`, `1,000,081`;
- positive control: `J=0,n=6`, north row `(-1,0,2)`, which must recover
  operator rank `79`, commutator rank `42`, nullity `37`, and all six onsite
  `A=(-4X+3Z)/5` charges.

The independent audit is frozen in the same preregistration commit as the main
executor. It may not import or dynamically load R193-R200. It first seals the
31-axis catalog and all 186 expected grid keys without a source result, then
rebuilds every row under two fresh primes and reports missing, extra, and
duplicate rows separately. The source payload must hash correctly after a
plain JSON write/read round trip.

## Engineering Probe

The pre-publication probe uses only the already observed coupling `13/32`.
It contributes zero frozen decisions. It passes `82/82` exact frame checks,
`20/20` directed overlap subspace checks, `31/31` projective subspace checks,
and `4/4` `n=6` grid smoke rows. The zero-coupling control recovers all six
expected onsite charges. The frozen holdouts remain unopened.

## Claim Boundary

Even a complete pass can close only the declared finite rational projective
catalog, finite
sizes, and quadratic-Majorana-plus-parity family. It cannot establish a
continuous two-dimensional Bloch-sphere exclusion, an all-frame exclusion,
an irrational-axis exclusion, nonlinear or higher-order charge exclusion,
nonlocal-duality exclusion, interacting nonintegrability, chaos, hardness,
Quantum PCP, NLTS, BQP separation, hardware relevance, or a solved frontier.

## Next Gate

Publish this preregistration commit before opening either holdout. Then execute
the frozen `186`-row run, execute the already-frozen non-importing dual-prime
audit, and admit
no scientific promotion or new credit unless every declared gate survives.
