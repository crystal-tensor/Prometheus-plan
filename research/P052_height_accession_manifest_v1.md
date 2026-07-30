# P052 height accession and ancestry-leakage manifest v1

**Decision:** `blocked_no_individual_level_external_holdout`.

## What the gate asked

Do three ancestry-labelled public height files already form an external genotype-to-phenotype test? The answer is no. This gate separates a reusable summary-statistics manifest from the participant-level evidence required to calculate calibration and incremental explained variance.

The exact current `body height` query returned `200` studies; `106` report full summary statistics. Three 2026 accessions were frozen as a cross-cohort design seed.

## Frozen three-accession seed

| Accession | Intended role | Cohort | Catalog ancestry | N | SNPs | Response | Published covariates | License |
|---|---|---|---|---:|---:|---|---|---|
| [GCST90728584](https://www.ebi.ac.uk/gwas/studies/GCST90728584) | training_summary_statistics | UKB | European | 451,921 | 11,164,270 | Standing height (inverse-normalization-transformed) | age, age2, sex, genotyping array, 10 genetic PCs | CC0 |
| [GCST90727382](https://www.ebi.ac.uk/gwas/studies/GCST90727382) | transfer_summary_statistics_sentinel | CKB | East Asian | 72,471 | 21,000,000 | Standing height | array_type, regional PC1-4, age, age^2 | CC0 |
| [GCST90727327](https://www.ebi.ac.uk/gwas/studies/GCST90727327) | transfer_summary_statistics_sentinel | G&H | South Asian | 33,182 | 1,232,514 | Height.residual | not listed | EMBL-EBI terms |

Together the manifest covers `557,574` discovery participants, `3` named cohorts, and `3` Catalog ancestry categories. Every accession has an accessible raw file, harmonised GRCh38 GWAS-SSF file, declared checksum, cohort, ancestry metadata, and license path.

## Why the evaluation is still blocked

The retained artifacts are aggregate association estimates. They do not provide participant- or family-level keys, held-out genotypes or frozen scores, measured outcomes, per-participant ancestry assignment, covariate values, or resampling clusters. Therefore they cannot produce the preregistered external-cohort calibration slope, incremental explained variance, or ancestry-stratified bootstrap interval.

The phenotype scale is also not interchangeable: the three accessions describe inverse-normalized standing height, standing height, and a height residual. UKB and CKB were published in the same paper, so their cross-population comparison is a retrospective sentinel rather than an unopened confirmation. The G&H accession comes from a second publication but is exome-wide and remains aggregate-only.

## Leakage contract

- Distinct accession IDs and ancestry labels do not prove participant- or cohort-level independence.
- No held-out association, paper result, or phenotype transformation may guide feature selection, allele alignment, weighting, calibration, or hyperparameters.
- Participant, family, household, and cohort boundaries must all remain intact.
- Catalog ancestry descriptors are not treated as discrete causal biological categories.
- Raw, residualized, and inverse-normalized outcomes require a frozen scale-alignment rule.

## Reproducibility and next falsifier

The formal packet passes `20/20` checks. Multi-gigabyte association files are not duplicated in the repository; their official URLs, HTTP metadata, GWAS Catalog metadata, declared MD5 checksums, directory listings, and small-source SHA-256 hashes are retained.

The next gate is an approved, cohort-disjoint individual-level holdout that supplies all seven frozen fields. Only then may variant intersection, allele alignment, LD reference, response transformation, additive denominator, bootstrap clusters, and calibration code be frozen before outcomes are opened.

## Official sources

- [GWAS Catalog summary-statistics documentation](https://www.ebi.ac.uk/gwas/docs/methods/summary-statistics)
- [GWAS Catalog population descriptors](https://www.ebi.ac.uk/gwas/docs/population-descriptors)
- [GWAS Catalog REST API v2](https://www.ebi.ac.uk/gwas/rest/api/v2/docs)

No individual height prediction, re-identification, reproductive selection, clinical decision, causal mapping, wet-lab, or solved-frontier claim is made.
