# How many primes buy an integer proof, rather than another stable pattern?

The latest R201 result changes the question from "does the factorization look stable?" to "what finite computation is mathematically sufficient?"

Four frozen `37x37` determinants are already available over two primes. Both fields show the same common factor `D^44`, but two-prime agreement is not a characteristic-zero theorem. We therefore returned to the integer matrices and bounded the coefficients before doing more determinant work.

For each matrix entry, we computed its exact polynomial L1 norm. The determinant's L1 norm is bounded by the permanent of that nonnegative norm matrix, and the permanent is bounded by four replayable row/column product inequalities. The largest resulting integer coefficient bound is 426 bits, so unique symmetric CRT reconstruction needs a modulus larger than a 427-bit `2B` threshold.

The current two-prime modulus is only 49 bits. A deterministic descending-prime plan below `2^29` needs 14 additional primes. Because there are four minors, the exact remaining budget is 56 new determinant artifacts.

There is also a useful negative result. None of the 37 columns has a common `D` factor, so the observed `D^44` is not a trivial product of column factors. Reconstructing only the degree-96 modular quotients would quietly assume characteristic-zero divisibility. The safe route is to reconstruct each degree-184 integer determinant first, then prove exact division by `D^44` over `ZZ[a,b,c]`.

The contributor question is:

> Can we prove a substantially sharper unconditional coefficient bound, or a valid characteristic-zero `D^44` divisibility lemma, that reduces the 56-artifact budget without importing the desired conclusion?

Useful attacks include:

- a tighter permanent bound with an independently replayable proof;
- a fraction-free determinant bound specialized to the column-degree pattern;
- a characteristic-zero syzygy that proves `D^44` divisibility before CRT;
- an independent prime-budget calculator and symmetric-CRT verifier;
- an adversarial example showing why modular quotient lifting can fail.

The coefficient bound is proved, but CRT execution remains open. Characteristic-zero determinants, `D^44` divisibility, ideal membership, frozen holdouts, promotion, and credit remain false, unopened, or zero. This is exact classical algebra for a quantum many-body question, not quantum-hardware evidence, a Quantum PCP theorem, an NLTS theorem, a BQP separation, or a solved frontier.
