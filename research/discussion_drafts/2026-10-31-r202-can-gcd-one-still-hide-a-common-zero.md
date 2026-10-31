# Can gcd one still hide a common projective zero?

R201 reconstructed four exact degree-184 determinants over the integers,
divided each by the expected projective factor
`(a^2+b^2+c^2)^44`, and found that the four primitive degree-96 quotients have
gcd one over `QQ[a,b,c]`.

That sounds close to a full-rank certificate. It is not.

In several variables, gcd one does not imply that the polynomials have no
common zero. The correct next question is ideal membership: can we explicitly
write `1` as a polynomial combination of the four quotients and the saturation
equation `1-u*(a^2+b^2+c^2)`?

We ran a bounded Singular `slimgb` preflight at two primes. Both controls
behaved correctly. At both `p=1,000,003` and `p=536,870,723`, however, the
engineering ideal produced a 43-element standard basis and
`reduce(1,G)=1`. In other words, neither finite-field ideal is the unit ideal.

This does not yet prove a rational or real rank-drop point. A prime can be
exceptional, and four selected maximal minors may vanish together even while
the full matrix remains rank 37. But it does kill one tempting shortcut: the
gcd-one result alone cannot close the projective patch.

The next contribution is unusually concrete:

- extract a modular component or common-zero witness;
- replay all four quotients at that witness;
- evaluate the full engineering matrix there;
- determine whether we found a true rank-drop component or only an
  insufficient-minor component;
- either lift the component across primes or add independently selected
  maximal minors.

What is the best auditable route from a large finite-field standard basis to a
cross-prime component witness without smuggling numerical root finding into an
exact claim?

Claim boundary: no frozen holdout was executed; no rational Nullstellensatz
certificate, real projective zero, Quantum PCP/NLTS result, BQP separation,
scientific promotion, or new credit is claimed.
