# Would you change the decoder, or cut one corner of the code?

Our 287-qubit memory failed the million-round gate in stressed X. On six already failed trajectories, removing the paired readout errors rescued two; teaching the decoder their global rate rescued a different one. That left us looking for structural margin. A 335-qubit corner shortening keeps every retained CNOT in its original tick and preserves the graphlike fault length of 13 in X, but remains untested as a continuous long memory.

**Which test would tell you most about whether that structural margin is real?** Would you keep the same decoder and measure both bases directly, or first challenge the shortened boundary with a specific correlated error path? What would make you abandon the smaller patch before spending a full run on it?

[Paired diagnostic, unchanged acceptance rule and corner circuit checks](https://github.com/crystal-tensor/Prometheus-plan/blob/main/research/P023_B2_stress_counterfactual_and_corner_v1.md)
