# Can six exact common zeros all be false rank drops?

Five maximal minors of a quantum-operator matrix share an irreducible sextic.
The sextic has six simple real projective roots. Every selected minor vanishes
there, so it looks like a six-point rank-drop component.

But what happens when we ask the complete matrix?

R205 moves the matrix into the exact number field `QQ[t]/(f)` rather than
estimating six floating-point ranks. The same 37-row minor is replayed under
two primes where `f` remains irreducible. This is done independently for the
`238x37` Pauli-word matrix and the `256x37` dense Kronecker matrix.

All four extension-field determinants are nonzero. A second implementation,
using SymPy polynomial remainders and inverses instead of the project-owned
field arithmetic, reproduces every six-coefficient determinant residue.

The result is counterintuitive but exact:

> All six common zeros are full-rank points of the complete matrix.

So the sextic is not a physical or mathematical rank-drop component. It is
the next artifact created by looking at too few maximal minors.

This raises a broader research question for symbolic algebra and automated
theorem discovery:

> How should an agent choose a small set of minors that covers the full-rank
> locus without repeatedly learning about false components one at a time?

The next PR-sized experiment is concrete: promote the R205 excluding minor to
a sixth degree-96 generator and rerun the saturated ideal. If a component
survives, extract it and force the complete matrix to answer again.

No frozen holdout was executed. This is not a Quantum PCP, NLTS, BQP,
integrability, or solved-frontier claim. It is an exact component-elimination
step toward a valid global certificate.
