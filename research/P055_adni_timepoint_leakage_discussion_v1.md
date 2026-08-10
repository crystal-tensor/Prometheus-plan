Can a biomarker predict the future if its timestamp already knows the answer?

A neurodegeneration model can look impressively accurate for the wrong reason: a lab value was collected after baseline, a diagnosis code came from a later visit, two phases reused the same VISCODE, or one enrollment site leaked into both train and test.

The #055 contract now freezes one testable question. Does baseline plasma `pT217_AB42_F` improve site-held-out prediction of ADAS-Cog13 `TOTAL13` change near month 24 beyond age, sex, APOE genotype, baseline diagnosis, and baseline cognition? The outcome window is months 18-30, and every feature must be dated no later than the latest retained baseline input.

The public ADNI dictionary exposes `18` ordered fields for the cross-phase pTau217 table and `3` phase-specific `TOTAL13` rows. The resulting manifest has `13` roles and `9` fail-closed leakage sentinels. But the exact public `FAMILYID` search yields `0` rows, and row-level data require approved IDA access. So the schema is frozen while the model remains unopened.

The most dangerous ambiguity may be the clock itself. ADNI warns that VISCODE meanings vary by phase, that different actual dates can share a visit code, and that VISCODE-only joins can be wrong. This contract therefore uses actual examination or collection dates for the feature cutoff and outcome horizon; administrative timestamps are forbidden.

Which rule would you make non-negotiable before trusting an ADNI progression model: a site-held-out split, a family/relatedness cluster, actual-date reconciliation, an untouched month-24 outcome, or train-only preprocessing? And what evidence would convince you that a missing family identifier has been resolved rather than ignored?

A useful contribution is a falsifiable join rule, lawful relatedness field, missingness state, site-split invariant, or phase-specific data-dictionary correction—not a diagnosis or treatment recommendation.

Reproducibility: `28/28` formal checks over `15` normalized official snapshots; a separate standard-library parser must independently reconstruct the dictionary rows, source hashes, manifest roles, and decision. No participant analysis, model, biomarker threshold, diagnosis, root-cause, treatment-effect, clinical-utility, regulatory, or solved-frontier claim is made.
