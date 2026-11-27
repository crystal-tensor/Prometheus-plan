# Can you make a million-round experiment cheaper without making it easier to pass?

Our distance-15 simulation had been drawing faults one mechanism at a time. Grouping **identical** probabilities accelerated the 128-shot sampler 8–10×, while replaying the same fault bits into the original simulator reproduced every tested detector and logical bit. A single nominal X or Z run now covers a real million rounds in about 15 seconds of measured sample-plus-decode work. The four independently seeded long qualification cohorts still have to clear the same two-basis gate; those timing shots do not count.

**What evidence would convince you that a faster sampler really preserves a long-memory experiment?** Is exact event replay the decisive test, or would you also require a test against a specific correlated fault process? If you have another exact acceleration, which workload and invariants should both implementations freeze before competing?

[Method, raw timing vectors and independent gate audit](https://github.com/crystal-tensor/Prometheus-plan/blob/main/research/P023_grouped_sampler_checkpoint_v1.md)
