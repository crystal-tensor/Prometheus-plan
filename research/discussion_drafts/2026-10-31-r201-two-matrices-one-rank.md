# When Two Matrices Have Different Shapes, Can They Still Prove the Same Rank?

R201 reached an uncomfortable audit question: the source algebra used a `238x37` Pauli-coordinate matrix, while the independent dense route used a `256x37` Hermitian-coordinate matrix. Matching ranks at a few public anchors was useful pressure, but it was not an exact equivalence proof.

The new binding certificate fills the 18 identically zero Pauli rows, constructs a complete `256x256` coordinate transform, and verifies both directions exactly. Its integer matrices satisfy `T*R = R*T = 16I`, with 2,176 nonzero entries in each direction and 256/256 Pauli-matrix roundtrips.

The column relation also exposes a detail that a rank-only comparison would miss:

```text
C_dense = T * C_source * Lambda
M_dense = -2 * T * M_source * Lambda
```

All 37 candidate relations and all 37 commutator relations pass symbolically. The diagonal scaling `Lambda` contributes a total `D^72`, so any selected dense minor obeys

```text
det(E*M_dense) = (-2)^37 * D^72 * det(E*T*M_source_full).
```

Five mutations fail: removing the minus sign, removing the factor two, changing a `D` exponent, reversing the imaginary-coordinate sign, and reversing Kronecker site order.

Questions for contributors:

1. What is the most compact standard-library replay format for the sparse `T` and `R` transforms?
2. Can the known `D^72` factor materially reduce bounded-CRT reconstruction cost for the four frozen dense minors?
3. Which independent coordinate basis would provide the strongest third implementation without recreating the same Kronecker assumptions?
4. How should the future ideal certificate bind each generator to both the source and dense representations without duplicating enormous polynomial payloads?

Relevant artifacts:

- `tools/b9_r201_representation_binding.py`
- `results/B9_R201_source_dense_representation_binding_v0.json`
- `research/B9_R201_representation_binding.md`

Claim boundary: this proves exact equivalence of the two public engineering matrix representations on the declared `D != 0`, characteristic-not-two domain. It does not compute the characteristic-zero engineering minors, certify the selected-minor ideal, open the frozen holdouts, prove nonintegrability, establish Quantum PCP or NLTS, separate BQP, or add scientific credit.
