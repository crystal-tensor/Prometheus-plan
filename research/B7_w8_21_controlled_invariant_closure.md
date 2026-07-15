# B7 w8_21 Controlled-Unitary Invariant Closure

- Status: `controlled_invariant_closure_complete_scoped_no_compression_claim`
- Classification: `family_level_symbolic_invariant_closure`
- Requirements: `10/10`
- Payload hash: `f778ad7583c83420cbca6eb420fc2c153d92293fa08d6a66973bc18fda046f3c`

## Heuristic question

If the repeated w8_21 block is a controlled-unitary family with one nonlocal invariant parameter, can the remaining local dressing be rewritten without paying five arbitrary rotations at every occurrence?

## Derived closure

In the control-target basis the source order is block diagonal: `U = |0><0| tensor U0 + |1><1| tensor U1`. Direct 2x2 multiplication gives

`W = U0^dagger U1 = [[-exp(i*b)*cos(c), -exp(i*a)*sin(c)], [exp(-i*a)*sin(c), -exp(-i*b)*cos(c)]]`,

so `tau = trace(W)/2 = -cos(b)cos(c)`. The corresponding magic-basis matrix satisfies the candidate identity `m^2 - 2*tau*m + I = 0`, and its characteristic polynomial is `(lambda^2 - 2*tau*lambda + 1)^2`. The formula is independent of `d` and `e` at the relative-block level.

For the source point, `tau = 0.5000000000000002` with error from `1/2` equal to `2.220e-16`. The magic quadratic residual is `1.032e-15` and the characteristic-coefficient residual is `2.245e-15`.

A deterministic family check covers `65` parameter points. The maximum relative closed-form residual is `8.874e-16` and the maximum characteristic-coefficient residual is `6.673e-15`.

## Interpretation

This upgrades the earlier pointwise KAK observation into a family-level invariant closure for this fixed skeleton. It identifies a one-parameter nonlocal invariant and gives a cleaner target for local-dressing synthesis. It does not prove a compression rewrite, a lower CNOT count, a reduction in arbitrary rotations, or any B7 resource credit.
