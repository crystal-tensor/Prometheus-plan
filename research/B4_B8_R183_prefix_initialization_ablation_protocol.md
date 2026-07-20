# B4/B8/B10 R183 Prefix-Initialization Ablation Protocol

- Status: `preregistered_design_unopened`
- Protocol payload hash: `9057160630b687f79a25f3c02ff45e1974d187393d06d0321297726db7255d67`
- Design contract payload hash: `09cc7e5084b163cc2660c8b77e085bb41cd3d146be9aac147657df7429ce26b3`
- Scientific execution: unopened

## Heuristic Question

R182 cut arithmetic-limb visits by 52.1362% but improved the median end-to-end time by only about 1.25%. Is initializing the unused suffix of the fixed-width exact-score destination the missing dominant cost, or is the remaining time elsewhere in object copies and VF2 control flow?

## Frozen Pairing

The design keeps the same `34`-limb score object and the same active-prefix arithmetic, then changes only whether the unused destination suffix is initialized. Each of `13` cells runs `32` same-process AB/BA pairs with equal order balance.

## Decision Boundary

The candidate must preserve every mapping and every non-initialization counter. A material initialization-write reduction with a paired median timing ratio above 0.90 rejects unused-tail initialization as the dominant source-bound explanation. A ratio at or below 0.90 supports contribution under this frozen implementation, not causal completeness or a production remedy.

## Claim Boundary

This is a preregistered classical compiler micro-ablation. It is not an upstream Qiskit patch, production remedy, hardware result, quantum advantage, BQP separation, solved B4/B8/B10 frontier, or new credit.
