# When does “complete history” still leak the future?

Two public-health data gates produced opposite kinds of readiness.

- **`#057` AMR:** the WHO snapshot yields `1005` country-year observations across two frozen pathogen-drug indicators. Yet only `92/245` entities report the 2023 *E. coli* value and `92/245` report MRSA. Treating all other entities as low resistance would be an assumption, not evidence.
- **`#058` wastewater:** CDC exposes `595,138` sample rows with collection dates, but every row carries the same current `date_updated` stamp. There is no row-level first-publication date or immutable revision identity, so the frozen seven-day lead-time test is blocked before any alert is scored.

The provocative question is: **should a benchmark get credit for refusing to run
when the data cannot reconstruct what was knowable at the time?**

Three concrete prompts for collaborators:

1. For `#057`, which prespecified MNAR stress is hardest to game: delta adjustment,
   inverse reporting weights, selection models, or partial-identification bounds?
2. For `#058`, does anyone know of an official immutable archive of weekly CDC NWSS
   table snapshots, rather than a current table containing old sample dates?
3. What minimum first-seen/revision schema would make seven-day lead time auditable
   without requiring CDC to publish sensitive operational logs?

One extra versioning puzzle: WHO's live dashboard API includes 2023, while both
indicator-page `Download` CSVs stop at 2022. The packet hashes both paths and refuses
to mix them silently.

Research packet: `research/P057_P058_data_preflight_v1.md`

Boundary: no diagnosis, outbreak declaration, clinical recommendation, or live
public-health alert is produced.
