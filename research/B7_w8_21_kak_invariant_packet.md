# B7 w8_21 Local KAK Invariant Packet

- Status: `kak_invariant_packet_complete_scoped_not_global_lower_bound`
- Classification: `local_invariant_and_rank_witness_recorded`
- Requirements: `10/10`
- Payload hash: `dfcf50857d603c9fd6638516b62c963959bbcfabfc56bac26a3f40ae34ef8018`

## Heuristic question

Does the w8_21 source block carry five locally independent continuous directions even after global phase is removed, and can its local invariant spectrum anchor a future symbolic KAK proof?

The source block is unitary to residual `1.159e-16`. An analytic derivative packet gives numerical rank `5` with singular values `[1.3656979118908799, 1.1334112322340968, 0.9999999999999999, 0.8458007913484042, 0.3672454403486733]`. The largest recorded 5x5 minor has determinant `2.371168e-02` over phase-projected real coordinates.

The magic-basis m-matrix unitarity residual is `1.124e-15` and the four invariant eigenphases are `[-1.0471975511965976, -1.0471975511965976, 1.0471975511965974, 1.0471975511965976]` radians.

## Interpretation

This is a source-bound local invariant and differential-rank witness. It makes the next symbolic route more concrete, but it does not prove that every two-CNOT circuit needs five arbitrary rotations, does not exclude arbitrary Clifford scaffolds or three-CNOT constructions, and creates no occurrence-removal, resource, B7, hardware, advantage, BQP, or solved-frontier credit.
