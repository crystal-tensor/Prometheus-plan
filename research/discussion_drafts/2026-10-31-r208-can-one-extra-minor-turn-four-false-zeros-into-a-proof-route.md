# Can One Extra Minor Turn Four False Zeros into a Proof Route?

R206 left an off-slice component. R207 showed that its four algebraic points
were all false rank drops of a selected six-minor system, not rank drops of the
complete matrix. That raised a sharper question:

> If one fixed maximal minor is nonzero at all four points, does promoting it
> to a full polynomial close the entire saturated ideal, or does another
> hidden component appear?

R208 computes that `37x37` determinant from the source matrix at two large
primes. In both fields it has degree 184 and 5,309 terms. Exact factorization
and sparse recomposition remove `D^44`, leaving a degree-96, 821-term quotient
with the same monomial support in both fields.

After appending this seventh quotient, the saturated ideal becomes the unit
ideal at both primes: Singular returns basis `[1]` and `reduce(1,G)=0`. The
four-point R207 radical chart also becomes unit. An independent `std` audit
replays that chart directly: vector-space dimension falls from 4 to 0 at both
primes.

The interesting part is what this does **not** prove. Two finite fields do not
give a `QQ` Nullstellensatz certificate. We have a strong route-selection
signal, not a characteristic-zero global theorem, Quantum PCP result, NLTS
theorem, hardware result, or new project credit.

The next contribution opportunity is unusually concrete:

1. reconstruct the fifth, sixth, and seventh quotient coefficients over
   `ZZ` with proved bounds;
2. find an explicit rational identity showing the seven quotients and the
   saturation equation generate 1;
3. verify the identity independently before opening the sealed coupling
   holdouts.

Which route is likely to be smaller: direct rational Groebner computation,
modular certificate lifting, or a quotient-ring interpolation certificate
built from the components already classified in R203-R207?

No frozen holdout was executed. No quantum hardware was used. The full report
and machine-readable artifacts keep those boundaries explicit.
