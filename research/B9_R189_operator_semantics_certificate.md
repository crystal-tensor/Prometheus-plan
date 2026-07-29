# B9 R189 Operator-Semantics Certificate

## Verdict

- Status: `checked_all_n_matrix_operator_and_spectrum_set_scaling_complete_all_n_ordered_spectrum_formula_open`
- Requirements: `13/13`
- Protocol hash: `3e7e36c8aa9b83c6737a21b1c0458e2b9f66c3f91080b95c501dd776bd4fbadd`
- Payload hash: `24afca7b0ed683f715dc337952c35c4b61e8847c7bb66974dca42052d6164373`
- Transcript hash: `227621753afc8ea6f8412bca7800501c71aa8a1feb6d41f18fd9ecbc52fd75dc`
- Lean module warnings: `0`
- New credit delta: `0`

## Formal Result

Lean now interprets the R188 open-chain support object as an explicit complex
matrix on the `2^n` computational basis. It proves all local words, term
operators, and summed Hamiltonians Hermitian. The independently defined
reweighted Hamiltonian is exactly `(27/20) • H`, and its full complex spectrum
set is exactly `(27/20) • spectrum(H)`.

## Independent Finite Oracle

| n | dimension | nonzero entries | gap | width | normalized gap | checked |
|---:|---:|---:|---:|---:|---:|---|
| 4 | 16 | 64 | 2 -> 27/10 | 8 -> 54/5 | 1/4 | True |
| 5 | 32 | 160 | 2 -> 27/10 | 10 -> 27/2 | 1/5 | True |
| 6 | 64 | 384 | 2 -> 27/10 | 12 -> 81/5 | 1/6 | True |

The independent path rebuilds each matrix from bit flips and neighboring
`Z` phases with Python `Fraction`; NumPy is used only for the eigenspectrum
cross-check.

## Supported

- Lean interprets every R188 open-chain term as a 2^n-dimensional complex Pauli-word matrix.
- Lean proves every local Pauli word, term operator, and summed Hamiltonian Hermitian.
- Lean proves the independently defined reweighted Hamiltonian equals (27/20) times the original operator.
- Lean derives exact complex spectrum-set scaling from the operator identity and a nonzero unit.
- An independent Fraction bit-action oracle exactly reproduces Hermiticity and operator scaling for n=4,5,6.
- Independent NumPy eigenspectra match the finite open-chain formula and show unchanged normalized gap for n=4,5,6.

## Not Supported

- The ordered all-n spectrum formula and all-n spectral-gap formula are not yet formalized in Lean.
- Finite NumPy rows are cross-checks, not a replacement for the remaining all-n ordered-spectrum proof.
- No quantum hardware execution, Quantum PCP theorem, NLTS theorem, global no-go theorem, BQP separation, solved frontier, or new credit is supported.

## Next Gate

Formalize the ordered all-n eigenvalue multiset, including binomial
multiplicities, from the commuting independent stabilizer generators. Then
derive the all-n raw gap, width, and normalized gap from that ordered spectrum
inside Lean rather than from finite NumPy rows.
