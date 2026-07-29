# Problems `#049`–`#050` Executable Preflight v1

Date: 2026-07-29

Status: **the executable packet is valid; the `#049` numerical candidate passes,
while the `#050` toy-model candidate is rejected by its frozen yield margin.**

This update remains strictly inside catalog problems `#049` and `#050`. It upgrades
two activation gates from prose to replayable numerical tests. It does not claim a
chemical prediction, molecular assembly fidelity, quantum advantage, or a solved frontier.

## Machine-check summary

- Contract checks: `13/13` passed.
- `#049` decision: `candidate_pass` on `3` unopened momenta.
- `#050` decision: `candidate_fail` under equal design-call budgets.
- Benchmark SHA-256: `6fbad4c35d87cfc9fdb79e28a4850ae297916bc2d541c9da4f42f455b5d9f8e8`.
- Tool SHA-256: `1500bbcffb6e239cf149d2712524835b2173850dfb72d653a925f666af52a02c`.

## `#049` — Does an independent propagator survive unopened energies?

The frozen model is a one-dimensional Gaussian barrier in dimensionless atomic units.
The denominator is a Strang split-operator FFT propagation on 4,096 points; grid
convergence is checked independently on 8,192 points at half the time step. The
candidate uses a fourth-order real-space Crank–Nicolson Hamiltonian on the same
working grid. A second-order spatial discretization is retained as a negative control.

| Split | Momentum | Energy | Denominator T | Candidate error | Grid error | CN2 control error |
|---|---:|---:|---:|---:|---:|---:|
| pilot | 1.1 | 0.605 | 0.061597969 | 1.146e-07 | 1.700e-07 | 2.822e-04 |
| holdout | 1.3 | 0.845 | 0.301790497 | 1.297e-06 | 3.350e-07 | 1.213e-03 |
| holdout | 1.5 | 1.125 | 0.711838383 | 2.407e-06 | 1.063e-07 | 1.500e-03 |
| holdout | 1.7 | 1.445 | 0.945773981 | 1.209e-06 | 6.511e-08 | 5.598e-04 |

All three holdouts pass the `1e-3` probability threshold; the largest candidate error is `2.407e-06` and the largest denominator grid error is `3.350e-07`.
The deliberately weaker second-order control fails `2/3` holdouts, so this gate is not accepting every plausible-looking propagation.

### Cost proxy

- Denominator: `9000` steps, one FFT and one inverse FFT per step.
- Candidate: `4500` steps, one pentadiagonal matrix-vector product and one prefactored LU solve per step.

## `#050` — Does lower off-target rate earn the frozen yield claim?

Eight paired search seeds each receive exactly 256 design calls. The candidate,
target-only baseline, and random-search baseline see two public conditions. None
can see the three acceptance defects while searching. The hidden topology is an
eight-node branched path.

| Method | Total calls | Median hidden yield | Median hidden off-target rate |
|---|---:|---:|---:|
| `budget_matched_random_search` | 2048 | 0.424070 | 0.209378 |
| `target_only_local_search` | 2048 | 0.479463 | 0.240941 |
| `off_target_aware_local_search` | 2048 | 0.494393 | 0.203902 |

The off-target-aware candidate lowers the median hidden off-target rate relative to both baselines, so the safety-style guardrail passes. But its yield gains are only `7.03` percentage points over random search and `1.49` points over target-only search.
Both must reach the preregistered `10.00`-point margin. The candidate is therefore rejected rather than rescued by a favorable secondary metric.

## Evidence and method boundary

- Split-operator lineage: [Feit, Fleck, and Steiger (1982)](https://doi.org/10.1016/0021-9991(82)90091-2).
- Reaction-record context: [QCArchive record and computation types](https://docs.qcarchive.molssi.org/user_guide/records/index.html).
- Off-target assembly evidence: [Moradzadeh et al. (2026)](https://www.nature.com/articles/s41467-026-73387-4).

The `#049` Gaussian barrier is a numerical calibration object, not coupled
electron–nuclear molecular dynamics. The `#050` independent-bond model omits
geometry, cooperative kinetics, strand displacement, and molecular sequence
physics. Its value is to exercise the denominator and rejection logic before a
higher-fidelity simulator is admitted.

## Next falsifiers

1. Replace the `#049` Gaussian barrier with a source-backed reactive potential and
   a state-resolved observable while keeping the unopened-energy split unchanged.
2. Replace the `#050` independent-bond model with mesoscopic cooperative kinetics;
   retain the same equal-budget baselines and ten-point hidden-yield margin.
3. Proceed next to the public-data manifests for `#057` AMR and `#058`
   vintage-aware wastewater alerts without widening beyond `#049`–`#060`.

## Claim boundary

Passing the executable packet means the calculations, hashes, decisions, and
negative controls replay consistently. It does not mean problem `#049` or `#050`
is solved, and it creates no chemical, biological, environmental, or clinical claim.
