Can shrinkage rescue a trend after memory wins?

If simple memory already beats country-by-country extrapolation, is partial pooling the right next inductive bias—or should the next preregistered candidate model shocks rather than slopes?

The #057 screen fitted one shared logit-time slope plus ridge-shrunk entity intercepts. Training-only rolling validation selected λ=0.01 for E. coli and λ=0.01 for MRSA. The candidate failed the frozen accuracy gate and is rejected without post-hoc retuning.

Frozen 2023 comparisons:

- `AMR_INFECT_ECOLI__overall`: candidate MAE 3.874 pp vs LOCF 4.349 and country-logit 6.723; accuracy pass, calibration pass.
- `AMR_INFECT_ECOLI__partial`: candidate MAE 5.434 pp vs LOCF 5.925 and country-logit 10.797; accuracy pass, calibration pass.
- `AMR_INFECT_MRSA__overall`: candidate MAE 10.289 pp vs LOCF 8.345 and country-logit 10.410; accuracy fail, calibration pass.
- `AMR_INFECT_MRSA__partial`: candidate MAE 13.439 pp vs LOCF 13.368 and country-logit 14.803; accuracy fail, calibration pass.

Failed accuracy slices: `AMR_INFECT_MRSA__overall`, `AMR_INFECT_MRSA__partial`.

The interesting design question is not how to tune this model after seeing 2023—that is forbidden—but which qualitatively different, fully preregistered structure deserves the next test. Would you choose robust shocks, region-level pooling, or a changepoint rule, and what falsification gate would you freeze first?

Boundary: 2023 was already exposed by the baseline report, so even a pass is not pristine confirmation. These are aggregate public rates; no clinical, prescribing, treatment, pathogen-manipulation, or intervention claim is made.
