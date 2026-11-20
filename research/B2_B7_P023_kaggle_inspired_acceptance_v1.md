# B2/B7/#023 Kaggle-Inspired QEC Acceptance Standard v1

Last updated: 2026-11-20

Status: **kaggle_inspired_strict_1k_reference_verified_p023_b2_b7_credit_closed**

## What is our standard, and what is the baseline?

The standard is verifier-first and cost-second. A QEC candidate receives no resource score unless both X and Z memories pass the same horizon, noise, decoder, and confidence contract. Only verified candidates are compared with a fixed reference by physical-qubit-round cost.

The current reference is the frozen distance-7 rotated-surface-code memory at physical error 0.001, exactly 1,000 rounds, Stim 1.16.0, and PyMatching 2.4.0. Its per-basis operational proxy is `Q×H = 118×1,000 = 118,000` physical-qubit-rounds. Once strictly verified it is normalized to score 1.0; a future candidate must reach a geometric X/Z score of at least 1.25 with neither basis regressing.

## Why the prior pass was downgraded

The earlier 3,838-shot packet used a two-sided 95% Wilson bound. Under the competition-inspired one-sided Clopper–Pearson bound at confidence `1-2^-128`, it is not accepted:

| basis | failures/shots | Wilson 95% upper | strict CP upper | Wilson pass | strict pass |
|---|---:|---:|---:|---|---|
| x | 13/3838 | 0.00578689 | 0.0332351 | True | False |
| z | 14/3838 | 0.0061139 | 0.0338697 | True | False |

This is not a contradiction: 95% exploration and `1-2^-128` acceptance answer different questions. The former guides where to spend shots; the latter decides whether a result can become the comparison baseline.

## Strict 102,400-shot reference run

| basis | seed | failures/shots | observed pL | strict CP upper | target | strict pass | Q×H |
|---|---:|---:|---:|---:|---:|---|---:|
| x | 271056497332980417 | 350/102400 | 0.00341797 | 0.00638657 | 0.01 | True | 118,000 |
| z | 709792491623917302 | 283/102400 | 0.00276367 | 0.00549701 | 0.01 | True | 118,000 |

Both bases strict-pass: **True**. Normalized reference score: **1.0**. Pair cost: **236,000 physical-qubit-rounds**.

## What was adopted from Google’s competition

- correctness verification before any cost score;
- fixed reference-cost / candidate-cost improvement ratios;
- geometric mean across the mandatory X and Z tasks;
- one-sided Clopper–Pearson upper bounds at `1-2^-128`;
- artifact-hash-derived challenge seeds and immutable replay manifests;
- zero score when any correctness or evidence gate fails.

## What was deliberately not copied

The competition's Toffoli formulas price application circuits, not physical logical memory. Its DQI repetition factor is also inapplicable: a bad DQI output can be rejected and rerun, but a failed memory instance has already lost the unknown quantum state. For memory, reliability is therefore a hard veto, not a purchasable repetition penalty.

## Claim boundary

This is an adaptation of evaluation principles, not an official Kaggle metric implementation or competition submission. It does not claim a new code, threshold, scalable or million-round memory, hardware performance, production decoding, B2 low-overhead improvement, B7 resource credit, or quantum advantage.

## Next gate

Freeze a same-condition candidate code/schedule/decoder artifact before revealing its acceptance salt; score it only after both bases pass the strict gate, require Score_QEC>=1.25 with no per-basis regression, and keep #023/B7 closed until million-round and drift/correlation evidence exists.

Formal checks: `24/24`.

Sources: [official Kaggle evaluation](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/overview/evaluation); [official companion paper](https://arxiv.org/abs/2610.23832).
