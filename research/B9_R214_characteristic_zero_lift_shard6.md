# B9 R214 Characteristic-Zero Lift: Sixth CRT Shard

## Question

Can 412,920 exact checks still describe more than one integer polynomial?

## Result

R214 completes minors 4, 5, and 6 at the sixth planned prime `536870837`.
Together with the two classification primes and the R209-R213 shards, the
partial reconstruction now spans eight pairwise-coprime fields.

| Quantity | R214 result |
|---|---:|
| completed planned primes | `6/14` |
| completed new determinant artifacts | `18/42` |
| remaining new determinant artifacts | `24` |
| combined modulus | `12855531450783183035157337214212514962907942258337906440421603482597` |
| combined modulus bit length | `223` |
| worst uniqueness threshold | `428` bits |
| primary CRT round trips | `412920/412920` |
| independent CRT round trips | `412920/412920` |
| independent matrix replays | `72/72` |
| independent `D^44` recompositions | `72/72` |

The modulus grows by another 29 bits, but it remains below the proved
428-bit threshold. The partial symmetric representatives therefore remain
non-promotable.

## Sixth Prime Shard

The new field preserves the determinant and quotient supports seen in the
first five shards:

| Minor | Determinant terms | Degree-96 quotient terms | Modular division |
|---:|---:|---:|---|
| 4 / R204 | 5,997 | 1,113 | exact `D^44` |
| 5 / R206 | 6,555 | 1,363 | exact `D^44` |
| 6 / R208 | 5,309 | 821 | exact `D^44` |

Every artifact also replays the four frozen public matrix points and verifies
the quotient recomposition at those points.

## Independent Audit

The independent path validates the exact artifact grid for all eight primes,
then rebuilds every completed new-prime matrix with custom modular Gaussian
elimination. It imports none of the primary CRT state when recombining the
17,205 homogeneous coefficient slots with `sympy.ntheory.modular.crt`.

All `72/72` matrix values and `72/72` `D^44` recompositions match. Both CRT
implementations pass `412920/412920` residue round trips and agree on every
nonzero count, maximum symmetric residue, and partial payload hash.

Adversarial overlay tests additionally reject a changed determinant
coefficient and a missing frozen replay point through the immutable artifact
grid binding.

## Claim Boundary

This is a sixth exact modular shard and an independently replayed partial CRT
state. It is not an integer reconstruction, characteristic-zero `D^44`
certificate, rational Nullstellensatz identity, global-rank theorem, Quantum
PCP or NLTS result, quantum-hardware result, scientific promotion, or new
credit. The frozen `J=127/128,131/128` holdouts remain sealed.

## Next Gate

Compute minors 4, 5, and 6 at the seventh planned prime `536870819`. Rerun
both CRT implementations over nine total primes, preserve the full
artifact-grid and frozen-point checks, and continue to reject promotion until
the combined modulus exceeds twice every proved coefficient bound.
