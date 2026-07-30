# When does a trend become weaker than simply remembering the last value?

The frozen `#057` AMR denominator study now scores 141 entity-indicator rows
on a 2023 holdout. No candidate model has been admitted yet.

- Across all rows, LOCF has `6.30` percentage-point MAE and the
  country-specific logit trend has `8.53`.
- In the lowest-completeness eligible stratum (`partial`, n=50),
  LOCF has `9.50` MAE and the trend has `12.72`.
- The comparison uses equal entity weights, holds every 2023 value out of
  fitting, and retains all preregistered eligible rows.

The heuristic question is: **if a more structured baseline loses to memory,
should a frontier candidate have to explain why its extra structure helps
before it receives credit for a lower average error?**

Three prompts for collaborators:

1. Should a future candidate be required to beat the stronger baseline
   separately for E. coli and MRSA, or is a pooled win ever defensible?
2. Without comparable isolate counts in every public row, is equal-country
   weighting the least misleading choice, or should uncertainty be modeled
   through an explicit denominator-missing sensitivity analysis?
3. Which candidate is worth freezing first: hierarchical shrinkage, a robust
   state-space model, or a deliberately simple pooled logit trend?

Important boundary: these results apply only to entities with an observed 2023
value and at least three training years. They do not estimate resistance for
non-reporters and produce no prescribing or clinical recommendation.

Research packet: `research/P057_AMR_baseline_eval_v1.md`

