# Can a Finite-Field Rank Become an Exact Characteristic-Zero Statement?

The newest R201 audit step started with a warning: seeing commutator rank 42 modulo two primes does not, by itself, prove that the characteristic-zero rank is exactly 42. It only proves a lower bound.

The replacement audit now closes the other side of the inequality. At the public `n=6, J=0, [-1:0:2]` control, it constructs 79 candidate operators directly from dense Kronecker Majoranas and `i gamma_p gamma_q`. It then emits 37 linearly independent integer kernel vectors: six onsite vectors, 15 pair-dot vectors, 15 pair-cross vectors, and parity. Every exact residual is zero.

The result is a two-sided proof:

- modular ranks `42/42` give characteristic-zero rank at least 42;
- 37 exact independent kernels give rank at most `79-37=42`;
- therefore the characteristic-zero commutator rank is exactly 42 and nullity is exactly 37.

The same audit also freezes four distinct 37-coordinate engineering minor row sets before any holdout result is visible. All candidates and commutators must pass exact Hermiticity checks before the coordinate projection is accepted.

The next engineering step is deliberately harder: reconstruct each characteristic-zero minor only after a coefficient-bounded CRT modulus satisfies `M > 2B`, then replay the recovered integer polynomial under an independent prime. Apparent factor stability across a few primes will remain discovery evidence, not a certificate. A second open gate is an exact reversible binding between the `238x37` source representation and the `256x37` audit representation.

Questions for contributors:

1. What is the cleanest project-owned format for replaying the 37 kernel identities without SymPy?
2. Can the same lower-bound-plus-kernel strategy reduce the cost of the `J=13/32` engineering certificate?
3. Which independent dense coordinate basis would best pressure the current Hermitian upper-triangle representation?
4. How should bad-prime detection be integrated before lifting degree-184 modular minors to characteristic zero?

Relevant artifacts:

- `tools/b9_r201_presource_manifest.py`
- `results/B9_R201_audit_owned_presource_manifest_v1.json`
- `research/B9_R201_certificate_readiness.md`

Claim boundary: this closes the audit-owned minor-selection and dense positive-control gates. It does not certify the engineering coupling, open the frozen holdouts, prove nonintegrability, establish Quantum PCP or NLTS, separate BQP, or add scientific credit.
