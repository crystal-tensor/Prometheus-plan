# P057 AMR shared-slope shrinkage candidate screen

**Decision:** `reject_candidate`.

## What was frozen

For each indicator, the candidate fits one shared logit-time slope and ridge-shrunk entity intercept deviations. The ridge penalty was selected only from 2019–2022 rolling-origin validation; no 2023 outcome entered selection.

- E. coli selected λ: `0.01`
- MRSA selected λ: `0.01`
- Evaluated 2023 rows: `141`

## 2023 candidate screen

| Slice | Candidate MAE | LOCF MAE | Country-logit MAE | Candidate abs. bias | Calibration limit | Primary | Calibration |
|---|---:|---:|---:|---:|---:|:---:|:---:|
| AMR_INFECT_ECOLI__overall | 3.874 | 4.349 | 6.723 | 0.102 | 2.038 | pass | pass |
| AMR_INFECT_ECOLI__partial | 5.434 | 5.925 | 10.797 | 1.191 | 2.023 | pass | pass |
| AMR_INFECT_MRSA__overall | 10.289 | 8.345 | 10.410 | 1.477 | 2.259 | fail | pass |
| AMR_INFECT_MRSA__partial | 13.439 | 13.368 | 14.803 | 5.727 | 7.057 | fail | pass |

Pooled descriptive candidate MAE was **7.013 pp** with absolute calibration bias **0.670 pp**. The frozen gate is decided only by the four indicator-overall/partial slice comparisons above.

## Confirmation boundary

The 2023 outcomes had already been summarized in the published baseline evaluation before this candidate protocol was frozen. Therefore, a gate pass could only be called a provisional retrospective screen pass, never pristine confirmatory validation. A pass would still require an untouched future year or data vintage; a failure rejects this exact candidate without post-hoc retuning.

## Reproducibility and limits

- Formal checks: `22/22`
- Protocol commit: `4bf9192b5eb0272f08e1324455d1f4933388bef9`
- Aggregate public resistance rates are forecasting targets, not individual-level clinical outcomes.
- No patient, prescribing, treatment, pathogen-manipulation, or intervention recommendation is supported.
- This screen does not solve catalog problem #057.
