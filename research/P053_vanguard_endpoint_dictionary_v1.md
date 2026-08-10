# P053 Vanguard endpoint and claim dictionary v1

**Decision:** `endpoint_dictionary_ready_claims_separated`.

## What changed in the public protocol

[NCT06995898](https://clinicaltrials.gov/study/NCT06995898) is currently `RECRUITING`, randomized, parallel, screening-purpose, and estimates enrollment of `24,000` participants across three arms. No results section is posted.

The current registry is richer than a simple feasibility label: it lists `6` primary, `20` secondary, and `9` other outcomes. The endpoint dictionary maps all `35` measures exactly once rather than letting one endpoint silently support several claims.

## Frozen evidence ladder

| Level | Evidence class | Minimum evidence | Still does not imply |
|---:|---|---|---|
| 0 | `operational_feasibility` | completed registered primary feasibility outcomes with prespecified denominators and numeric success thresholds | assay accuracy, diagnostic benefit, mortality reduction, personalized treatment, cure |
| 1 | `diagnostic_pathway_and_harm` | resolved and unresolved abnormal-test pathways, time to resolution, procedures, complications, anxiety, contamination, and standard-screening participation | mortality reduction, personalized treatment, cure |
| 2 | `assay_performance` | prospective sensitivity, specificity, predictive values, interval cancers, false positives, tissue-of-origin accuracy, and complete cancer ascertainment | stage-shift benefit, mortality reduction, personalized treatment, cure |
| 3 | `clinical_utility_and_mortality` | completed randomized arm-specific estimand with adequate follow-up, prespecified multiplicity and power, mortality ascertainment, and joint benefit-harm accounting | treatment personalization, cure |
| 4 | `personalized_treatment_or_cure` | treatment-specific randomization, molecular assignment rule frozen before outcomes, comparative treatment outcomes, toxicity, recurrence, and survival | No higher claim encoded |

## The two traps

**A registered mortality field is not a mortality result.** Targeted cancer-specific mortality, cancer-specific mortality, and all-cause mortality are present only as `other` outcomes, with no posted results. The study remains a recruiting feasibility trial, and NCI describes it as groundwork for later definitive randomized evaluation.

**A measurement window is not a success threshold.** All six primary outcomes provide a measure and time frame, but `0/6` state an explicit numeric go/no-go cutoff for the measure itself. Enrollment goals, 60/90-day windows, and references to trial targets describe observation, not the minimum result that would make feasibility pass.

## Timing sentinel

The registry gives an actual start of `2025-06-18` and estimated completion of `2029-06-30`, a calendar span of `4.03` years. Long-term outcomes are listed through `12` years, while the detailed description says passive follow-up up to `10` years. This does not invalidate the study; it means the public calendar and long-term estimands require alignment before any mortality claim is promoted.

## What the current outcomes can eventually test

- Primary outcomes: recruitment, questionnaires, year-one blood draw, retention, representative enrollment, and staggered-arm feasibility.
- Diagnostic pathway and harm: result return, diagnostic resolution, contamination, standard screening, complications, anxiety, and cancer worry.
- Assay performance: sensitivity, specificity, predictive values, false positives, interval cancers, detected cancers, and tissue-of-origin accuracy.
- Long-term clinical utility: stage, mortality, and costs—but only after results, adequate randomized estimands, power, multiplicity control, follow-up, and joint harm accounting.
- Personalized treatment or cure: absent; the protocol does not randomize treatment or test a molecular therapy-selection rule.

## Reproducibility and next falsifier

The formal packet passes `25/25` checks. The current ClinicalTrials.gov JSON and five NCI pages are hash-retained. No participant-level analysis or comparison between the two assays was performed.

The next falsifier is a public numeric feasibility decision rule: denominators and pass/fail thresholds for each primary endpoint, plus a registry calendar aligned to the longest planned outcome. Assay performance, diagnostic burden, mortality, and treatment claims remain separate estimands.

## Official sources

- [ClinicalTrials.gov NCT06995898](https://clinicaltrials.gov/study/NCT06995898)
- [NCI Vanguard Study](https://prevention.cancer.gov/research-areas/networks-consortia-programs/csrn/vanguard-study)
- [NCI cancer-screening overview](https://www.cancer.gov/about-cancer/screening/hp-screening-overview-pdq)
- [NCI levels of evidence for screening](https://www.cancer.gov/publications/pdq/levels-evidence/screening-prevention)

No assay recommendation, screening advice, diagnostic action, treatment selection, trial-participation recommendation, mortality benefit, personalized cure, regulatory, or solved-frontier claim is made.
