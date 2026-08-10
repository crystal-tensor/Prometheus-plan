Can a connectome predict cognition—or only family resemblance, head motion, and scanner history?

The seductive result in connectomics is an accurate cognitive predictor. The dangerous result looks identical until relatives, motion, reconstruction version, regional anatomy, and preprocessing are forced into the room first.

The #059 HCP-YA 2025 contract now freezes that confrontation. The target is the unadjusted NIH Toolbox Fluid Cognition Composite. The nuisance-only model gets exact age, gender, education, four-run motion summaries, run availability, reconstruction version, QC A-E indicators, intracranial volume, and all 68 regional cortical-thickness fields. It gets **zero connectivity edges**.

Only then may a second ridge model add 64,620 Fisher-z edges from a 360-area HCP-MMP1.0 connectome built from the 2025 Reclean+tICA resting-state product. No S1200 2017 processing may be mixed in. Entire biological families—not subjects or scans—enter a deterministic 70/15/15 split.

The public evidence exposes an uncomfortable retest mismatch: the 2017 interval table and BALSA project describe 46 retested subjects, while the 2025 processed release contains 45. Without an exact current crosswalk, which single subject would you drop—and what evidence would make that choice non-arbitrary?

The prediction gate is intentionally severe:

- family-held-out `delta_mae` must have a clustered 95% lower bound above zero;
- median edgewise test/retest ICC(2,1) must reach the preregistered 0.40 engineering floor;
- within-subject connectome similarity must beat between-subject similarity; and
- a cognition-blind motion-matched replay must preserve a positive interval and at least 80% of the gain.

Which failure would change your mind fastest?

1. the gain vanishes when twins and siblings cannot cross the split;
2. the gain survives family separation but collapses after motion matching;
3. prediction improves while edge reliability stays below 0.40;
4. the 45-subject current retest roster cannot be reconstructed without guessing; or
5. anatomy alone explains nearly everything attributed to connectivity?

And a harder design question: should QC-D/E subjects remain in the primary cohort when HCP says FIX-cleaned scans are reasonable, or should every A-E code be excluded even at the cost of power?

Useful contributions are falsifiable: a lawful current-roster crosswalk, a correction to the frozen fields, a better cognition-blind motion matching rule, a family-safe split audit, or a reliability threshold you can defend before seeing outcomes.

Reproducibility: **37/37** formal checks over **15** hash-bound official snapshots; an independent parser is run separately. No participant data, image, connectome, cognition outcome, model, diagnosis, identity inference, causal cognition, clinical utility, or solved-frontier claim is made.
