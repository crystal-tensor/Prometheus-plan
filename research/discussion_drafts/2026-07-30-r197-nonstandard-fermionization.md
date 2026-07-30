# If Five Jordan-Wigner Frames Reveal No Hidden Charge, Is the Escape Continuous or Interacting?

## Research question

Could the surviving B9 candidate look nonintegrable only because we chose the
wrong Jordan-Wigner parity axis?

R197 attacks that question with five exact fermionization frames, including a
rational frame aligned with the tilted onsite field. The answer is negative
inside the declared quadratic-Majorana spaces, but the larger question remains
open.

## What R197 froze before execution

The public contract fixes unseen couplings `J=79/128` and `J=83/128`, sizes
`n=8,9,10`, two prime fields, exact rational frame algebra, and five
Jordan-Wigner constructions:

- standard Pauli-X, Pauli-Y, and Pauli-Z parity axes;
- tilted A, where `A=(-4X+3Z)/5` is aligned with the onsite field;
- tilted B, where `B=(3X+4Z)/5` is the orthogonal rational axis.

Each single-frame family contains identity, the exact Hamiltonian, every
Majorana-linear operator, every Hermitian quadratic Majorana bilinear, and full
parity. A sixth family forms the independent operator-space union of all five
frames.

## What happened

- All `30/30` single-frame rows have exact nullity two.
- All `6/6` five-frame-union rows have exact nullity two.
- The largest union at `n=10` contains `871` independent operators,
  `196,703` commutator nonzeros, and a `67,296`-word output basis.
- At the solvable `J=0,n=8` control, tilted A and the all-frame union recover
  nullities `66` and `91`.
- All eight onsite tilted charges in the positive control are independently
  verified to commute and lie in the searched space.

Identity and the Hamiltonian are explicit kernels in every accepted row.
Rank `ncols-2` under both frozen primes therefore certifies exact rational
nullity two inside each declared finite operator space.

## Why trust the computation?

The main executor passes `11/11` requirements. A separate auditor:

- imports none of the R193-R197 construction modules;
- uses sparse symplectic Pauli `(x,z)` bit pairs;
- reconstructs all rational frames independently;
- rebuilds all 36 bases, commutator matrices, and digests;
- recomputes every rank under a third prime, `1,000,037`;
- reproduces all 36 nullities and the positive-control nullities `66/91`;
- reports zero errors.

The contract hash is `6ab7640f...`, the protocol hash is `19605d12...`, and
the result payload hash is `ae331194...`.

## What remains genuinely open?

R197 closes five finite quadratic-Majorana-plus-H frames and their linear
union. An integrable escape could still require:

- a continuously rotated fermionization frame;
- nonlinear mixtures between frames;
- cubic or quartic Majorana charges;
- Kramers-Wannier or another explicit nonlocal duality;
- adaptive or size-dependent strings;
- genuinely interacting conserved operators;
- range-nine or longer quasi-local tails;
- larger-size spectral drift.

## Questions for contributors

- Can the frame angle be treated symbolically so that all continuously rotated
  quadratic-Majorana charges are tested at once?
- Which quartic-Majorana basis gives the strongest exact, preregistered next
  adversary without exploding beyond reproducible sparse rank?
- Is there an explicit Kramers-Wannier-like duality that maps this tilted-field
  Ising family to a known integrable line?
- Can anyone reproduce the `871`-column union and its third-prime nullity in
  Sage, Julia, Rust, GAP, Mathematica, or another exact algebra stack?
- What positive control would prove that a proposed interacting-charge search
  can recover a nonquadratic conserved quantity?

## Contribution-sized entry points

- Rebuild one R197 single-frame or union matrix in an independent language.
- Derive a symbolic continuous-frame commutator condition.
- Propose a preregistered quartic-Majorana basis with a solvable positive
  control.
- Implement one explicit nonlocal-duality candidate with exact replay.
- Add a range-nine or larger-size test under new frozen holdouts.

## Claim boundary

R197 does not establish nonintegrability, quantum chaos, spectral hardness, an
all-size or all-coupling theorem, exclusion of all fermionizations or
dualities, Quantum PCP, NLTS, BQP separation, hardware relevance, or a solved
frontier. Scientific promotion is false and new credit remains zero. The next
task is `T-B9-012`.

Artifacts: [contract](https://github.com/crystal-tensor/Prometheus-plan/blob/main/benchmarks/B9_R197_nonstandard_fermionization_contract_v0.json), [result](https://github.com/crystal-tensor/Prometheus-plan/blob/main/results/B9_R197_nonstandard_fermionization_stress_v1.json), [independent audit](https://github.com/crystal-tensor/Prometheus-plan/blob/main/results/B9_R197_independent_audit_v1.json), [report](https://github.com/crystal-tensor/Prometheus-plan/blob/main/research/B9_R197_nonstandard_fermionization_stress.md), [method](https://github.com/crystal-tensor/Prometheus-plan/blob/main/tools/b9_r197_nonstandard_fermionization_stress.py), and [research dashboard](https://htmlpreview.github.io/?https://github.com/crystal-tensor/Prometheus-plan/blob/main/research/axiom_horizon_landing.html).
