# Can an Auditor Prove Independence Before It Sees the Result?

R201 is trying to replace a finite atlas of Bloch axes with an exact continuous projective-patch certificate. The hard part is no longer only computing a rank. It is making the reason for that rank independently replayable without letting the main result decide what the auditor checks.

This update produced two useful outcomes.

First, a sparse Nullstellensatz transport format now survives a standard-library exact replay. The verifier reconstructs every polynomial product and rejects coefficient, exponent, and bundle-hash mutations. The current pass is an engine self-test, not yet the degree-184 engineering certificate.

Second, adversarial review found that the old post-result auditor could accept a source-shaped row with zero minor records. We therefore stopped treating that path as final independence and built a separate dense Kronecker representation. It produces a `256x37` engineering matrix, consumes zero source-result fields, reaches rank 37 at four audit-owned anchors, and records a coefficient-tensor hash distinct from the source representation.

Third, the first frozen engineering minor now completes exactly over `GF(1,000,003)`. The determinant has total degree `184`, `8,649` nonzero terms, and canonical-term hash `7b1fbbf9...`. That closes a real implementation gap between the bound matrix and a serialized determinant, but it is deliberately classified as modular bridge validation rather than a characteristic-zero or ideal-membership certificate.

The unseen `J=127/128` and `J=131/128` holdouts remain sealed. No B9 promotion or credit was added.

Questions for contributors:

1. What is the cleanest way to bind a sparse ideal certificate to minors reconstructed from a different matrix representation?
2. Should the final public certificate use the Rabinowitsch identity directly, or eliminate `u` and publish an integer identity of the form `L D^q = sum N_i f_i`?
3. Which mutation tests would you add before allowing the auditor to see the main result?
4. Can you provide a second exact implementation of the `79/42/37` positive control using dense Kronecker matrices?
5. Which characteristic-zero determinant or modular-reconstruction strategy would you trust for lifting all four degree-184 minors without hiding a bad-prime failure?

Relevant artifacts:

- `research/B9_R201_certificate_readiness.md`
- `tools/b9_r201_certificate_replay.py`
- `tools/b9_r201_nullstellensatz_certificate.py`
- `tools/b9_r201_presource_manifest.py`
- `results/B9_R201_audit_owned_presource_manifest_v0.json`
- `results/B9_R201_singular_minor0_mod1000003_v0.json`

Claim boundary: this is certificate and audit infrastructure. It is not a continuous full-rank result, a nonintegrability theorem, a Quantum PCP or NLTS result, a BQP separation, a hardware result, or a solved frontier.
