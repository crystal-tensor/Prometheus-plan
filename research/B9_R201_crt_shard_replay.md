# B9 R201 Fourteenth Incremental CRT Shard Replay

- Date: `2026-10-31`
- Track: `B9`
- Status: `all fourteen planned prime shards complete; bounded CRT complete`
- New determinant artifacts: `56/56`
- Completed additional primes: `14/14`
- Bounded CRT integer reconstruction complete: `true`
- Characteristic-zero `D^44` divisibility verified: `false`
- Frozen holdouts executed: `false`
- Scientific promotion: `false`
- New credit: `0`

## Question

When does the last prime turn modular traces into unique integers?

## Four New Determinants

The fourteenth and final added prime in the frozen plan is `536,870,717`. All
four public `37x37` determinants complete exactly over `GF(536,870,717)`:

| Minor | Total degree | Terms | Artifact SHA-256 |
| --- | ---: | ---: | --- |
| 0 | 184 | 8,649 | `189ec1fd2a7026f0180430056c88dd5316c681e1cc2c17a1292380b484a62a48` |
| 1 | 184 | 4,468 | `68019a4cff4d3030afef9087a7ba6dac4106603033fc987be7a7da8cb055af7a` |
| 2 | 184 | 4,770 | `f52149f0906e42c4c5c09e40c439c9d682dc27c4c565bd3814d670bf7a5703e9` |
| 3 | 184 | 2,760 | `39957de08b307a2f2f1ba72f7118dee0a65c1ef06513c47ec2dbecfde06b0108` |

Every artifact preserves its frozen row-set hash, source-matrix hash,
candidate-label hash, bridge-tool hash, degree, term count, and zero-credit
boundary.

## Independent Matrix Replay

`tools/b9_r201_crt_shard_replay.py` loads all 64 determinant artifacts now
available across

```text
1,000,003
536,870,723
536,870,909
536,870,879
536,870,869
536,870,849
536,870,839
536,870,837
536,870,819
536,870,813
536,870,791
536,870,779
536,870,767
536,870,743
536,870,729
536,870,717
```

For every artifact it rebuilds the frozen matrix at five public deterministic
points, computes the `37x37` determinant with project-owned modular Gaussian
elimination, evaluates the stored polynomial independently, and compares the
two values.

All `320/320` matrix-determinant point replays match. Artifact binding errors
are zero.

## Partial CRT State

The sixteen-prime modulus is

```text
88,725,429,155,847,367,123,952,464,860,805,265,032,336,625,105,857,301,461,886,875,442,859,544,774,910,805,027,980,599,480,961,817,515,313,659,979,716,796,526,414,431,390,834,144,683
```

with bit length `455`. For every minor, the verifier walks the complete
`17,205`-slot homogeneous degree-184 lattice, treats omitted modular terms as
zero, computes a symmetric partial CRT residue, and reduces that residue back
modulo every source prime.

| Minor | Support terms | Slot-prime round trips | Partial residue hash |
| --- | ---: | ---: | --- |
| 0 | 8,649 | 275,280/275,280 | `a5b03bfcdbdbb85b2b3d6de0fe1e5c2237a6bbc109a09285c086c89248b3850e` |
| 1 | 4,468 | 275,280/275,280 | `19f0ebbdfab6495ac0ac22ac9b897197cf1caed2690f954cf6d26519504103b6` |
| 2 | 4,770 | 275,280/275,280 | `be26aa18d457cac31aeb5377e2e048d190325600a9f7447c89f13a2d3a91470d` |
| 3 | 2,760 | 275,280/275,280 | `ff43773999bf35766538e8faf35d2ecaac21d3620a6d05fb8c77aaed7f9b1bf2` |

All four monomial supports match across all sixteen primes. Aggregate coefficient-slot round trips pass `1,101,120/1,101,120`.

## Why This Is Now Unique Integer Reconstruction

The proved uniqueness threshold has 427 bits and the final modulus has 455
bits. Because every true coefficient is covered by the unconditional bound and
the modulus now exceeds twice that bound, every symmetric CRT representative is
the unique bounded integer coefficient. The companion reconstruction gate
rebuilds those coefficients explicitly before testing exact polynomial
division.

The execution ledger is now:

```text
completed new primes:      14/14
completed new artifacts:  56/56
remaining new primes:      0
remaining new artifacts:  0
```

## Claim Boundary

This result verifies all fourteen modular execution shards, their CRT round
trips, and the bound crossing needed for unique integer coefficients. The
companion integer-reconstruction result verifies the characteristic-zero
determinants and their exact common `D^44` factor. Neither result emits the
ideal-membership certificate, opens either frozen coupling, establishes
Quantum PCP or NLTS, separates BQP, claims quantum-hardware evidence, promotes
the science result, or adds credit.

## Next Gate

Consume the unique integer determinants in the characteristic-zero certificate
builder. Emit replayable ideal-membership multipliers for the four degree-96
quotients, bind them to the isolated pre-source reconstruction, and keep the
two frozen couplings sealed until that certificate passes independently.
