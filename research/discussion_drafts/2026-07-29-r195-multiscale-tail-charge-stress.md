# How Many Local Shells Must Fail Before "No Hidden Charge" Means Anything?

## Research question

When a finite spin chain shows no conserved operator beyond the identity and
Hamiltonian, how much larger must the search become before the absence is
scientifically informative rather than an artifact of a narrow ansatz?

## What R195 tested

R195 froze two couplings that did not appear in the R193 or R194 observed
grids: `J=53/128` and `J=69/128`.

It then attacked the surviving candidate in three different ways:

- Complete position-dependent range-six Pauli bases at `n=8,9`. All `4/4`
  rows have exact modular nullity two.
- Translation-summed range-seven bases at `n=9,10`, with `12,289` candidate
  columns per row. All `4/4` rows have exact modular nullity two.
- Boundary-dressed bases containing every bulk translation sum through range
  six plus independent left/right Pauli corrections through range three.
  These `3,169`-column searches also have exact nullity two on `4/4` rows.

At the integrable control `J=0`, the same three adversaries recover nullities
`2,268`, `2,509`, and `701`. The tests therefore detect abundant extra
conserved structure when it is actually present.

Two complete executions are byte-identical. A separate portfolio
implementation rebuilds every candidate basis, commutator matrix, digest, and
two-prime exact rank. R195 passes `16/16` with no audit errors or warnings.

## Why this is interesting

The result closes three finite escape routes at once: a new system size for
the complete range-six search, one additional translation shell, and explicit
finite edge corrections. It also makes the remaining uncertainty more
specific.

The strongest surviving escape routes are no longer simply "maybe range
five." They are range eight or longer tails, larger or size-dependent boundary
dressings, nonlocal dualities, nonstandard fermionizations, interacting
integrability, and finite-size drift.

## Questions for contributors

- Can complete range six be pushed to `n=10` without losing exact sparse-rank
  reproducibility?
- Which range-eight translation basis gives the best information gain per
  candidate column?
- How should a size-dependent boundary tail be preregistered without fitting
  it to the observed null space?
- Which nonlocal duality or nonstandard fermionization is the strongest
  adversary for this Hamiltonian?
- Can an integrable adversarial model be constructed that passes all three
  R195 tests but exposes a longer or nonlocal conserved structure?

## Contribution-sized entry points

- Independently reproduce one R195 row in Sage, Julia, Rust, or another exact
  algebra stack.
- Add complete range-six `n=10` support with deterministic sparse elimination.
- Implement a range-eight translation-summed search.
- Add boundary corrections through range four under a frozen protocol.
- Propose and test one explicit nonlocal-duality or fermionization candidate.

## Claim boundary

R195 does not establish nonintegrability, quantum chaos, spectral hardness,
an all-size or all-coupling theorem, complete quasi-local exclusion, arbitrary
boundary-dressing exclusion, Quantum PCP, NLTS, BQP separation, or a solved
frontier. Scientific promotion remains false and new credit remains zero. The
next task is `T-B9-010`.

Artifacts: [result](https://github.com/crystal-tensor/Prometheus-plan/blob/main/results/B9_R195_multiscale_tail_charge_stress_v1.json), [report](https://github.com/crystal-tensor/Prometheus-plan/blob/main/research/B9_R195_multiscale_tail_charge_stress.md), [method](https://github.com/crystal-tensor/Prometheus-plan/blob/main/tools/b9_r195_multiscale_tail_charge_stress.py), and [research dashboard](https://htmlpreview.github.io/?https://github.com/crystal-tensor/Prometheus-plan/blob/main/research/axiom_horizon_landing.html).
