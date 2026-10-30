# B9 R199 A-Y Meridian Preregistration

- Status: `publicly_preregistered_execution_pending`
- Contract SHA256: `a9679357747deb983de1285946ac97c1679c018b383a8e5e0d9c2c9cc6bcb1cb`
- Main tool SHA256: `ba7dda8f92a6deb24fb1be33f2961c0a70b6de9134adc4bd6e56597c81728231`
- R198 dependency SHA256: `c2644527c64d863005b61733a719a1f122dd65b922a4b34ae545e7d61bb0fc13`
- Requirements SHA256: `4f6fee8aef0c9d39f196c6d3b1e03d354da68a99fa831c01e57c6dfd998efa49`
- Engineering probe SHA256: `7881ccdb390e70e6e528197f67540ff314bed492aa90c14d314f0b174560d6e6`
- Frozen holdouts executed: `false`
- Scientific promotion: `false`
- New credit delta: `0`

## Research Question

Can a continuously rotated Jordan-Wigner parity axis that leaves the XZ plane
reveal an exact quadratic-Majorana conserved operator missed by R198?

## Frozen Chart

Let

```text
A = (-4X+3Z)/5
B = (-3X-4Z)/5
P = cA+sY
Q = -sA+cY
R = B
c = (1-t^2)/(1+t^2)
s = 2t/(1+t^2)
```

The triad is exactly right-handed and orthonormal: `Q x R=P`, `R x P=Q`,
and `P x Q=R`. Ten symbolic polynomial identities prove the three norms,
three pairwise orthogonalities, three cyclic orientations, and the positive
determinant `125(1+t^2)^3`. For finite `t != 0`, the parity axis `P` has a
nonzero `Y` component and is outside the R198 XZ chart. At `t=0`, `P=A`,
preserving an exact `J=0` positive control.

## Frozen Acceptance Surface

- unseen couplings: `97/128`, `107/128`;
- exact continuum certificates: `n=4,5` at both couplings;
- initial maximal-minor anchors: `0,1,2,4`;
- maximum adaptive quotient-field rounds: `12`;
- larger-size pressure: 72 directed rational frames representing 36
  projective candidate subspaces at `n=6,8,10`;
- frozen directed grid rows / projective rows: `432` / `216`;
- declared primes: `1,000,003`, `1,000,033`;
- independent audit prime: `1,000,037`;
- positive control: `J=0,n=6,t=0`, 79 independent candidates,
  commutator rank 42, nullity 37, and six commuting onsite A-axis charges.

The engineering probe uses only observed `J=13/32`. It contributes zero
frozen decisions and passes the exact frame checks, one `n=4` continuum
certificate, and four `n=6` rational-frame smoke rows. Runtime fields are
excluded from this preregistration artifact; two executions are byte-identical.

## Claim Boundary

Even a complete pass can close only this one A-Y great-circle meridian at the
declared finite sizes and operator family. It cannot establish a full
two-dimensional Bloch-sphere exclusion, nonlinear frame-mixture exclusion,
higher-order Majorana-charge exclusion, nonlocal-duality exclusion,
interacting nonintegrability, chaos, hardness, Quantum PCP, NLTS, BQP,
hardware relevance, or a solved frontier.

## Next Gate

Publish the preregistration commit before opening either holdout. Then execute
the frozen run, build the non-importing symplectic-bit and polynomial audit,
and admit no positive scientific credit unless every declared gate survives.
