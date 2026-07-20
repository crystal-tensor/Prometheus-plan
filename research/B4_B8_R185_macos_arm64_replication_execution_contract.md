# B4/B8/B10 R185 Execution Contract

- Status: `execution_tooling_bound_unopened`
- Contract payload hash: `19d56ee8532617768137b47288e0ad86381084c2fef2daf34fda4f9decf710cf`
- Tool bindings: `5`
- Source bindings: `18`
- Public design commit: `83c0741e47827cf7e09d0622d1edb4912dcf5731`
- Public Discussion: https://github.com/crystal-tensor/Prometheus-plan/discussions/280
- Scientific execution: unopened

## Same-Process Triplets

The frozen matrix contains `468` BigUint/prefix/window triplets in `13` isolated workers. Every triplet runs three uninstrumented timing calls and one separate window probe; probe time is excluded. All six arm orders occur `6` times per cell.

## Isolation Boundary

The BigUint arm is the exact dynamic denominator, the 34-limb prefix arm is the latest fixed-width reference, and the candidate stores an exact four-limb window plus a global offset. Any wider exact sum falls back to BigUint; no truncation or approximate comparison is allowed.

## Claim Boundary

The unchanged patch, local Darwin arm64 runner, oracle, build, and bundle are hash-bound. The later build must run from a clean commit already published as remote main. This contract is not a timing result, universal platform theorem, full-domain performance theorem, upstream Qiskit remedy, hardware result, quantum advantage, BQP separation, solved frontier, or new credit.
