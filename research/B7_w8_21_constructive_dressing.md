# B7 w8_21 Constructive Local Dressing

- Status: `constructive_dressing_complete_no_resource_reduction_claim`
- Classification: `exact_two_cnot_local_dressing_normal_form`
- Requirements: `10/10`
- Payload hash: `c850d553eb0a1ec5338314f2bbe7f656035f56270dcc9a956cb9991ec7b1988e`

## Heuristic question

Can an exact controlled-unitary dressing expose a rotation-free interface around the repeated w8_21 block, or does exact synthesis preserve all five continuous degrees of freedom?

## Constructive factorization

The relative block has the Euler form `W = Rz(alpha) Ry(2c) Rz(gamma)` with `alpha=-a-b-pi` and `gamma=a-b-pi`. The standard controlled-unitary identity gives `controlled(W) = (I tensor A) CX (I tensor B) CX (I tensor C)` with `A=Rz(-a-b-pi) Ry(c)`, `B=Ry(-c) Rz(b+pi)`, and `C=Rz(a)`.

After absorbing A into the source control-zero branch, the exact normal form is

`U = (I tensor Ry(e) Rz(d)) CX (I tensor Ry(-c) Rz(b+pi)) CX (I tensor Rz(a))`.

At the source point the constructive unitary residual is `4.074e-16` and the controlled-relative residual is `4.475e-16`. A deterministic family replay covers `65` points; the maximum constructive-unitary residual is `5.895e-16`.

## Resource boundary

The normal form keeps two CNOTs and five arbitrary parameters. It is therefore a constructive synthesis identity and a better scaffold for future local-dressing search, not a resource reduction. No occurrence, proxy-T, B7, lower-bound, or solved-frontier credit is assigned.
