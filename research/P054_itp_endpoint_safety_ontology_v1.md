# P054 ITP endpoint and safety ontology v1

**Decision:** `endpoint_safety_ontology_ready_public_gate_not_executable`.

## What the public portal can actually support

The current ITP1 portal exposes `74` compound-cohort rows covering `62` named compounds and `17` cohorts. Every row links a lifespan analysis, but only `22` rows link any other phenotype.

| Public linkage layer | Rows | Share of 74 |
|---|---:|---:|
| Survival analysis | 74 | 100.0% |
| Any other phenotype | 22 | 29.7% |
| Physical function | 2 | 2.7% |
| Pathology | 1 | 1.4% |
| Per-row pilot-toxicity link | 0 | 0.0% |
| Survival + function + pathology | 1 | 1.4% |
| Full linked gate | 0 | 0.0% |

This is a coverage audit, not a claim that ITP failed to measure the missing layers. The JAX protocol explicitly says MPD houses a subset of ITP studies and will add more data. A blank portal cell therefore means `not linked in this snapshot`, never `no harm`.

## Frozen endpoint ontology

| Evidence class | Current public anchor | Minimum executable fields |
|---|---|---|
| `survival_and_censoring` | One survival-analysis link for every portal compound-cohort row plus the JAX lifespan protocol. | compound, dose, cohort, site, sex, treatment_start_age, event_or_censor_age, event_status, removal_reason |
| `physical_function` | Portal links labeled grip strength, grip duration, and rotarod. | assay, unit, measurement_age, compound, cohort, site, sex, denominator, missingness_reason |
| `physiology_and_body_composition` | Portal links labeled body weight, body composition, fat pads, postprandial glucose, and uterus weight. | measure, unit, measurement_age, compound, cohort, site, sex, denominator |
| `pathology_and_tumor` | One portal pathology link, for acarbose C2013, with sex-specific organ/condition odds ratios. | organ_or_condition, lesion_or_tumor_class, severity, necropsy_denominator, compound, cohort, site, sex, effect_estimate, multiplicity_rule |
| `exposure_and_pilot_toxicity` | NIA describes chow stability, plasma levels, eight-week toxicity, and occasional pharmacodynamic pilot testing; the portal table exposes no per-row pilot-toxicity link. | compound, dose, exposure_or_chow_stability, pilot_duration, adverse_sign, severity, count, denominator, sex, site, stopping_rule |
| `humane_removal_and_technical_loss` | The JAX protocol lists moribund signs and four non-natural-death removal categories. | mouse_identifier, date_or_age, site, sex, clinical_signs, removal_reason, event_status, analysis_handling |
| `biochemical_mechanism` | NIA and JAX describe biochemical mechanism as an expanded Stage II endpoint class, not as a universal portal result. | frozen_mechanism_hypothesis, assay, tissue, collection_age, compound, cohort, site, sex, denominator, multiplicity_rule |

## Why lifespan cannot grade its own safety

NIA describes a staged program: pilot chow stability, exposure and eight-week toxicity; Stage I lifespan; and Stage II health, pathology, biochemical mechanism and additional lifespan work. Those layers are complementary, not interchangeable.

Acarbose C2013 is the only portal row linking survival, physical function and pathology. Its pathology page contains eight sex-condition rows. The displayed male `Lung tumor` row reports an odds ratio of `2.851` and `p=0.0334`. This is retained as a safety sentinel, not interpreted as causal toxicity: the page-level display does not by itself resolve necropsy denominators, multiplicity, or analysis-plan context.

## Humane endpoints are analysis fields

The JAX protocol lists five moribund clinical signs and four non-natural-death removal categories. Fighting, humane removal, physiological/behavioral removal, and technical loss must remain distinct event states. Collapsing them into natural death—or deleting them—can change a survival estimand and erase safety information.

## Reproducibility and next falsifier

The formal packet passes `28/28` checks and hash-retains five official HTML snapshots. Supplementary workbook links are inventoried but their cell contents are not parsed or used in this result.

The next falsifier is a row-level public manifest joining each compound, cohort, site and sex to survival status, function, pathology/tumor, pilot toxicity/exposure, denominators, missingness reasons and multiplicity rules. Until then, the frozen survival-plus-function-plus-safety gate is not executable across the portal.

## Official sources

- [NIA — About the ITP](https://www.nia.nih.gov/research/dab/interventions-testing-program-itp/about-itp)
- [NIA — ITP application instructions](https://www.nia.nih.gov/research/dab/interventions-testing-program-itp/application-instructions)
- [JAX Mouse Phenome Database — ITP portal](https://phenome.jax.org/centers/ITP)
- [JAX — ITP1 project protocol](https://phenome.jax.org/projects/ITP1/protocol)
- [JAX — Acarbose C2013 pathology](https://phenome.jax.org/itp/othpheno/ACA/pathology/C2013)

No animal experiment, individual-mouse analysis, compound ranking, efficacy recommendation, causal toxicity conclusion, human anti-aging advice, dosing, treatment, rejuvenation, reversal, regulatory, or solved-frontier claim is made.
