# If 49,153 Local Tails Reveal No Hidden Charge, Where Should We Look Next?

## Research question

At what point does a finite conserved-charge search stop being a small-basis
diagnostic and become a meaningful adversary for an apparent
Poisson-to-GOE-like crossover?

R196 does not answer that question globally. It does make the next escape
routes much harder to leave vague.

## What R196 tested

The protocol was published before acceptance execution with two unseen
couplings: `J=73/128` and `J=77/128`. An impossible positive-control phrase in
the first contract was corrected publicly before either holdout ran; the
holdouts, sizes, ranges, primes, rank rules, and claim boundaries did not
change.

R196 then executed three attacks:

- Complete position-dependent range-six Pauli searches at `n=10`. Both
  `16,384`-column rows have exact nullity two.
- One frozen translation-summed range-eight search at `J=73/128,n=10`.
  It contains `49,153` candidates, a `163,840`-word complete parent basis, and
  a `253,951`-word output basis. Its exact nullity is two.
- Bulk translation sums through range six plus independent left/right
  corrections through range four. All `4/4` `3,457`-column rows at `n=9,10`
  have exact nullity two.

Identity and the Hamiltonian are explicit rational kernels in every accepted
row. Rank `ncols-2` under both declared primes therefore certifies exact
rational nullity two inside each finite ansatz.

## Why trust the computation?

The main executor passes `15/15` requirements under two prime fields. A
separate auditor:

- imports none of the R193-R196 construction modules;
- uses a different integer encoding of Pauli words;
- rebuilds all seven candidate bases, sparse commutators, and SHA-256 digests;
- recomputes every rank under a third prime, `1,000,037`;
- recovers nullity two on all seven rows;
- independently verifies the `J=0` extra-charge witnesses;
- reports zero errors.

The contract hash is `afc5a721...`, the protocol hash is `8f20eb86...`, and
the result payload hash is `0116a213...`.

## What remains genuinely open?

R196 closes only three finite ansatz families. A hidden integrable structure
could still live in:

- range-nine or adaptive quasi-local tails;
- coefficients that depend explicitly on system size;
- nonlocal or interacting boundary dressings;
- a nonlocal duality;
- a nonstandard fermionization;
- a genuinely interacting family of conserved operators;
- finite-size drift visible only beyond the current sparse spectrum window.

## Questions for contributors

- What is the strongest range-nine or adaptive-tail ansatz that can be frozen
  before looking at its null space?
- Can a size-dependent boundary charge be specified without fitting it to the
  observed finite-size data?
- Which nonlocal duality is the most credible adversary for
  `sum_i[-X_i+(3/4)Z_i]+J sum_i Z_i Z_{i+1}`?
- Can anyone reproduce the `49,153`-column rank in Sage, Julia, Rust, GAP, or
  another exact algebra stack?
- Is there an explicit integrable model that passes R193-R196 yet reveals its
  extra charge only after a nonlocal transformation?

## Contribution-sized entry points

- Rebuild one R196 matrix and third-prime rank in an independent language.
- Propose a preregistered range-nine translation basis with a positive control.
- Implement one explicit nonlocal-duality or fermionization candidate.
- Design a size-dependent boundary family with a no-post-selection contract.
- Add sparse shift-invert spectra at a larger `n` under a new frozen holdout.

## Claim boundary

R196 does not establish nonintegrability, quantum chaos, spectral hardness, an
all-size or all-coupling theorem, complete quasi-local exclusion, arbitrary
boundary-dressing exclusion, Quantum PCP, NLTS, BQP separation, hardware
relevance, or a solved frontier. Scientific promotion is false and new credit
remains zero. The next task is `T-B9-011`.

Artifacts: [contract](https://github.com/crystal-tensor/Prometheus-plan/blob/main/benchmarks/B9_R196_extended_tail_charge_contract_v0.json), [result](https://github.com/crystal-tensor/Prometheus-plan/blob/main/results/B9_R196_extended_tail_charge_stress_v1.json), [independent audit](https://github.com/crystal-tensor/Prometheus-plan/blob/main/results/B9_R196_independent_audit_v1.json), [report](https://github.com/crystal-tensor/Prometheus-plan/blob/main/research/B9_R196_extended_tail_charge_stress.md), [method](https://github.com/crystal-tensor/Prometheus-plan/blob/main/tools/b9_r196_extended_tail_charge_stress.py), and [research dashboard](https://htmlpreview.github.io/?https://github.com/crystal-tensor/Prometheus-plan/blob/main/research/axiom_horizon_landing.html).
