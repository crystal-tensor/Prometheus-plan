# Can four matching prime worlds still lie about the integer answer?

R201 has completed its second planned CRT shard. Four more frozen degree-184 determinants were computed over `GF(536,870,879)`, bringing the execution ledger to two added primes and `8/56` new artifacts.

The reassuring evidence is broader than a successful computation. A project-owned verifier rebuilt all 16 determinant artifacts now available across four primes, reconstructed every source matrix at five public points, and obtained `80/80` exact matrix-determinant matches. Every minor also preserves the same monomial support in all four finite fields.

The verifier then walked all `17,205` homogeneous coefficient slots per minor, including absent modular terms as explicit zeros. All `275,280/275,280` slot-prime round trips pass after symmetric partial CRT.

But four agreeing prime worlds still do not determine the integer world. The combined modulus has 107 bits, while the proved uniqueness threshold has 427 bits. The current symmetric representatives can be replayed exactly, yet they are not certified integer coefficients.

Current execution ledger:

```text
new primes complete:       2/14
new artifacts complete:    8/56
new artifacts remaining:  48
```

The contributor question is:

> What invariant could detect a misleading partial CRT reconstruction before the full 427-bit uniqueness threshold is reached?

Useful attacks include:

- construct a bounded-looking symmetric representative that changes after the next prime;
- derive a coefficient-stability diagnostic that does not assume the unknown integer bound is already saturated;
- independently reproduce one of the four 68,820-roundtrip minor digests;
- identify determinant-specific bad-prime conditions not caught by support equality;
- propose a proof-safe batching strategy for the remaining 48 determinant artifacts.

This is verified modular execution progress. It is not quantum-hardware evidence, integer reconstruction, characteristic-zero `D^44` divisibility, an ideal-membership certificate, a Quantum PCP or NLTS theorem, a BQP separation, a solved frontier, promotion, or new credit.
