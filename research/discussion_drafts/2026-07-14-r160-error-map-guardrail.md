# When Does Deterministic Tie-Breaking Become a Deterministic Wrong Answer?

## Research question

If four independent accumulation methods stabilize the same tied layout, is the
selector actually repaired, or has it only become consistently wrong near the
tie boundary?

## What R160 tested

R160 ran four external ErrorMap accumulation methods across 16 processes, 33
declared tied and ULP-perturbed cases, and 1,056 direct VF2 calls. Every case
was scored against an exact rational oracle over all 5,040 candidate mappings.

The untouched tie stabilized to one mapping in all four methods. Twelve
margin-protected cases above the frozen 1e-16 gap passed completely. But 224
calls across seven 1-8 ULP near-tie cases returned the stabilized mapping while
the exact oracle preferred another mapping. The executor's positive label was
therefore overruled by an independent adjudication: the bounded tie-stability
claim survives, while complete remediation fails.

## The open challenge

Where do the 1-8 ULP score gaps disappear: accumulation, candidate-score
combination, or the final comparison rule? Can compensated or exact score
accumulation plus an explicit tie tolerance preserve true ties while selecting
the exact optimum for every declared nonzero gap?

## Contribution-sized entry points

- Instrument the candidate-score combination path and produce a first-divergence
  trace for each failing near-tie case.
- Implement an exact/compensated comparison variant without changing the
  candidate set, then replay the frozen 1,056-call contract.
- Design an adversarial near-tie generator that separates stable ties from
  numerically induced false ties.
- Review the claim boundary: what would count as a general compiler fix rather
  than a bounded user-space remediation for one frozen input?

## Claim boundary

R160 does not claim an upstream patch, a confirmed general Qiskit bug,
cross-platform determinism, hardware relevance, route advantage, quantum
advantage, BQP separation, or a solved B4/B8/B10 frontier. It is a reproducible
diagnostic boundary for the next experiment.

Artifacts: [protocol](https://github.com/crystal-tensor/Prometheus-plan/blob/main/research/B4_B8_R160_deterministic_error_map_remediation_protocol.md), [execution](https://github.com/crystal-tensor/Prometheus-plan/blob/main/research/B4_B8_R160_deterministic_error_map_remediation.md), [adjudication](https://github.com/crystal-tensor/Prometheus-plan/blob/main/research/B4_B8_R160_deterministic_error_map_remediation_adjudication.md).
