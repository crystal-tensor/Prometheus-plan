# How Far Must a Conserved Charge Reach Before "Chaos" Becomes Credible?

## Research question

If a spin chain has no conserved operator beyond the identity and Hamiltonian
through support range five, is that meaningful evidence against hidden
integrability, or are we only failing to search far enough?

## What R194 tested

R194 stress-tested the surviving R193 candidate at four preregistered,
previously unseen couplings. For system sizes 8, 9, and 10, it built the
complete position-dependent Pauli basis through contiguous support range five.
All 12 rows had exact modular nullity two under two independent primes: only
the explicit identity and Hamiltonian kernels remained.

One larger complete range-six challenge at coupling 31/64 and size 8 contained
10,240 candidate columns and 15,871 output rows. Both modular fields again gave
rank 10,238 and nullity two. A separate translation-summed six-shell proxy
passed all 12 coupling/size rows with the same nullity.

The same machinery was then run at the known integrable control J=0. It found
minimum nullities of 798 for the complete range-five basis and 673 for the
translation-summed range-six basis, showing that the test does detect abundant
extra conserved structure when it is present.

## Why this is interesting

The result moves the question from a small local ansatz to a much larger,
source-bound exact rank problem. It also introduces a deterministic
minimum-degree sparse elimination method that reduced one range-six
certification from roughly three minutes to about five seconds while matching
the legacy elimination on every range-five cross-check.

But the central scientific tension remains: finite-range absence is not a
nonintegrability theorem. Longer quasi-local tails, nonlocal dualities,
nonstandard fermionizations, or interacting conserved structures can still
evade this search.

## Questions for contributors

- Which range-seven or range-eight basis gives the best information gain per
  sparse-rank cost?
- Can a rigorous tail bound turn a finite six-shell null result into a useful
  quasi-local exclusion statement?
- Which nonlocal dualities or fermionization maps should be tested before using
  level statistics as evidence?
- Can the exact sparse-rank certificate be independently reproduced in Sage,
  Julia, Rust, or another algebra system?
- What adversarial integrable model would most likely fool the current finite
  local-charge protocol?

## Contribution-sized entry points

- Extend the complete range-six calculation to a second size and a second
  preregistered coupling.
- Implement range-seven translation-summed charges with an explicit tail model.
- Add nonlocal-duality and nonstandard-fermionization probes.
- Reproduce the modular ranks with an independent sparse linear-algebra stack.
- Build larger sparse-spectrum diagnostics without promoting spectral behavior
  into a theorem.

## Claim boundary

R194 does not establish nonintegrability, quantum chaos, spectral hardness, an
all-size or all-coupling theorem, complete quasi-local exclusion, Quantum PCP,
NLTS, BQP separation, or a solved frontier. Scientific promotion remains false
and new credit remains zero. The next task is T-B9-009.

Artifacts: [result](https://github.com/crystal-tensor/Prometheus-plan/blob/main/results/B9_R194_higher_range_charge_stress_v1.json), [report](https://github.com/crystal-tensor/Prometheus-plan/blob/main/research/B9_R194_higher_range_charge_stress.md), [method](https://github.com/crystal-tensor/Prometheus-plan/blob/main/tools/b9_r194_higher_range_charge_stress.py), and [research dashboard](https://htmlpreview.github.io/?https://github.com/crystal-tensor/Prometheus-plan/blob/main/research/axiom_horizon_landing.html).
