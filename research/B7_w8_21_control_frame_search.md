# B7 w8_21 Control-Side Clifford-Frame Search

- Status: `control_frame_search_complete_no_exact_context_replay`
- Classification: `bounded_control_side_fixed_clifford_frame_boundary`
- Families tested per context: `72`
- Contexts tested: `7`
- Optimizer runs: `1008`
- Exact context replays: `0/7`
- Best residual norm: `0.7886609149859014`
- Payload hash: `c1e7b114d501ecbb13d17872e7793dcfc8622a2eae2f233825e0c849a13a5389`

## Heuristic question

Can one fixed control-side Clifford frame change the continuous escape route without adding a CNOT or a sixth arbitrary angle?

## Search scope

The candidate keeps two CX gates and the five arbitrary target-side source angles. It adds exactly one fixed control-side `+/- pi/2` Euler rotation, exhausts all three local layers, all three Euler axes, both signs, and all four CX direction sequences. This yields 72 families per context and is distinct from the earlier target-slot relocation search.

## Result

| Context | Exact families | Best residual | Best frame |
|---:|---:|---:|---|
| 1 | 0 | 0.7886609149859014 | `mid:q0:rz0=-pi/2, CX 1010` |
| 2 | 0 | 0.7886609149859014 | `mid:q0:rz0=-pi/2, CX 1010` |
| 3 | 0 | 0.7886609149859014 | `mid:q0:rz0=-pi/2, CX 1010` |
| 4 | 0 | 0.7886609149859014 | `mid:q0:rz0=-pi/2, CX 1010` |
| 5 | 0 | 0.7886609149859014 | `mid:q0:rz0=-pi/2, CX 1010` |
| 6 | 0 | 0.7886609149859014 | `mid:q0:rz0=-pi/2, CX 1010` |
| 7 | 0 | 0.7886609149859014 | `mid:q0:rz0=-pi/2, CX 1010` |

No exact five-angle replay was found in the declared control-side Clifford-frame family.

## Claim boundary

This closes only the 72 fixed-frame families in the declared search. It is not a global KAK lower bound, not an exhaustive Clifford-word search, and not a full-circuit rewrite. Accepted occurrence removal, proxy-T reduction, and B7 credit remain zero.

## Next route

The remaining continuous route is a longer fixed Clifford word or a genuinely different nonlocal skeleton, with exact arbitrary-input replay and resource pricing required before promotion.
