# B7 w8_21 Two-Frame Control-Side Clifford Search

- Status: `double_control_frame_search_complete_no_exact_context_replay`
- Classification: `bounded_two_frame_control_side_clifford_boundary`
- Families tested per context: `432`
- Contexts tested: `7`
- Optimizer runs: `6048`
- Exact context replays: `0/7`
- Best residual norm: `0.2301426459717444`
- Payload hash: `711ebabbcb6a0642fac278f447804bc437538d63a54387be9fce39d57f72d4c9`

## Heuristic question

Can two fixed control-side Clifford frames in different layers alter the phase obstruction without adding a CX or arbitrary angle?

## Search scope

The candidate retains two CX gates and five arbitrary target-side source angles. It inserts two fixed control-side `+/- pi/2` Euler rotations in two distinct local layers, exhausts all layer pairs, axes, signs, and CX direction sequences, yielding 432 families per context.

## Result

| Context | Exact families | Best residual | Best two-frame word |
|---:|---:|---:|---|
| 1 | 0 | 0.2301426459717444 | `pre:q0:rz0=-pi/2, mid:q0:rz0=+pi/2, CX 0101` |
| 2 | 0 | 0.2301426459717444 | `pre:q0:rz0=-pi/2, mid:q0:rz0=+pi/2, CX 0101` |
| 3 | 0 | 0.2301426459717444 | `pre:q0:rz0=-pi/2, mid:q0:rz0=+pi/2, CX 0101` |
| 4 | 0 | 0.2301426459717444 | `pre:q0:rz0=-pi/2, mid:q0:rz0=+pi/2, CX 0101` |
| 5 | 0 | 0.2301426459717444 | `pre:q0:rz0=-pi/2, mid:q0:rz0=+pi/2, CX 0101` |
| 6 | 0 | 0.2301426459717444 | `pre:q0:rz0=-pi/2, mid:q0:rz0=+pi/2, CX 0101` |
| 7 | 0 | 0.2301426459717444 | `pre:q0:rz0=-pi/2, mid:q0:rz0=+pi/2, CX 0101` |

No exact five-angle replay was found in the declared two-frame control-side Clifford family.

## Claim boundary

This closes only the 432 two-frame families in the declared search. It is not a global KAK lower bound, an exhaustive Clifford-word search, or a full-circuit rewrite. Accepted occurrence removal, proxy-T reduction, and B7 credit remain zero.

## Next route

If this boundary remains negative, the next test should change the nonlocal word itself or move to a symbolic invariant for longer words, with exact arbitrary-input replay and resource pricing required before promotion.
