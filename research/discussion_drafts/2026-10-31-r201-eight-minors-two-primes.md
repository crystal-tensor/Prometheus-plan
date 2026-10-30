# If four degree-184 determinants share one factor, what should we lift first?

The R201 continuous-projective-patch route now has eight public modular determinant artifacts: four frozen `37x37` minors, each evaluated over two different primes. A project-owned verifier independently reconstructs the matrices, replays 40 public point evaluations, and multiplies every finite-field factorization back to the original polynomial.

The surprising structure is stable across both primes. All four minors share exactly `D^44`, where `D=a^2+b^2+c^2`. Removing this degree-88 common factor leaves a degree-96 modular residual in each field. The residual term counts are 2,401, 464, 590, and 450, but direct quotient lifting remains conditional on characteristic-zero divisibility.

The tempting conclusion would be that the hard part is now solved. It is not. Two primes do not prove a characteristic-zero gcd, and they do not supply an integer coefficient bound. The frozen scientific couplings remain unopened, promotion remains false, and credit remains zero.

The useful question for contributors is narrower:

> What is the sharpest replayable coefficient bound for the original degree-184 integer determinants, and can we reduce the CRT budget without assuming characteristic-zero `D^44` divisibility?

High-value contributions include:

- an independent coefficient-bound derivation;
- a second implementation of sparse modular determinant replay;
- a characteristic-zero gcd certificate;
- a prime-selection strategy with explicit bad-prime exclusions;
- adversarial examples where two-prime factor stability fails to lift.

The current evidence validates classical exact algebra used to study a quantum many-body model. It is not quantum-hardware evidence, a Quantum PCP result, an NLTS theorem, a BQP separation, or a solved frontier.
