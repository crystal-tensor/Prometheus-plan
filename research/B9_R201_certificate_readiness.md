# B9 R201 Certificate Readiness and Audit Reset

- Date: `2026-10-31`
- Track: `B9`
- Status: `certificate infrastructure verified; engineering certificate incomplete`
- Frozen holdouts executed: `false`
- Readiness blocker closed: `false`
- Scientific promotion: `false`
- New credit: `0`

## Question

Can the R201 rank claim be made replayable without asking an independent reviewer to trust the same symbolic executor that produced it?

## Exact Certificate Engine

`tools/b9_r201_nullstellensatz_certificate.py` now tracks the transformation from original ideal generators to a nonzero constant. It emits every generator and multiplier as a sorted sparse rational polynomial. `tools/b9_r201_certificate_replay.py` uses only the Python standard library to multiply, add, hash, and compare the exact identity.

The engine self-test passes:

- schema: `sparse-nullstellensatz-v1`;
- variables: `u,a,b,c`;
- generators: `3`;
- generator terms: `6`;
- multiplier terms: `3`;
- replay errors: `0`;
- generator bundle hash: `5c4eaf21310e40cf12cda0d28a3efb44338a35b3a162ac78c3f96cf50f02ff1b`;
- identity hash: `8cead437cef22243477e6dd55d79c24532b72cb0b5ef23f65d44bf3c1200cf5f`.

Three mutations are rejected: one multiplier coefficient, one generator exponent, and the generator-bundle hash. This validates the transport and replay format. It is not the engineering `J=13/32` certificate.

This is an engine self-test, not yet the degree-184 engineering certificate.

## Adversarial Audit Finding

The original R201 independent auditor is not accepted as a final independent reconstruction. Its post-result path used the source result's `minor_records` length to decide how many minors to rebuild. A forged source-shaped zero-minor row could therefore pass that local comparison when paired with the matching negative fields.

The frozen holdouts remain protected because the public contract still sets `frozen_holdouts_may_execute=false`, and the main executor rejects execution before evaluating `J=127/128` or `J=131/128`.

## Audit-Owned Dense Reconstruction

`tools/b9_r201_presource_manifest.py` now constructs the engineering object without importing the R201 source executor or independent auditor. It uses exact `2x2` Pauli matrices, Kronecker products, direct Majorana candidates, dense commutators, and 256 real Hermitian upper-triangle coordinates.

The pre-source design seal records:

- dense operator dimension: `16`;
- audit matrix shape: `256x37`;
- candidate-label hash: `8641091b90145c6d05a2c0f754232a8dc78e0c1b93004678b9895cabed0b1e65`;
- nonzero polynomial entries: `9,472`;
- coefficient-tensor hash: `48370c7d01167fbd734dad2ccc941f312254b268299a48a21265c4c7e43a4e42`;
- audit-owned engineering anchors: `4/4` at rank `37` modulo `1,000,003`;
- source result fields consumed for reconstruction: `[]`;
- frozen holdout matrix, row selection, minor, solver, and scientific decision execution: all `false`;
- mutation rejection: `3/3`.

The dense bilinear columns retain only nonzero powers of `D=a^2+b^2+c^2` relative to the source Pauli-coordinate columns. This changes the coefficient tensor representation but preserves the declared real projective rank problem where `D` is nonzero.

## Exact Minor Backend

Singular `4.4.1` is available as an external discovery backend. `tools/b9_r201_singular_minor_bridge.py` binds the public engineering matrix and the four unique row-set hashes, then requests exact degree-184 determinants. Any resulting polynomial must still be serialized, hash-bound, and replayed by project-owned exact code.

The first public engineering row set now completes as an exact modular bridge validation over `GF(1,000,003)`. Its frozen row-set hash is `2525123337c76d67569a4153a099dfa5e18b28649d8655bdfe2e79a6585b5dae`; the determinant has total degree `184`, `8,649` nonzero terms, canonical-term hash `7b1fbbf96d1761b92f507fd96f01676ddcc26486b4e4075689e76795ffe93c9b`, and Singular elapsed time `148.98323` seconds. The result is a modular bridge validation only. It shows that the bound matrix, row set, determinant backend, parser, and canonical serializer can complete together; it is not the characteristic-zero engineering certificate or an ideal-membership certificate.

A direct SymPy `domain-ge` attempt on the first `37x37` engineering minor was stopped after `576.02` seconds without producing the determinant. This is a resource diagnostic, not evidence for or against the rank claim.

No Singular conclusion, Groebner hash, modular rank loss, selected-minor root, numerical root, or failed SOS search is accepted by itself.

## Remaining Gates

1. Freeze audit-owned dense row selection and the exact expected minor count.
2. Reproduce the `79/42/37` positive control and six onsite witnesses in the dense representation.
3. Compute the four characteristic-zero engineering minors and emit a real `J=13/32` ideal-membership certificate; the first modular minor does not satisfy this gate.
4. Bind the certificate generators to independently reconstructed dense minors.
5. Run pre-source holdout reconstruction in an isolated filesystem where the main result path is unavailable.
6. Publish a new readiness commit before changing any execution permission.

The conditional `n=5` route, global chart coverage, higher-order charges, nonlocal dualities, interacting integrability, Quantum PCP, NLTS, BQP separation, hardware relevance, solved-frontier status, scientific promotion, and new credit all remain unresolved or zero.
