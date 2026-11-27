# #021/B7: preserving the flagged readout did not produce a validated gain

2026-11-27. Adding the observed third class to a causal likelihood decoder **did not beat both binary baselines or the misalignment control**. This was an independent source-held-out test: 85,840 real records per injection setting, 26 rounds, no active leakage removal and no postselection. It rules out this small likelihood model for the tested purpose, not the utility of measured leakage in general.

## A fixed test of a different use for the flag

In the [eight-round diagnostic](B7_qutech_ternary_same_shot_v1.md), discarding flagged observations made errors worse with active injection. The [new protocol](../benchmarks/B7_qutech_ternary_likelihood_v2.json) does not discard the hard readout. It models the probability of the class-2 assignment given the hard readout and latent ancilla state, and allows the flag to change the next round's nearby data-flip probabilities. The matched binary comparator is the same fitted probability model with the unavailable flags summed out; its decoder is not handicapped by substituting all-zero flags.

The [original QuTech download](https://doi.org/10.4121/902d7f9e-38bf-48a2-a2f7-52bbf7aeeedf) supplies measured rows for the Z-basis distance-three repetition code at these conditions. The 26-round members are the first common provider train/test round count greater than eight; all eight preparations were included. Model parameters were fitted to 1,536 training rows per setting (192 per preparation). The model sees no training/test member duplication or earlier eight-round member, and receives only terminal adjacent parities at inference—not the terminal logical parity. The placebo shifts class-2 assignments to other shots with the same hard-one slot, retaining the flag count per preparation, round and ancilla line without changing any binary readout.

| Injection setting | Test shots | Binary-only fit | Matched hard marginal | Aligned ternary | Shuffled ternary |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 85,840 | 33,912 | 33,878 | 33,917 | 33,915 |
| 3 | 85,840 | 40,928 | 40,985 | 40,983 | 40,961 |

In the actively injected cell, aligned flags rescued 214 and harmed 212 versus the matched marginal (two fewer failures; exact one-sided \(p=0.481\)), while the independently binary-trained policy made 55 fewer errors than the aligned policy. The aligned policy did not beat the shuffled control in either cell. Both settings failed the predeclared diagnostic criterion of \(p\le0.0125\) versus both binary baselines and fewer failures than the shuffle. The joint fit estimated equal within-observation flag probabilities for the two latent binary states in both settings; that is a feature of this fit, not a calibrated measurement of the hardware or proof that flags are causally irrelevant.

This analysis does not reproduce the [authors' leakage-informed neural decoder](https://doi.org/10.1103/y66v-988s), use their weights, or establish a non-regression claim for the three original T5 challenges. B7 still needs a source/calibration join accepted for that denominator and a paired holdout win; there is no B7 resource credit.

## Verify and replay

The [source receipts, paired predictions and result](../results/B7_qutech_ternary_likelihood_v2/) bind 32 separate original ZIP members. Two source replays were byte-identical. A separate integer-bit audit independently verifies decision counts, recoveries, harms, and the exact binomial tails without rerunning the models:

```sh
python3 -B tools/b7_qutech_ternary_likelihood_audit_v2.py results/B7_qutech_ternary_likelihood_v2
export OPENBLAS_NUM_THREADS=1
qec_src=$(mktemp -d)
qec_result=$(mktemp -d)
python3 -B tools/b7_qutech_likelihood_intake_v2.py --artifact-dir "$qec_src"
python3 -B tools/b7_qutech_ternary_likelihood_v2.py --artifact-dir "$qec_src" \
  --out-dir "$qec_result" --freeze 0894d8e141fd11f54cd64b0b0424e2c96cc55c94
cmp "$qec_result/score.json" results/B7_qutech_ternary_likelihood_v2/score.json
```
