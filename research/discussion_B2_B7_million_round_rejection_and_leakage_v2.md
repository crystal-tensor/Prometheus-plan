# When a memory fails at one million rounds, should we change the code or the decoder?

The 335-qubit corner-cut circuit made no logical errors in four 1,000-round tests. At one million rounds, both Z conditions hit four errors by 512 trajectories, above the preset cap of three. The 449-qubit reference passed. Independently, real three-state readouts from a 26-round repetition experiment did not improve our decoder against binary or shuffled controls. Neither short tests nor additional inputs guarantee a usable improvement.

**What is the smallest same-trajectory test that would tell you whether the lost Z protection is a property of the code boundary or a result of the decoder breaking up correlated fault events?** What evidence would justify investing in another full million-round run?

[Original acceptance audit and archived failures](https://github.com/crystal-tensor/Prometheus-plan/blob/main/research/P023_d15_million_acceptance_and_B2_corner335_v1.md) · [Measured three-state tests](https://github.com/crystal-tensor/Prometheus-plan/blob/main/research/B7_qutech_ternary_likelihood_v2.md)
