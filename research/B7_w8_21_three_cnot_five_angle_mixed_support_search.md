# B7 w8_21 Three-CX Five-Angle Mixed-Support Search

- Status: `three_cnot_five_angle_mixed_support_search_complete_no_exact_context_replay`
- Classification: `bounded_three_cnot_five_angle_mixed_support_frontier`
- Families tested per context: `720`
- Contexts tested: `7`
- Optimizer runs: `10080`
- Exact context replays: `0/7`
- Best residual norm: `1.033550478227691`
- Payload hash: `fded77822169a0bc98f1271820a24ba21f0f93ba17c3db773804248a988659c1`

## Heuristic question

Can moving one of five arbitrary angles off the target side absorb a non-grid external local rotation?

## Search scope

The candidate changes local support rather than merely adding target-side slots: three CX gates, the source target-side `Rz(pi)` scaffold fixed, four source target-side arbitrary slots retained, and one arbitrary slot allowed on any other local Euler slot. All eight CX direction sequences are exhausted. This is a bounded support-pattern frontier test, not a global synthesis claim.

## Result

| Context | Exact families | Best residual | Best mixed-support family |
|---:|---:|---:|---|
| 1 | 0 | 1.033550478227691 | `CX 010101; pre:q0:rz0, pre:q1:rz0, mid1:q1:ry, post:q1:rz0, post:q1:ry` |
| 2 | 0 | 1.033550478227691 | `CX 010101; pre:q0:rz0, pre:q1:rz0, mid1:q1:ry, post:q1:rz0, post:q1:ry` |
| 3 | 0 | 1.033550478227691 | `CX 010101; pre:q0:rz0, pre:q1:rz0, mid1:q1:ry, post:q1:rz0, post:q1:ry` |
| 4 | 0 | 1.033550478227691 | `CX 010101; pre:q0:rz0, pre:q1:rz0, mid1:q1:ry, post:q1:rz0, post:q1:ry` |
| 5 | 0 | 1.033550478227691 | `CX 010101; pre:q0:rz0, pre:q1:rz0, mid1:q1:ry, post:q1:rz0, post:q1:ry` |
| 6 | 0 | 1.033550478227691 | `CX 010101; pre:q0:rz0, pre:q1:rz0, mid1:q1:ry, post:q1:rz0, post:q1:ry` |
| 7 | 0 | 1.033550478227691 | `CX 010101; pre:q0:rz0, pre:q1:rz0, mid1:q1:ry, post:q1:rz0, post:q1:ry` |

No bounded exact replay was found in this family.

## Resource boundary

The candidate spends one additional CX to retain five arbitrary angles while moving one angle off the target-side support. Occurrence removal, proxy-T reduction, and B7 credit remain zero until a concrete arbitrary-input rewrite and full ledger pass.

## Claim boundary

This closes only the declared mixed-support family with four retained source target-side slots and one external local slot. It is not a global three-CX lower bound, an exhaustive local-Euler search, a full-circuit rewrite, or a solved B1/B7 frontier.
