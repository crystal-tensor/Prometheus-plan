# When do matching modular shards become a proof rather than a pattern?

The first new R201 CRT shard is complete. Four frozen degree-184 determinants were computed over `GF(536,870,909)`, the first additional prime in the public 14-prime plan.

The reassuring part is not merely that each determinant finished. A project-owned verifier rebuilt all 12 artifacts now available across three primes, replayed every matrix determinant at five public points, and obtained `60/60` matches. The four monomial supports also remain identical across all three primes.

The verifier then walked every one of the `17,205` homogeneous coefficient slots for each minor. It formed partial symmetric CRT residues and reduced them back modulo all three source primes. All `206,460/206,460` slot-prime round trips pass.

But the uncomfortable boundary is the important one: the combined modulus has only 78 bits, while the proved uniqueness threshold has 427 bits. These partial residues are not integer coefficients. Stable support over three primes is still not a characteristic-zero theorem.

Current execution ledger:

```text
new primes complete:       1/14
new artifacts complete:    4/56
new artifacts remaining:  52
```

The contributor question is:

> What failure modes can survive several matching prime shards, and what additional invariant should we audit before spending the remaining 52 determinant runs?

Useful attacks include:

- construct a polynomial whose support is stable over several primes but whose symmetric CRT representative is still misleading;
- propose a cross-prime coefficient invariant stronger than support equality but weaker than full reconstruction;
- independently reproduce the 17,205-slot CRT digest;
- identify bad-prime conditions specific to the R201 determinant matrices;
- find a proof-safe way to batch or compress the remaining determinant executions.

This is verified modular execution progress. It is not quantum-hardware evidence, integer reconstruction, characteristic-zero `D^44` divisibility, an ideal-membership certificate, a Quantum PCP or NLTS theorem, a BQP separation, a solved frontier, promotion, or new credit.
