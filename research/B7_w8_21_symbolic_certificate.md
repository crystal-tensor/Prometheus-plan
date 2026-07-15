# B7 w8_21 Machine-Checked Symbolic Certificate

- Status: `symbolic_certificate_complete_scoped_no_resource_claim`
- Classification: `exact_fixed_skeleton_symbolic_invariant_certificate`
- Exact checks: `6/6`
- Machine checked: `True`
- Payload hash: `89fb12d301b06418d73f0553559e17589e98670f04825a5253ffad87a3e98080`
- Candidate hash: `1db53e9e6be5fd2dda830ca53a583f1e72dd45b92295bede5f783800c24fbed3`

## Heuristic question

Can a fixed two-CNOT circuit family carry a compact exact invariant certificate without that certificate being mistaken for a compression theorem?

## Exact symbolic result

SymPy constructs the source-order role block with symbolic parameters `a,b,c,d,e`. It proves the control-target block form, the closed relative block

`W = [[-exp(i*b)*cos(c), -exp(i*a)*sin(c)], [exp(-i*a)*sin(c), -exp(-i*b)*cos(c)]]`,

the half-trace `tau = -cos(b)*cos(c)`, unitarity, independence from `d,e`, and the exact Cayley-Hamilton relation `W^2 - 2*tau*W + I = 0`.

All `6` exact checks pass. The certificate is bound to the source QASM and to the existing fixed-family numerical closure; the prior search digest retains `43480` optimizer runs and `8880` three-CNOT attempts with `0` passing candidates.

## Boundary

This is a scoped exact identity for one fixed role skeleton. It does not prove a global KAK obstruction, minimality, a shorter rewrite, resource reduction, or B7 credit. The next technical question is whether this invariant can be connected to a source-level occurrence-removing certificate without introducing equally expensive local parameters.
