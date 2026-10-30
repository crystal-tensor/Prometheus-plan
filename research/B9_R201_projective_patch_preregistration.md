# B9 R201 Continuous Projective Bloch-Patch Preregistration

- Status: `public_preregistration_ready_execution_blocked`
- Contract SHA256: `b3c960f5081a776ccd7165c0146c39e81bf6170820ac593c0f37c8b928b6cb99`
- Main tool SHA256: `5b3d9c9aebdb7fa6aa93f28f336e5b95a7ba41ccf8cd926dea28dc04d569216c`
- Independent audit tool SHA256: `be394fec66bb10231550721745e13bb3a6c3a4f2d97ff955a3ac7e965e18a944`
- Engineering probe SHA256: `cb33131308ea61bd12c40d1d7b02f65b08e9a198b0e3ef5c773e30f2f7a2b228`
- Independent design seal SHA256: `732b30fde0931e04d74c1acad4dd8c3fb9cf900a1245546ba9de70434443393c`
- R198 dependency SHA256: `c2644527c64d863005b61733a719a1f122dd65b922a4b34ae545e7d61bb0fc13`
- Requirements SHA256: `b48cbe8e5ef1382bb266ff9d39b6d225d7a0effd82cbdc873729195daae52d88`
- Protocol SHA256: `994905bd727da0eb6ae34aa6c56e4f5477d3f9ea9e8720eea5b23ae8e4188c7d`
- Frozen holdouts executed: `false`
- Frozen acceptance decisions: `0`
- Scientific promotion: `false`
- New credit delta: `0`

## Research Question

Can the complete quadratic-Majorana-plus-parity candidate family retain full
commutator column rank over a continuous two-parameter real projective Bloch
patch, rather than only along one-dimensional meridians or at finitely many
rational axes?

## Exact Patch

Over `Q[a,b,c]`, define

```text
D = a^2+b^2+c^2
P = (2ac, 2bc, c^2-a^2-b^2)
Q = (c^2-a^2+b^2, -2ab, -2ac)
R = (-2ab, c^2+a^2-b^2, -2bc)
```

The implementation verifies ten vector identities, including equal norm
`D^2`, pairwise orthogonality, right-handed cross products, and determinant
`D^3`. Each candidate column is multiplied by its own nonnegative power of
`D` when denominators are cleared. This does not change rank on the declared
real projective domain, where `D>0`.

## Engineering Probe

The public engineering coupling remains the already observed `J=13/32`. At
`n=4`, the exact polynomial commutator matrix has:

- `238` output rows and `37` candidate columns;
- `2,129` nonzero polynomial matrix entries;
- column degrees `2^6, 4^14, 6^10, 8^7`;
- maximal-minor total-degree bound `184`;
- full column rank at all eight engineering anchors, including the `c=0`
  boundary points `[1:0:0]` and `[0:1:0]`.

The `J=0,n=6` positive control at `[-1:0:2]` recovers operator rank `79`,
commutator rank `42`, nullity `37`, and all six onsite field-axis charges.
These checks show that the detector and the projective boundary are wired
correctly. They are not a continuous proof and contribute zero acceptance.

## Frozen Scientific Surface

- unseen couplings: `127/128`, `131/128`;
- first mandatory size: `n=4`;
- conditional size: `n=5`, only after both `n=4` rows are exactly resolved;
- at most 12 publicly selected maximal minors;
- exact saturation on `D != 0`;
- exact full-matrix recheck for every candidate real rank-drop point;
- `8 CPU hours / 24 GiB` for each `n=4` complex route;
- `12 CPU hours` for an `n=4` real fallback;
- `24 CPU hours / 48 GiB` for each conditional `n=5` route.

## Execution Blockers

The holdouts remain mechanically sealed after this preregistration. Two
implementation obligations must close before a new public readiness commit:

1. emit and exactly verify a Nullstellensatz identity or complete
   ideal-membership trace, rather than grading a Groebner result by hash;
2. replace source-shaped inputs in the comparison auditor with an audit-owned
   pre-source reconstruction.

A modular rank loss, a selected-minor common root, a failed SOS search, or a
numerical residual can never be labeled an exact real counterexample. Such a
claim requires the full exact matrix to lose rank over an algebraic real
point and an explicit nonzero kernel vector.

## Claim Boundary

Even a complete pass would cover only the declared continuous north
projective patch, the two frozen couplings, the executed finite sizes, and the
quadratic-Majorana-plus-parity family. It would not prove a global tangent
frame, exclude higher-order or nonlocal charges, establish interacting
nonintegrability, or support Quantum PCP, NLTS, BQP, hardware, solved-frontier,
scientific-promotion, or new-credit claims.

## Next Gate

Implement a standalone exact certificate emitter and a non-circular audit
rebuild, publish their hashes in a new readiness commit, and only then open
`127/128` and `131/128` at `n=4`.
