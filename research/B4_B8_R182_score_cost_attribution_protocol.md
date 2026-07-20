# B4/B8/B10 R182 Exact-Score Cost-Attribution Protocol

- Status: `preregistered_design_unopened`
- Protocol payload hash: `c4108dd5cab9d33cfe6a69f7822892f8ae4a151d6d3c4b5f8f41c2bd297dbe03`
- Contract payload hash: `065799ba197dc8cd81a7138b1e821848540fe7f1d559da3f26fa1f1e604b700a`
- Scientific execution: unopened
- Execution tooling: deliberately unbound at this design gate

## Heuristic Question

R181 reduced full-width arithmetic scans but missed both frozen speed gates. Are full-array destination initialization, retained-binary64 construction, comparison work, carry propagation, or BigUint heap behavior the dominant source-bound cost pressures?

## Frozen Attribution Channels

R182 separates retained-binary64 leaf construction, destination initialization, arithmetic limb visits, comparison limb visits, carry extension, and BigUint heap activity. The instrumented path must preserve every selected mapping before any cost classification is accepted.

## Decision Boundary

The experiment may identify a source-bound cost pressure, reject the proposed attribution, or remain inconclusive. It may not promote a counter correlation into a causal compiler remedy. Execution remains blocked until the patch, runner, oracle, build tool, bundle tool, and public workflow are hash-bound in a second-stage execution contract.

## Claim Boundary

This is a preregistered classical compiler cost-attribution design. It is not an upstream Qiskit patch, production remedy, hardware result, quantum advantage, BQP separation, solved B4/B8/B10 frontier, or new credit.
