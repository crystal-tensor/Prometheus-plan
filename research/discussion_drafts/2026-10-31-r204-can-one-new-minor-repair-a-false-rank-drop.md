# Can one new maximal minor repair a false rank-drop certificate?

Four exact maximal minors vanished at two rational projective points, yet the
complete quantum-operator matrix stayed full rank. That made the next move
look simple: add one independently selected maximal minor that is nonzero at
both points.

R204 does exactly that.

The new degree-184 determinant is reconstructed over two finite fields. After
exactly removing `D^44`, its degree-96 quotient has 1,113 terms and is nonzero
at both `[2:0:1]` and `[1:0:-2]`. The two known false rank drops disappear.

But does one repaired witness repair the whole certificate?

No. On the `b=0` slice, the common factor falls from degree 16 to degree 6:
the two fivefold rational factors vanish, while the same seven-term sextic
survives. In the full saturated ideal, the standard basis contracts from 43
elements to 10 at both declared primes, but `reduce(1,G)=1` still says the
ideal is nonunit.

This leaves a sharper question for algebraists, symbolic-computation
researchers, and quantum-complexity theorists:

> Is the remaining sextic a genuine full-matrix rank-drop component, or just
> the next selected-minor artifact waiting for another independent witness?

The next contribution can be very concrete: isolate the sextic's exact
projective roots, evaluate the full `238x37` Pauli matrix and `256x37` dense
matrix over their algebraic extensions, and return either a nonzero maximal
minor or a nonzero kernel vector.

No frozen holdout was executed. This is not a Quantum PCP, NLTS, BQP,
integrability, or solved-frontier claim. It is a smaller and more useful
object: a reproducible algebraic fork where the next PR can decisively say
"artifact" or "rank drop."
