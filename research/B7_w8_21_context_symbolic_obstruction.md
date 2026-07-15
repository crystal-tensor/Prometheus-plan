# B7 w8_21 Context Symbolic Obstruction

- Status: `context_symbolic_obstruction_complete_same_branch_no_absorption`
- Classification: `scoped_same_relative_branch_left_dressing_obstruction`
- Exact symbolic checks: `7/7`
- Contexts tested: `7`
- Same-branch absorptions allowed: `0/7`
- Payload hash: `5b410e143131a4680276980c479920c1ced73e27a45e7b3882d7219e93a13fa6`

## Heuristic question

If the neighboring Rz does not change the controlled relative block, why can it still resist a five-parameter refit?

## Symbolic result

For the fixed relative-block branch, the source left dressing is `Ry(e) Rz(d)`. A post-context rotation produces `Rz(theta) Ry(e) Rz(d)`. The candidate five-parameter form has only `Ry(ep) Rz(dp)` on the left.

When `sin(e/2)` and `cos(e/2)` are nonzero, compare the two phase ratios:

- off-diagonal ratio: context `exp(i(theta-d))`, candidate `exp(-i dp)`;
- diagonal ratio: context `exp(i(theta+d))`, candidate `exp(i dp)`.

Multiplying the ratios forces `exp(2*i*theta)=1`, hence for real angles `theta = 0 mod pi`. This is an exact same-branch obstruction, not a global lower bound.

## Source-bound check

The seven selected contexts have generic source dressing in `7/7` rows. Their distance from the necessary condition is between `0.5692420427088251` and `0.5692420427088251`. Same-branch absorption is allowed in `0/7` rows.

## Claim boundary

This artifact covers only the same relative-block branch and the declared two-parameter left dressing. It does not exclude alternate parameter branches, other Clifford scaffolds, ancillas, measurements, or a full-circuit rewrite. Accepted occurrence removal, proxy-T reduction, and B7 credit remain zero.

## Next route

Enumerate the discrete relative-block branches symbolically, then test whether any branch changes the phase-ratio obstruction without adding CNOTs or an additional arbitrary parameter.
