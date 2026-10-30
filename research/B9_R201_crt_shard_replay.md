# B9 R201 Fourth Incremental CRT Shard Replay

- Date: `2026-10-31`
- Track: `B9`
- Status: `four planned prime shards complete; bounded CRT incomplete`
- New determinant artifacts: `16/56`
- Completed additional primes: `4/14`
- Bounded CRT integer reconstruction complete: `false`
- Characteristic-zero `D^44` divisibility verified: `false`
- Frozen holdouts executed: `false`
- Scientific promotion: `false`
- New credit: `0`

## Question

Can six agreeing finite fields create a false sense of coefficient stability while the unique integer lift remains 262 bits away?

## Four New Determinants

The fourth added prime in the frozen plan is `536,870,849`. All four public `37x37` determinants complete exactly over `GF(536,870,849)`:

| Minor | Total degree | Terms | Artifact SHA-256 |
| --- | ---: | ---: | --- |
| 0 | 184 | 8,649 | `1d4d41bfa57f926ddd653bb19c5e3dfaa81028177cbcb094510f900b63fe7c80` |
| 1 | 184 | 4,468 | `5896b5cb59bf3c4459e9c21c9bffdd29c55834ae3f6f82ad88712affa28a48ff` |
| 2 | 184 | 4,770 | `f5e550cd2aaf3c31d5cd100a840591e2eb92d073639f15e5ef64e4405fa92b59` |
| 3 | 184 | 2,760 | `1482f215db7e642d682c39bb0614412a4faa053af5780d4d347f992bc38404d7` |

Every artifact preserves its frozen row-set hash, source-matrix hash, candidate-label hash, bridge-tool hash, degree, term count, and zero-credit boundary.

## Independent Matrix Replay

`tools/b9_r201_crt_shard_replay.py` loads all 24 determinant artifacts now available across

```text
1,000,003
536,870,723
536,870,909
536,870,879
536,870,869
536,870,849
```

For every artifact it rebuilds the frozen matrix at five public deterministic points, computes the `37x37` determinant with project-owned modular Gaussian elimination, evaluates the stored polynomial independently, and compares the two values.

All `120/120` matrix-determinant point replays match. Artifact binding errors are zero.

## Partial CRT State

The six-prime modulus is

```text
44,601,596,703,050,957,462,716,084,525,238,582,972,915,796,217,879
```

with bit length `165`. For every minor, the verifier walks the complete `17,205`-slot homogeneous degree-184 lattice, treats omitted modular terms as zero, computes a symmetric partial CRT residue, and reduces that residue back modulo every source prime.

| Minor | Support terms | Slot-prime round trips | Partial residue hash |
| --- | ---: | ---: | --- |
| 0 | 8,649 | 103,230/103,230 | `837d3d485a8b6afc00c7ea86a87ca4b33b89da754e0c0c132d12317fdbd53f4a` |
| 1 | 4,468 | 103,230/103,230 | `8410598ecd24eb80ce99bd5309990bd626ef87440a1fc2c2613bcab595b59701` |
| 2 | 4,770 | 103,230/103,230 | `0805445d8dcc1b6f69f5e863a6b9e207ae7f970baff7afaeabc7cc89b9455b13` |
| 3 | 2,760 | 103,230/103,230 | `0d4909db1079b564b9cc982b9e2b3e6e3fa404c3a7ab44b7ee19a54ed4b4c9ca` |

All four monomial supports match across all six primes. Aggregate coefficient-slot round trips pass `412,920/412,920`.

## Why This Is Not Yet Integer Reconstruction

The proved uniqueness threshold has 427 bits. The current modulus has only 165 bits, so many different bounded and unbounded integers can share the same six residues. The symmetric values hashed above are partial CRT representatives, not verified characteristic-zero coefficients.

The execution ledger is now:

```text
completed new primes:      4/14
completed new artifacts:  16/56
remaining new primes:     10
remaining new artifacts:  40
```

## Claim Boundary

This result verifies the first four modular execution shards and their partial CRT round trips. It does not uniquely reconstruct an integer coefficient, verify a characteristic-zero determinant, prove `D^44` divisibility, compute a characteristic-zero gcd, emit the ideal-membership certificate, open either frozen coupling, establish Quantum PCP or NLTS, separate BQP, claim hardware evidence, promote the science result, or add credit.

## Next Gate

Compute the four minors at planned prime `536,870,839`, rerun the full point and slot-roundtrip audit, and advance the ledger to `20/56` artifacts only if every binding and replay remains exact.
