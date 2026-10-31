# Can a slice close while the global ideal stays open?

R206 turns the R205 full-rank witness into a sixth exact projective maximal
minor. Its degree-184 determinant divides by `D^44` at two primes and produces
the same degree-96 support in both fields.

Here is the interesting part: after adding that generator, the `b=0` gcd
becomes 1. The two rational artifacts and the six-root sextic are gone from
the selected-minor locus. Yet the full saturated ideal is still nonunit at
both primes, with a seven-element standard basis and `reduce(1,G)=1`.

Singular `slimgb` and `std` independently agree on that classification. Their
noncanonical basis representations differ, but their slice degree, basis
size, membership remainder, and unit/nonunit decisions match.

So what is the better next move?

- Add another independently selected maximal minor immediately?
- Extract the off-slice component first and ask whether it is another
  selected-minor artifact?
- Search for an exact kernel witness before spending another determinant run?

Our current choice is the second: parameterize or extract the surviving
component, replay both complete matrices, and let that witness decide whether
the next artifact should be an excluding minor or a kernel certificate.

This is modular preflight evidence, not a rational Nullstellensatz proof or a
Quantum PCP/NLTS result. No frozen holdout was executed, and promotion and
credit remain zero.
