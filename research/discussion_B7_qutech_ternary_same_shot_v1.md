# If the leakage flag is real, why can erasing the readout make decoding worse?

In a public QuTech experiment, each record includes real three-state ancilla measurements across several rounds. On 85,840 identical test shots with active leakage injection, our replay made 24,959 logical errors with binary input and 25,374 when it discarded the readouts marked as leaked. The flag was real and correctly aligned; this particular way of using it still made the result worse.

**Would you keep the flagged readout and change its likelihood, or treat the flag as evidence for a fault that persists into the next rounds?** What is the smallest same-shot control that could distinguish the two?

[The paired result, source files, and runnable replay](https://github.com/crystal-tensor/Prometheus-plan/blob/main/research/B7_qutech_ternary_same_shot_v1.md)
