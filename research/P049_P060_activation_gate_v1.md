# Problems #049–#060 Activation Gate v1

Date: 2026-07-29

Status: **activation packet validated; no frontier problem is claimed solved.**

This packet reopens only catalog problems **#049 through #060**. It does not revise the frozen
100-problem catalog, execute a human/animal intervention, or touch any other research lane.
Its contribution is narrower and auditable: each problem now has one heuristic question, one
first falsifiable gate, an explicit denominator, a holdout rule, and a safety boundary.

## Machine-check summary

- Scope: `12/12` exact catalog IDs.
- Contract checks: `13/13` passed.
- Ready for public replay: `4`.
- Ready after data/access work: `5`.
- Protocol-only high-stakes lanes: `3`.
- Packet SHA-256: `811e3f5a8f5d93e734969bda513411257dc4366f75cbf897ee95d2a65c65eb9a`.

## Activation matrix

| ID | Heuristic question | First denominator | Acceptance boundary | Readiness |
|---:|---|---|---|---|
| #049 | Can a reaction-dynamics solver predict an observable it was not tuned on before it asks for scale credit? | Grid-converged split-operator propagation on the identical potential, grid, time window, and observable extraction code. | All three unopened energies must have probability error <= 1e-3, norm-accounting error <= 1e-8, and a documented cost comparison against the same-access denominator. | `ready_for_public_replay` |
| #050 | If off-target interactions are part of the physics, can inverse design still win on structures it never saw? | Budget-matched random search and a target-only inverse-design baseline that does not model off-target interactions. | The preregistered design must improve median hidden-condition yield by at least 10 percentage points over both denominators without increasing the off-target structure rate. | `ready_for_public_replay` |
| #051 | Can an ensemble prediction explain held-out dynamics that a beautiful single structure cannot? | Best available single-structure prediction plus a short conventional molecular-dynamics ensemble under the same experimental restraints. | The candidate ensemble must reduce median held-out normalized error by at least 20% versus both denominators and retain the gain under leave-one-protein-out replay. | `ready_after_access` |
| #052 | Does a genotype-to-phenotype model survive a change of ancestry, environment, and measurement protocol? | An additive polygenic-score model using the same variants, summary statistics, covariates, and training cohorts. | Every held-out ancestry group must have calibration slope in [0.9, 1.1] and positive incremental explained variance with a bootstrap interval excluding zero. | `ready_after_access` |
| #053 | What evidence would distinguish an early-cancer signal from an expensive cascade of false positives? | Standard-of-care screening in a randomized control arm, not a retrospective case-control sample. | No promotable detection claim until a prospective randomized study meets its preregistered predictive-value and diagnostic-burden thresholds; no cure claim without treatment-specific randomized outcomes. | `protocol_only_high_stakes` |
| #054 | If lifespan moves, what would prove that function improved without merely changing how disease was counted? | Concurrent vehicle control under the same husbandry and a three-site protocol modeled on the NIA ITP. | A candidate advances only if survival and at least one late-life functional endpoint improve, direction is not reversed at any site, and tumor/pathology safety guardrails do not worsen. | `protocol_only_high_stakes` |
| #055 | Can a proposed mechanism predict who changes next, not merely describe who is already ill? | Age, sex, APOE status, baseline diagnosis, and baseline cognition without the proposed mechanism-derived features. | The mechanism signature must improve held-out prediction error with a bootstrap interval excluding zero and remain calibrated across site and sex strata. | `ready_after_access` |
| #056 | Can an immune controller hit its target state without borrowing success from cytokine toxicity? | No-treatment or standard-treatment arm plus a linear dose-response model using the same donor information. | Target-state error must improve versus both denominators while every prespecified guardrail is non-inferior on donor-held-out data. | `ready_after_access` |
| #057 | Can an AMR forecast beat yesterday's resistance rate where surveillance is thinnest? | Last-observation-carried-forward and a country-specific logistic time trend using the same GLASS rows. | The candidate must beat both denominators overall and in the lowest-completeness prespecified stratum without excluding countries after outcomes are seen. | `ready_for_public_replay` |
| #058 | How early is an early warning after false alarms and reporting delays are charged to the score? | Seasonal historical average, last-value trend, and clinical-data-only alerting at the same false-alert budget. | Wastewater-plus-clinical alerting must gain at least seven median days over every denominator while staying within the frozen false-alert budget on unseen jurisdictions and weeks. | `ready_for_public_replay` |
| #059 | Can a connectome predict cognition after family structure, head motion, and scanner artifacts are denied an escape route? | Demographics, motion, scanner/acquisition variables, and regional anatomy without functional-connectivity edges. | Connectivity must add reproducible held-out value with a bootstrap interval excluding zero and no material degradation after motion-matched replay. | `ready_after_access` |
| #060 | What would make an editing result fail even when its on-target number looks excellent? | Unedited cells, mock delivery, and the current standard editor/delivery system assessed with identical assays and sequencing depth. | No safety or scalability claim is promotable unless every assay-specific threshold is preregistered, met across independent lots, and non-inferior to the standard editor at matched sequencing sensitivity. | `protocol_only_high_stakes` |

## Problem-by-problem research entry points

### #049 — Exact Molecular Reaction Dynamics

**Question.** Can a reaction-dynamics solver predict an observable it was not tuned on before it asks for scale credit?

**Current evidence boundary.** QCArchive now standardizes large quantum-chemistry campaigns and includes reaction energies and nudged-elastic-band profiles, but stored electronic-structure records are not by themselves exact coupled electron-nuclear dynamics.

**First gate.** Freeze one low-dimensional reactive scattering model, three incident energies, the potential representation, grid, absorbing boundary, and observable definitions before any candidate output is opened.

**Denominator.** Grid-converged split-operator propagation on the identical potential, grid, time window, and observable extraction code.

**Primary metric.** Maximum absolute error across preregistered state-to-state reaction probabilities, accompanied by norm-loss and grid-convergence diagnostics.

**Acceptance rule.** All three unopened energies must have probability error <= 1e-3, norm-accounting error <= 1e-8, and a documented cost comparison against the same-access denominator.

**Falsifier.** Any unopened energy violates the probability or norm threshold, or the result depends on a changed grid, potential, time window, or observable extractor.

**Split.** One disclosed pilot energy for debugging; three unopened energies for acceptance.

**Safety boundary.** Computational chemistry only; no wet-lab reaction recommendation or materials-safety claim.

**Next artifact.** P049 frozen model specification plus an independently replayable split-operator denominator transcript.

**Source.** [Molecular Sciences Software Institute — QCArchive record and computation types](https://docs.qcarchive.molssi.org/user_guide/records/index.html). Current documentation includes reaction-energy and NEB reaction-profile records. Access: public.

### #050 — Programmable Self-Assembling Matter

**Question.** If off-target interactions are part of the physics, can inverse design still win on structures it never saw?

**Current evidence boundary.** A 2026 DNA-origami study reports that scaffold sequences with fewer predicted off-target interactions fold more reliably across several 2D and 3D targets, making unseen-defect robustness a concrete denominator rather than a qualitative aspiration.

**First gate.** Freeze a library of target structures, an assembly simulator, a design-call budget, and a hidden panel of off-target binding and component-dropout conditions.

**Denominator.** Budget-matched random search and a target-only inverse-design baseline that does not model off-target interactions.

**Primary metric.** Assembly yield on hidden defect conditions, with off-target structure rate reported separately.

**Acceptance rule.** The preregistered design must improve median hidden-condition yield by at least 10 percentage points over both denominators without increasing the off-target structure rate.

**Falsifier.** The gain disappears on hidden defect conditions, requires more design calls, or trades yield for an increased off-target rate.

**Split.** Disclosed target topologies for development; held-out target topology and defect panel for acceptance.

**Safety boundary.** In-silico assembly only; no biological delivery, environmental release, or autonomous active-matter experiment.

**Next artifact.** P050 simulator contract with seeded target/defect splits and budget-matched baseline implementations.

**Source.** [Nature Communications — Optimising DNA origami assembly by reducing off-target interactions](https://www.nature.com/articles/s41467-026-73387-4). Published 2026-05-26; experimentally links predicted off-target reactions to folding yield. Access: public.

### #051 — Protein Dynamics and Function Prediction

**Question.** Can an ensemble prediction explain held-out dynamics that a beautiful single structure cannot?

**Current evidence boundary.** AlphaFold DB expanded high-confidence complex predictions in 2026, while its own FAQ states that a prediction is not a Boltzmann sample and that known multiple conformations usually collapse to one output.

**First gate.** Select proteins with paired structural models and experimental dynamic observables; freeze observable preprocessing and exclude the acceptance observables from ensemble fitting.

**Denominator.** Best available single-structure prediction plus a short conventional molecular-dynamics ensemble under the same experimental restraints.

**Primary metric.** Normalized error on held-out NMR or conformational-population observables, stratified by protein and observable type.

**Acceptance rule.** The candidate ensemble must reduce median held-out normalized error by at least 20% versus both denominators and retain the gain under leave-one-protein-out replay.

**Falsifier.** The gain is confined to fitted restraints, vanishes under leave-one-protein-out replay, or is explained by a larger sampling budget.

**Split.** Restraint-level holdout within proteins plus a protein-level holdout.

**Safety boundary.** Public structural and biophysical data only; no clinical interpretation or protein-engineering safety claim.

**Next artifact.** P051 small benchmark roster with explicit experimental observables, licensing, and single-structure/MD denominators.

**Source.** [EMBL-EBI and Google DeepMind — AlphaFold Protein Structure Database FAQ](https://www.alphafold.ebi.ac.uk/faq). May 2026 database release added large complex-prediction sets while retaining explicit ensemble limitations. Access: public.

### #052 — Genotype-to-Phenotype Mapping

**Question.** Does a genotype-to-phenotype model survive a change of ancestry, environment, and measurement protocol?

**Current evidence boundary.** The NHGRI-EBI GWAS Catalog exposes harmonized summary statistics, ancestry metadata, and, from April 2026, standards for CNV and gene-based results; association resources still do not turn correlation into a general causal map.

**First gate.** Freeze one quantitative trait, harmonized studies from at least two ancestry groups, covariates, and a cohort-level external holdout before model selection.

**Denominator.** An additive polygenic-score model using the same variants, summary statistics, covariates, and training cohorts.

**Primary metric.** External-cohort calibration slope and incremental explained variance over the additive denominator, reported by ancestry group.

**Acceptance rule.** Every held-out ancestry group must have calibration slope in [0.9, 1.1] and positive incremental explained variance with a bootstrap interval excluding zero.

**Falsifier.** Any ancestry group fails calibration, the incremental interval includes zero, or hidden cohort information enters harmonization or feature selection.

**Split.** Study-level and ancestry-level holdout; no random row split across related samples or cohorts.

**Safety boundary.** Summary statistics only; no re-identification, individual prediction, reproductive selection, or clinical decision use.

**Next artifact.** P052 trait-specific accession manifest and ancestry-aware leakage audit.

**Source.** [NHGRI-EBI — GWAS Catalog summary statistics documentation](https://www.ebi.ac.uk/gwas/docs/methods/summary-statistics). April 2026 standards extend beyond SNP-only submissions and preserve ancestry/sample metadata. Access: public.

### #053 — General Early Cancer Detection and Personalized Cure

**Question.** What evidence would distinguish an early-cancer signal from an expensive cascade of false positives?

**Current evidence boundary.** NCI's active Vanguard Study randomizes up to 24,000 cancer-free adults among two multi-cancer detection tests and a control arm to establish feasibility before a definitive mortality trial.

**First gate.** Adopt a prospective population-screening protocol that freezes eligibility, assay threshold, diagnostic-resolution pathway, cancer ascertainment, and follow-up before outcomes are opened.

**Denominator.** Standard-of-care screening in a randomized control arm, not a retrospective case-control sample.

**Primary metric.** Cancer-specific positive predictive value and diagnostic-resolution burden, with stage distribution and false-negative cancers reported.

**Acceptance rule.** No promotable detection claim until a prospective randomized study meets its preregistered predictive-value and diagnostic-burden thresholds; no cure claim without treatment-specific randomized outcomes.

**Falsifier.** Performance falls below the preregistered prospective thresholds, downstream diagnostic harm is excessive, or retrospective tuning enters the evaluation set.

**Split.** Prospective randomized arms and locked analysis plan; retrospective samples may be pilot-only.

**Safety boundary.** No medical advice, assay recommendation, patient recruitment, treatment selection, or cure claim.

**Next artifact.** P053 endpoint dictionary that separates detection feasibility, mortality benefit, and personalized-treatment evidence.

**Source.** [US National Cancer Institute — The Vanguard Study on Multi-Cancer Detection Tests](https://www.cancer.gov/research/areas/screening/vanguard-study). Active prospective feasibility study; posted 2025-09-10. Access: public protocol information.

### #054 — Mechanisms and Safe Reversal of Aging

**Question.** If lifespan moves, what would prove that function improved without merely changing how disease was counted?

**Current evidence boundary.** NIA's Interventions Testing Program runs standardized studies at three sites in genetically heterogeneous mice, uses pilot toxicity testing, and expands promising agents to health, pathology, and mechanism endpoints.

**First gate.** Use a blinded, multi-site, sex-stratified protocol with frozen dosing, pilot toxicity, survival, function, pathology, and tumor endpoints.

**Denominator.** Concurrent vehicle control under the same husbandry and a three-site protocol modeled on the NIA ITP.

**Primary metric.** Site-pooled survival effect paired with prespecified late-life function and pathology outcomes.

**Acceptance rule.** A candidate advances only if survival and at least one late-life functional endpoint improve, direction is not reversed at any site, and tumor/pathology safety guardrails do not worsen.

**Falsifier.** The survival effect is site-specific, functional outcomes do not improve, or any preregistered toxicity or tumor guardrail worsens.

**Split.** Pilot toxicity stage followed by independent multi-site efficacy stage; both sexes reported separately.

**Safety boundary.** No animal experiment is executed here; no human anti-aging recommendation or extrapolation.

**Next artifact.** P054 endpoint and adverse-event ontology aligned to public ITP outcomes.

**Source.** [US National Institute on Aging — Interventions Testing Program](https://www.nia.nih.gov/research/dab/interventions-testing-program-itp/about-itp). Updated 2026-05-12; documents three-site SOPs, pilot toxicity, and staged efficacy testing. Access: public.

### #055 — Neurodegenerative Disease Root Causes

**Question.** Can a proposed mechanism predict who changes next, not merely describe who is already ill?

**Current evidence boundary.** ADNI provides longitudinal, multi-center observational data and aggregate views from more than 2,500 participants to validate biomarkers for Alzheimer's disease trials.

**First gate.** Freeze one mechanism-derived biomarker signature, a future clinical-change window, site-aware preprocessing, and an untouched acquisition-site holdout.

**Denominator.** Age, sex, APOE status, baseline diagnosis, and baseline cognition without the proposed mechanism-derived features.

**Primary metric.** Calibration and time-dependent prediction error for prospective cognitive or diagnostic change on the site holdout.

**Acceptance rule.** The mechanism signature must improve held-out prediction error with a bootstrap interval excluding zero and remain calibrated across site and sex strata.

**Falsifier.** No incremental predictive value remains, calibration fails in a prespecified stratum, or the signature uses post-baseline information.

**Split.** Participant-, family-, time-, and acquisition-site-separated holdout.

**Safety boundary.** Observational biomarker research only; prediction does not establish a root cause or treatment effect.

**Next artifact.** P055 ADNI variable/timepoint manifest and post-baseline leakage sentinel.

**Source.** [Alzheimer's Disease Neuroimaging Initiative — ADNI data portal](https://adni.loni.usc.edu/). Current portal reports a longitudinal multi-center cohort with more than 2,500 participants. Access: registration and data-use agreement.

### #056 — Programmable Immune Control

**Question.** Can an immune controller hit its target state without borrowing success from cytokine toxicity?

**Current evidence boundary.** ImmPort exposes standardized clinical-trial, flow-cytometry, gene-expression, intervention, and adverse-event data, enabling donor-held-out retrospective control tests but not safe prospective immune programming.

**First gate.** Select a perturbation study with matched baseline, response, dose, and adverse-event measurements; freeze target and guardrail biomarkers before model fitting.

**Denominator.** No-treatment or standard-treatment arm plus a linear dose-response model using the same donor information.

**Primary metric.** Held-out donor target-state error with separate cytokine, off-target-cell-state, and adverse-event guardrails.

**Acceptance rule.** Target-state error must improve versus both denominators while every prespecified guardrail is non-inferior on donor-held-out data.

**Falsifier.** Apparent control requires donor leakage, a guardrail worsens, or benefit is confined to one study batch.

**Split.** Donor- and study-level holdouts; no cell-level random split across the same donor.

**Safety boundary.** Retrospective public-data analysis only; no dosing, immunotherapy, or clinical control recommendation.

**Next artifact.** P056 ImmPort study shortlist with donor-key, intervention, assay, and adverse-event completeness checks.

**Source.** [NIH/NIAID ImmPort — ImmPort Documentation](https://docs.immport.org/). Current repository supports immunology, clinical-trial, flow-cytometry, gene-expression, intervention, and adverse-event data. Access: free registration; controlled data may require approval.

### #057 — Global Reversal of Antimicrobial Resistance

**Question.** Can an AMR forecast beat yesterday's resistance rate where surveillance is thinnest?

**Current evidence boundary.** WHO GLASS standardizes resistance and antimicrobial-use surveillance and its 2025 global report provides a current cross-country evidence base; surveillance coverage and comparability remain part of the problem.

**First gate.** Freeze one pathogen-drug pair, country-year eligibility rules, missingness policy, and future-year holdout before forecasting.

**Denominator.** Last-observation-carried-forward and a country-specific logistic time trend using the same GLASS rows.

**Primary metric.** Calibration and weighted absolute error for held-out resistance prevalence, stratified by surveillance completeness.

**Acceptance rule.** The candidate must beat both denominators overall and in the lowest-completeness prespecified stratum without excluding countries after outcomes are seen.

**Falsifier.** The gain disappears in sparse-surveillance settings, calibration fails, or post-outcome completeness filtering changes the cohort.

**Split.** Forward-chaining country-year holdout with country-level robustness replay.

**Safety boundary.** Population-level surveillance analysis only; no antibiotic prescribing or pathogen-engineering guidance.

**Next artifact.** P057 pathogen-drug-country coverage matrix and missing-not-at-random sensitivity plan.

**Source.** [World Health Organization — Global Antimicrobial Resistance and Use Surveillance System](https://www.who.int/initiatives/glass). GLASS lists the Global antibiotic resistance surveillance report 2025. Access: public.

### #058 — Pandemic Prediction and Interdiction

**Question.** How early is an early warning after false alarms and reporting delays are charged to the score?

**Current evidence boundary.** CDC's 2026 wastewater program covers multiple viruses, updates public dashboards weekly, and describes wastewater as an early-warning signal that must be interpreted with clinical surveillance.

**First gate.** Freeze jurisdictions, pathogens, reporting-delay simulation, alert thresholds, and a future seasonal window before producing alerts.

**Denominator.** Seasonal historical average, last-value trend, and clinical-data-only alerting at the same false-alert budget.

**Primary metric.** Median lead time before a clinical threshold, conditional on a prespecified false-alert rate and data-availability lag.

**Acceptance rule.** Wastewater-plus-clinical alerting must gain at least seven median days over every denominator while staying within the frozen false-alert budget on unseen jurisdictions and weeks.

**Falsifier.** Lead time is below seven days, false alerts exceed budget, or the gain vanishes after realistic reporting delays.

**Split.** Geographic and forward-time holdout with vintage-aware data snapshots.

**Safety boundary.** Retrospective forecasting only; no live public-health alert or interdiction action.

**Next artifact.** P058 vintage-aware CDC data manifest and alert-score replay harness.

**Source.** [US Centers for Disease Control and Prevention — About Wastewater Data](https://www.cdc.gov/nwss/about-data.html). Updated 2026-04-10; documents multi-virus weekly data, early warning, and clinical-data complementarity. Access: public.

### #059 — Human Brain Connectome and Cognition

**Question.** Can a connectome predict cognition after family structure, head motion, and scanner artifacts are denied an escape route?

**Current evidence boundary.** The HCP-Young Adult 2025 release provides updated processed imaging for 1,071 subjects and phenotypic data for 1,206, with documented processing changes and quality-control exclusions.

**First gate.** Freeze one cognitive endpoint, motion and acquisition covariates, family groups, connectome construction, and an untouched family-level holdout.

**Denominator.** Demographics, motion, scanner/acquisition variables, and regional anatomy without functional-connectivity edges.

**Primary metric.** Family-held-out prediction error and test-retest reliability, with incremental value over the full nuisance denominator.

**Acceptance rule.** Connectivity must add reproducible held-out value with a bootstrap interval excluding zero and no material degradation after motion-matched replay.

**Falsifier.** The increment disappears after family-aware or motion-matched replay, or test-retest reliability is below the preregistered floor.

**Split.** Family-separated train/validation/test split; retest participants used only for reliability.

**Safety boundary.** Research-only neuroimaging; no individual cognitive diagnosis, identity inference, or causal cognition claim.

**Next artifact.** P059 HCP-YA 2025 subject-family/QC manifest and nuisance-only denominator.

**Source.** [Human Connectome Project — HCP Young Adult](https://www.humanconnectome.org/study/hcp-young-adult). 2025 release lists 1,071 processed imaging subjects and phenotypic data for 1,206 subjects. Access: open and restricted tiers.

### #060 — Safe Scalable Gene Editing

**Question.** What would make an editing result fail even when its on-target number looks excellent?

**Current evidence boundary.** FDA's 2024 final genome-editing guidance covers design, manufacturing, nonclinical safety, and trials; 2026 draft guidances separately address next-generation-sequencing safety assessment and reuse of prior knowledge.

**First gate.** Freeze one somatic-cell edit, manufacturing lot criteria, on-target assay, orthogonal off-target assays, chromosomal-integrity tests, and long-term follow-up triggers.

**Denominator.** Unedited cells, mock delivery, and the current standard editor/delivery system assessed with identical assays and sequencing depth.

**Primary metric.** On-target functional correction reported jointly with off-target edits, structural variants, chromosomal integrity, viability, immunogenicity, and lot variability.

**Acceptance rule.** No safety or scalability claim is promotable unless every assay-specific threshold is preregistered, met across independent lots, and non-inferior to the standard editor at matched sequencing sensitivity.

**Falsifier.** Any safety threshold fails, a signal is assay-specific and not orthogonally confirmed, or scale changes lot variability or detection sensitivity.

**Split.** Independent manufacturing lots and blinded assay laboratories; discovery and confirmation assays remain separate.

**Safety boundary.** No sequence design, wet-lab editing, germline work, clinical recommendation, or claim of FDA compliance.

**Next artifact.** P060 assay-and-lot evidence matrix aligned to final and draft FDA guidance.

**Source.** [US Food and Drug Administration — Cellular & Gene Therapy Guidances](https://www.fda.gov/vaccines-blood-biologics/biologics-guidances/cellular-gene-therapy-guidances). April-June 2026 draft guidances add NGS safety assessment and prior-knowledge considerations to the 2024 final guidance. Access: public.

## Claim boundary

Passing this packet means only that all twelve projects have an auditable first research gate.
It does **not** mean the gates have been executed, that any result generalizes, or that any of
the twelve frontier problems has been solved. Retrospective prediction does not establish
causality; protocol design does not establish clinical benefit; and a safety checklist does
not establish safety.
