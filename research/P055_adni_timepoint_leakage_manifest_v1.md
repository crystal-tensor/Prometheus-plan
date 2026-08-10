# P055 ADNI variable/timepoint manifest and leakage sentinel v1

**Decision:** `adni_timepoint_leakage_manifest_ready_execution_blocked_by_ida_access_and_family_group`.

## The prospective question is now concrete

The frozen candidate is deliberately narrow: use the baseline plasma `pT217_AB42_F` ratio to predict future `TOTAL13` change near month 24, only after age, sex, APOE genotype, baseline diagnosis, and baseline `TOTAL13` have entered the denominator. The outcome window is months 18-30, and the index date is the latest actual date among retained baseline inputs.

| Role | Table or source | Field | Time rule | Public anchor |
|---|---|---|---|---|
| participant group | `cross-table structural field` | `RID` | all time points / grouping only | yes |
| primary site holdout | `PTID enrollment-site prefix` | `PTID` | initial enrollment site / grouping only | yes |
| procedure-site sensitivity | `cross-table structural field` | `SITEID` | procedure-specific / phase-aware | yes |
| schedule label | `cross-table structural field` | `VISCODE2` | schedule alignment only | yes |
| actual observation date | `table-specific structural field` | `EXAMDATE | VISDATE | COLDATE` | index cutoff and horizon | yes |
| mechanism signature | `UPENN_PLASMA_FUJIREBIO_QUANTERIX` | `pT217_AB42_F` | baseline feature only | yes |
| age | `ADNIMERGE` | `AGE` | baseline_covariate_only | yes |
| sex | `PTDEMOG` | `PTGENDER` | baseline_covariate_and_stratum | yes |
| APOE genotype | `APOERES` | `GENOTYPE` | baseline_covariate_only | yes |
| baseline diagnosis | `DXSUM` | `DIAGNOSIS` | baseline_covariate_only | yes |
| baseline cognition | `ADAS` | `TOTAL13` | baseline_covariate_and_change_anchor | yes |
| future outcome | `ADAS` | `TOTAL13` | 18-30 months after index; target month 24 | yes |
| family group | `unresolved public dictionary state` | `FAMILYID or lawful relatedness cluster` | grouping only | no — unresolved |

The public manifest contains `13` rows. `12` have a public dictionary or documentation anchor; the family grouping row remains unresolved. That missing row blocks execution rather than being silently treated as unrelated participants.

## What the public dictionary establishes

The pTau217 search exposes `18` ordered rows for `UPENN_PLASMA_FUJIREBIO_QUANTERIX`, including participant/visit/date fields and the frozen `pT217_AB42_F` assay field across ADNI1, GO, 2, 3, and 4. `TOTAL13` has `3` exact phase-specific dictionary rows spanning the same five phases.

This is schema evidence, not an eligible cohort. Actual rows, dates, assay completeness, site counts, and participant overlap live behind approved IDA access. The public `FAMILYID` search returns zero exact rows; that is an unresolved dictionary state, not evidence that ADNI participants are unrelated.

## A visit label is not a timestamp

ADNI documents that VISCODE meanings vary by phase, different actual dates can share a VISCODE, and VISCODE-only reconciliation can produce erroneous merges. `VISCODE2` is retained as a schedule label, while `EXAMDATE`, `VISDATE`, or `COLDATE` controls the feature cutoff and outcome horizon. `USERDATE`, `USERDATE2`, `update_stamp`, `ID`, and `record_ID` remain administrative fields and are never model features.

The primary site split uses the stable enrollment-site prefix in `PTID`; procedure-level `SITEID` is a sensitivity analysis because ADNI1 site codes differ from later phases. All preprocessing must be fit inside training sites.

## Nine fail-closed leakage sentinels

| ID | Rule |
|---|---|
| `L01` | Reject every candidate feature whose actual EXAMDATE, VISDATE, or COLDATE is later than index_date. |
| `L02` | Treat every TOTAL13 after index_date as outcome-only; never use longitudinal ADAS values as predictors. |
| `L03` | Treat post-index DIAGNOSIS, DXCHANGE, DXCURREN, BLCHANGE, CDRSB, MMSE, and FAQ as forbidden predictors. |
| `L04` | Do not use USERDATE, USERDATE2, update_stamp, ID, or record_ID as biological, temporal, or participant features. |
| `L05` | Never join longitudinal tables on VISCODE alone; require RID plus phase-aware time reconciliation and an actual date. |
| `L06` | Do not treat a missing scheduled assessment as random; preserve table- and phase-specific -1, -4, -5, NA, empty, and zero encodings until adjudicated. |
| `L07` | Do not fit imputation, scaling, biomarker thresholds, or feature selection before the acquisition-site split. |
| `L08` | Do not let a rollover participant, duplicate RID, family cluster, or enrollment site occur in both training and holdout partitions. |
| `L09` | Do not use CDR to independently grade a diagnostic outcome without modeling their documented criterion dependence. |

## Why the model remains unopened

ADNI row-level data require an approved IDA account and Data Use Agreement. Without those rows, this packet cannot count eligible participants, adjudicate table-specific missingness, construct the family grouping, open site holdouts, or estimate prediction error. The public schema is ready; the experiment is not.

The formal packet passes `28/28` checks and hash-binds `15` normalized official HTML snapshots. Raw transfer hashes are recorded in the capture manifest; embedded media and application scripts are intentionally not retained.

## Next falsifier

After lawful IDA access, reconstruct this exact 13-row manifest before opening outcomes: resolve a family/relatedness cluster, enumerate complete baseline and month-24 rows by enrollment site and sex, preserve missingness reasons, freeze the site split, and fail if any post-index byte enters a feature matrix. Only then may the denominator and denominator-plus-signature models be compared.

## Official sources

- [ADNI data access](https://adni.loni.usc.edu/data-samples/adni-data/)
- [ADNI documentation — study design](https://adni.loni.usc.edu/quick-start-guide-asset101625/about.html)
- [ADNI documentation — table anatomy and time identifiers](https://adni.loni.usc.edu/quick-start-guide-asset101625/anatomy2.html)
- [ADNI documentation — diagnosis](https://adni.loni.usc.edu/quick-start-guide-asset101625/diagnostic.html)
- [ADNI documentation — clinical assessments](https://adni.loni.usc.edu/quick-start-guide-asset101625/clinical.html)
- [ADNI documentation — major biomarker tables](https://adni.loni.usc.edu/quick-start-guide-asset101625/domain.html)
- [ADNI data dictionary search](https://adni.loni.usc.edu/data-samples/data-dictionary-search/)

No participant data, model training, biomarker threshold, diagnosis, root-cause, treatment-effect, clinical-utility, regulatory, or solved-frontier claim is made.
