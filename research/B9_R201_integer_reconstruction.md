# B9 R201 Bounded Integer Reconstruction and Exact D^44 GCD

- Date: `2026-10-31`
- Track: `B9`
- Status: `characteristic-zero determinants reconstructed; exact common D^44 factor verified`
- CRT modulus bits: `455`
- Proved uniqueness threshold bits: `427`
- Characteristic-zero engineering determinants verified: `true`
- Exact `D^44` divisibility verified: `true`
- Exact four-minor gcd equals `D^44` up to a unit: `true`
- Ideal-membership certificate verified: `false`
- Frozen holdouts executed: `false`
- Scientific promotion: `false`
- New credit: `0`

## Question

What changes when the last prime crosses the proof boundary?

## Unique Integer Lift

The final 16-prime modulus has 455 bits. The unconditional coefficient-bound
packet proves that 427 bits are sufficient for uniqueness. For every one of the
`17,205` homogeneous degree-184 slots in each minor, the reconstruction tool
combines all residues, chooses the symmetric representative, reduces it back
through every prime, and verifies it remains within that minor's independent
coefficient bound.

| Minor | Bound bits | Observed max bits | Determinant terms | Integer payload SHA-256 |
| --- | ---: | ---: | ---: | --- |
| 0 | 423 | 276 | 8,649 | `2b2c648c5c88d48030614d30fc3da80c88a2fe6d2bfe1d7c75e3f76a83ae0ae2` |
| 1 | 425 | 294 | 4,468 | `3f1548d87a7676dabbe2ede170d9afa39b5fceffaa110cc568222ed26240c857` |
| 2 | 426 | 291 | 4,770 | `7868ff4c90d125de7e316b3c00301bba262c9ba7275bdb6323e2816232dd0189` |
| 3 | 402 | 250 | 2,760 | `3852ded7f97e3682fee46e3ccfc19f67d1a4c295706c72822d1df385a499fa99` |

All `1,101,120/1,101,120` coefficient-slot-prime round trips pass. The full
lattice hashes agree with the final CRT replay, so the explicit integer payloads
and the independently audited modular state are byte-bound.

## Exact D^44 Division

Let `D=a^2+b^2+c^2`. Each reconstructed degree-184 determinant divides exactly
by `D^44` over `ZZ[a,b,c]` with zero remainder:

| Minor | Quotient degree | Quotient terms | Quotient SHA-256 | Remainder terms |
| --- | ---: | ---: | --- | ---: |
| 0 | 96 | 2,401 | `f5f0f0852982e77fa37616f04d3a80d439c4510ad9314a9ea9477a5e05a3a41d` | 0 |
| 1 | 96 | 464 | `45db745f1338ae620bec3c4cac00f2b39593ece912bd9f5dc71fd6f829f11597` | 0 |
| 2 | 96 | 590 | `94fbdc546fa078c435a739021dbbb572eb1175b22964b76cc42889a700aa9a10` | 0 |
| 3 | 96 | 450 | `d704ec553cee5903c8a44058b5795ab84af74341304ba3486fc727285551d97a` | 0 |

The gcd of the four degree-96 quotients is the unit polynomial `1`; its payload
hash is `09fd7f6e6c63e50501a1908da4fbe0997357fdc3fd593638e578e4d221140236`.
Therefore the four characteristic-zero determinants have exact common gcd
`D^44` up to a unit.

## Claim Boundary

This result verifies four characteristic-zero engineering determinants and
their exact common `D^44` factor under the public `J=13/32` engineering row.
It does not yet provide the Nullstellensatz or ideal-membership multipliers
needed for the continuous full-rank certificate, does not independently replay
an isolated pre-source certificate generator, and does not open the frozen
`J=127/128,131/128` holdouts. It is not a Quantum PCP or NLTS theorem, BQP
separation, quantum-hardware result, solved frontier, scientific promotion, or
new credit.

## Next Gate

Use the four degree-96 quotients as the exact generator set for a replayable
ideal-membership certificate. Bind every multiplier and product term to the
integer payload hashes above, then reproduce the certificate through the
isolated pre-source path before either frozen coupling can open.
