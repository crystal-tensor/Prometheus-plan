# B9 R192 Connected Overlap Spectral Boundary

## Verdict

- Status: `checked_connected_overlap_spectral_boundary`
- Requirements: `14/14`
- Protocol hash: `82a4ecb46703068aa3b41a8db082f4b366208d5d6f61a2cdaa9c4eedc8476d56`
- Payload hash: `79b6a21e9dd5813ca2e3ff42af22ee24a15291c79ce0dde20f33fcd1f3309e7e`
- Transcript hash: `16c4d4d6f9d8403c7e133dc51795802acf0085c9f072affb6566b1350c7e550d`
- Lean module warnings: `0`
- New credit delta: `0`

## Frozen Model

R192 fixes the open-chain Hamiltonian
`H = sum_i[-X_i+(3/4)Z_i] + (1/2)sum_i Z_i Z_{i+1}`
for `n=4..10`. The denominator is
the R191 disjoint-site product control under the same local field.

## Formal Structural Gate

Lean checks two-site bond support, exact one-site overlap between
adjacent bonds, three-site coverage by the first two bonds, Hermiticity
of every declared operator layer, and a nonzero exact commutator between
the tilted one-site block and an adjacent `ZZ` bond.

## Independent Spectral Replay

| n | dim | gap | width | norm gap | product norm | ratio | distinct levels | even r | odd r | checked |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| 4 | 16 | 1.51651018 | 10.55732758 | 0.14364527 | 0.25000000 | 0.5746 | 16/16 | 0.5069 | 0.5135 | True |
| 5 | 32 | 1.45201140 | 13.27026448 | 0.10941842 | 0.20000000 | 0.5471 | 32/32 | 0.4482 | 0.4891 | True |
| 6 | 64 | 1.40741538 | 15.97997387 | 0.08807370 | 0.16666667 | 0.5284 | 64/64 | 0.5558 | 0.4979 | True |
| 7 | 128 | 1.37968920 | 18.69096109 | 0.07381585 | 0.14285714 | 0.5167 | 128/128 | 0.5548 | 0.4906 | True |
| 8 | 256 | 1.35962527 | 21.40145572 | 0.06352957 | 0.12500000 | 0.5082 | 256/256 | 0.4844 | 0.4489 | True |
| 9 | 512 | 1.34538800 | 24.11214170 | 0.05579712 | 0.11111111 | 0.5022 | 512/512 | 0.5071 | 0.4935 | True |
| 10 | 1024 | 1.33463620 | 26.82275351 | 0.04975761 | 0.10000000 | 0.4976 | 1024/1024 | 0.5067 | 0.4969 | True |

Both implementations produce byte-identical integer matrices before
division by four. Reflection commutes exactly with every integer
Hamiltonian, so level statistics are computed separately inside even
and odd reflection sectors.

## Result

- Full-spectrum degeneracy collapse: `7/7` finite sizes.
- Normalized-gap target passes: `0/7`.
- Normalized-gap ratio range versus R191: `0.4976` to `0.5746`.
- The connected overlap destroys the R191 single-site product spectrum at the checked sizes, but it does not improve the preregistered normalized-gap denominator.
- Reflection-resolved adjacent-gap ratios are recorded as a diagnostic; their finite-size variation is not promoted into a quantum-chaos or nonintegrability claim.

## Supported

- Lean checks connected two-local support, adjacent-bond overlap, Hermiticity, and exact local-bond noncommutation.
- Independent integer bit-action and Kronecker implementations match exactly for n=4..10.
- Every checked finite spectrum is simple, while the R191 product denominator has only n+1 distinct levels with binomial multiplicity.
- Reflection symmetry is resolved before adjacent-gap statistics are computed.
- The connected overlap normalized gap misses the 1.05x product target at every checked size, so promotion and new credit remain zero.

## Not Supported

- Finite degeneracy collapse is not an all-n spectrum theorem or a proof that no alternate integrable representation exists.
- Reflection-resolved adjacent-gap ratios are finite-size diagnostics, not a nonintegrability or quantum-chaos theorem.
- No spectral-hardness theorem, hardware execution, Quantum PCP theorem, NLTS theorem, BQP separation, solved frontier, or new credit is supported.

## Next Gate

Preregister a bounded coupling sweep and an adversarial low-weight
conserved-operator/free-fermion search. A later result may discuss
nonintegrability only if the symmetry-resolved spectral signal is
stable across size and coupling and the escape-route search fails.
