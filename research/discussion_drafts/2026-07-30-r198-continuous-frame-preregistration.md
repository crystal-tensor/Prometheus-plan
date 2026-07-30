# Can a Continuous Jordan-Wigner Axis Hide the Charge That Five Frozen Frames Missed?

R197 tested five discrete fermionization frames and their linear union. Every
declared search returned only the two known commuting directions, identity and
the Hamiltonian. But five frames are still five points. What if an additional
quadratic conserved operator appears only at an untested angle?

R198 turns that loophole into a public, falsifiable experiment before opening
either frozen coupling.

## The experiment

We rotate the Jordan-Wigner parity axis through the complete XZ projective
line:

`P(t)=((1-t^2)X+2tZ)/(1+t^2)`.

For `n=4,5`, every Majorana-linear operator, every Hermitian quadratic
bilinear, and full parity are expanded into one exact polynomial commutator
matrix. Instead of sampling angles, we compute exact maximal minors. If their
primitive polynomial gcd has no real root and the projective endpoint is full
rank, no extra charge exists anywhere in this declared continuous family.

For `n=6,8,10`, we add a 72-frame exact rational pressure grid. The two
holdouts, `J=89/128` and `J=101/128`, remain unopened until the contract is
publicly committed.

## Why the method is plausible

An engineering-only coupling, `J=13/32`, was used to test the machinery.
At both `n=4` and `n=5`, adaptive quotient-field minors remove every apparent
real-root obstruction. The final common factors are powers of `1+t^2`, which
has no real root, and the projective endpoint is full rank. At the solvable
control `J=0,n=6,t=3`, the same pool recovers all six expected onsite charges.
None of this counts toward the frozen result.

## What would change our minds?

- A real root of the final exact gcd would identify a candidate hidden frame.
- A rank defect on any frozen rational frame would expose an explicit search
  direction for an additional conserved operator.
- Failure of the solvable control would invalidate the adversary.
- Disagreement from the independent third-prime implementation would reject
  the result.

## Where contributors can attack

Can you derive a more direct symbolic determinant factorization? Can you
construct a non-XZ or nonlinear frame family that escapes this parameterization?
Can you supply a cubic/quartic Majorana pool whose exact rank remains tractable?
Can you independently rebuild the polynomial Pauli expansion without importing
the R198 executor?

## Claim boundary

Passing R198 would close only the declared continuous XZ-plane
quadratic-Majorana-plus-parity family at `n=4,5` and the 72-frame grid at
`n=6,8,10`. It would not exclude general Bloch-sphere frames, nonlinear
mixtures, higher-order Majorana charges, nonlocal dualities, interacting
integrability, or larger-size drift. It would not prove nonintegrability,
quantum chaos, spectral hardness, Quantum PCP, NLTS, BQP separation, hardware
relevance, or a solved frontier. Scientific promotion and new credit remain
zero.

Artifacts:

- `benchmarks/B9_R198_continuous_frame_contract_v0.json`
- `tools/b9_r198_continuous_frame_stress.py`
- `benchmarks/B9_quantum_pcp_local_hamiltonian.yaml`
- `research/ops/agent_task_board.md`
