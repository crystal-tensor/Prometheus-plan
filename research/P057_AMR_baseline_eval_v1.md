# Problem `#057` AMR Frozen-Baseline Evaluation v1

Date: 2026-07-30

Status: **the two preregistered denominators are now scored on the frozen
2023 holdout; no candidate model is evaluated.**

This packet remains strictly inside catalog problem `#057`. It does not
estimate resistance for non-reporting entities, recommend antibiotics, issue
a clinical or public-health action, or claim the frontier problem is solved.

## Machine-check summary

- Contract checks: `22/22` passed.
- Evaluated rows: `141` on the 2023 holdout.
- Protocol commit: `cafabf703649eb5300dba18d5b22262326b81442`.
- Candidate model executed: `false`.

## Does a trend beat yesterday's value?

| Slice | n | LOCF MAE | Country-logit MAE | Winner | Paired difference (trend − LOCF) | 95% bootstrap interval |
|---|---:|---:|---:|---|---:|---:|
| Pooled overall | 141 | 6.30 pp | 8.53 pp | `locf` | +2.22 pp | [+1.26, +3.30] pp |
| Pooled partial | 50 | 9.50 pp | 12.72 pp | `locf` | +3.22 pp | [+1.40, +5.29] pp |
| Pooled dense | 91 | 4.55 pp | 6.22 pp | `locf` | +1.67 pp | [+0.62, +2.85] pp |
| E. coli overall | 72 | 4.35 pp | 6.72 pp | `locf` | +2.37 pp | [+1.17, +3.84] pp |
| E. coli partial | 26 | 5.93 pp | 10.80 pp | `locf` | +4.87 pp | [+2.18, +8.33] pp |
| E. coli dense | 46 | 3.46 pp | 4.42 pp | `locf` | +0.96 pp | [+0.06, +1.83] pp |
| MRSA overall | 69 | 8.34 pp | 10.41 pp | `locf` | +2.07 pp | [+0.61, +3.70] pp |
| MRSA partial | 24 | 13.37 pp | 14.80 pp | `locf` | +1.43 pp | [-0.65, +3.64] pp |
| MRSA dense | 45 | 5.67 pp | 8.07 pp | `locf` | +2.40 pp | [+0.54, +4.62] pp |

A positive paired difference means the country-logit trend has larger
absolute error. The bootstrap interval is descriptive and does not alter any
gate. Equal entity weights are used because the frozen public rates do not
carry a comparable observation denominator for every entity-year.

### Indicator-level reading

- **E. coli overall (`n=72`):** LOCF MAE `4.35` pp; country-logit MAE `6.72` pp; LOCF is the harder denominator.
- **E. coli partial (`n=26`):** LOCF MAE `5.93` pp; country-logit MAE `10.80` pp; LOCF is the harder denominator.
- **MRSA overall (`n=69`):** LOCF MAE `8.34` pp; country-logit MAE `10.41` pp; LOCF is the harder denominator.
- **MRSA partial (`n=24`):** LOCF MAE `13.37` pp; country-logit MAE `14.80` pp; LOCF is the harder denominator.

The `partial` slice is the lowest-completeness stratum that can satisfy the
predeclared requirement of an observed 2023 holdout plus at least three
observed training years. Calling it `sparse` would silently change the frozen
stratification after eligibility was known.

## Calibration boundary

| Indicator / slice | LOCF signed bias | Country-logit signed bias | LOCF absolute bias | Country-logit absolute bias |
|---|---:|---:|---:|---:|
| E. coli overall | +0.15 pp | +0.04 pp | 0.15 pp | 0.04 pp |
| E. coli partial | +1.72 pp | -0.02 pp | 1.72 pp | 0.02 pp |
| MRSA overall | +0.26 pp | +2.30 pp | 0.26 pp | 2.30 pp |
| MRSA partial | +5.06 pp | +5.90 pp | 5.06 pp | 5.90 pp |

Calibration-in-the-large is reported because a low absolute error can coexist
with systematic over- or under-prediction. A future candidate must beat both
baselines on absolute error in each indicator overall and in `partial`, while
its absolute bias stays within the frozen two-percentage-point guardrail.

## Leakage and missingness audit

- Every trend and LOCF prediction uses observations from 2016–2022 only.
- The held-out 2023 value is used only as the final target; eligibility uses
  its presence, never its magnitude.
- All 141 preregistered eligible rows are retained: 72 E. coli and 69 MRSA.
- The comparison remains conditional on 2023 reporters. The earlier Manski
  bounds still govern any claim about all 245 frozen entities.

## Official evidence

- WHO AMR dashboard: [Antimicrobial Resistance profile]
(https://data.who.int/dashboards/amr/antimicrobial-resistance-profile).
- WHO E. coli indicator: [third-generation cephalosporin resistance]
(https://data.who.int/indicators/i/918081E/745F475).
- WHO MRSA indicator: [methicillin resistance]
(https://data.who.int/indicators/i/918081E/5DD9606).

## Next falsifier

Admit one explicitly specified candidate only after its features, fitting
window, hyperparameters, and missingness handling are committed. Score it on
these exact 141 rows; it must beat both frozen denominators for each indicator
overall and in `partial`, without changing the cohort or calibration guardrail.

## Claim boundary

This is a denominator study on country/entity-level surveillance percentages.
It is not a clinical forecast, resistance estimate for missing countries,
causal analysis, treatment recommendation, pathogen-design result, or solution
to catalog problem `#057`.

