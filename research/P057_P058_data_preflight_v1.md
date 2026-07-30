# Problems `#057`–`#058` Data Readiness Preflight v1

Date: 2026-07-30

Status: **the preflight is valid; `#057` now has a versioned coverage matrix,
while `#058` is blocked before alert scoring because the public table is not a
historical-vintage archive.**

This update remains strictly inside catalog problems `#057` and `#058`. It does
not execute a clinical forecast, issue a public-health alert, or claim that either
frontier problem is solved.

## Machine-check summary

- Contract checks: `21/21` passed.
- `#057`: `coverage_matrix_ready` with `1005` observations and `490` pathogen-drug-entity rows.
- `#058`: `blocked_missing_vintages`; alert model executed: `false`.
- Snapshot SHA-256: `7b840a328bdd59924b41d31dffcda035ef3019de2bc3716e47fe098721300dd9`.

## `#057` — Is missing surveillance being mistaken for low resistance?

The frozen universe is WHO's current set of 245 English `ADMIN_0` reference
entities. The matrix crosses that universe with two bloodstream-infection
indicators and eight years (2016–2023): *E. coli* resistance to third-generation
cephalosporins and methicillin-resistant *S. aureus*.

| Indicator | Observed cells | Cell coverage | 2023 reporters | Forecast-eligible | 2023 observed mean | Worst-case all-entity mean interval |
|---|---:|---:|---:|---:|---:|---:|
| `AMR_INFECT_ECOLI` | 506/1960 | 25.8% | 92/245 | 72 | 46.15% | 17.33%–79.78% |
| `AMR_INFECT_MRSA` | 499/1960 | 25.5% | 92/245 | 69 | 36.76% | 13.80%–76.25% |

The wide worst-case intervals are not estimates. They show that a global mean
is not identified by reported countries alone. The stored delta table asks what
happens if non-reporting entities differ from the observed 2023 mean by −20, −10,
0, +10, or +20 percentage points, with values clipped to the valid 0–100 range.

### A source-version trap

WHO's live dashboard API contains the frozen 2023 holdout, but both official
`Download` CSVs stop at 2022. The packet records each URL, response hash, CSV
hash, ETag, and Last-Modified value. The formal matrix uses the hashed dashboard
API snapshot and makes the download lag visible instead of silently mixing sources.

The next `#057` step is to run the last-observation and country-logistic
denominators only on the preregistered eligible rows, then report errors overall
and in the sparse-completeness stratum. A candidate will not be admitted until
those same-access denominators and the MNAR stress table are fixed.

## `#058` — Can one current history replay what was knowable then?

The CDC table is rich enough for event-time analysis: its 38 fields include
`sample_collect_date`, and the frozen metadata projection covers `595,138` rows from `2020-01-14` through `2026-07-21`. But event time is not publication time.

Every row shares one `date_updated` processing stamp. The schema contains neither
a row-level first-publication date nor an immutable revision identifier. CDC also
states that data may change as reports arrive and documents methodology changes
that were applied retroactively to historical values. A current full history can
therefore contain information that was unavailable at the simulated decision date.

For that reason, the seven-day lead-time gate is **not run**. The minimum repair is
to archive each Friday's full public table with a retrieval time and hash, preserve
row-level first-seen/last-seen dates and corrections, and only then freeze unseen
jurisdictions, weeks, thresholds, and the false-alert budget.

## Official evidence

- WHO AMR dashboard: [Antimicrobial Resistance profile](https://data.who.int/dashboards/amr/antimicrobial-resistance-profile).
- WHO indicator definition and download: [E. coli resistance to third-generation cephalosporins](https://data.who.int/indicators/i/918081E/745F475).
- WHO indicator definition and download: [MRSA](https://data.who.int/indicators/i/918081E/5DD9606).
- CDC dataset metadata: [CDC Wastewater Data for SARS-CoV-2](https://data.cdc.gov/api/views/j9g8-acpt).
- CDC update cadence and intended use: [About Wastewater Data](https://www.cdc.gov/nwss/about-data.html).
- CDC retrospective method revisions: [Wastewater Monitoring Data Methodology](https://www.cdc.gov/nwss/data-methods.html).

## Claim boundary

The packet establishes data-contract readiness, not predictive validity. It does
not infer resistance for non-reporters, compare individual wastewater sites,
diagnose disease, declare an outbreak, recommend an intervention, or solve
catalog problem `#057` or `#058`.
