# B4/B8/B10 R179 Independent Linux Oracle Adjudication

- Status: `evidence_integrity_complete_source_performance_rejection_preserved`
- Requirements: `10/10`
- Payload hash: `46e6fc71b7d9013e49694c5d851c384f2fa02ff4c65721f57aa1a0a8f5fe3425`

## Why The Oracle Says Failed

The independent oracle passes every evidence-integrity recomputation but fails P10 because the frozen source result is rejected at P13. This is the expected behavior: the oracle must not promote a source result that missed its preregistered performance target.

## Independent Evidence

Without importing Qiskit or the R179 executor, the oracle validates `39/39` worker hashes, `2400/2400` row hashes, and `84/84` case hashes. It reproduces `1728/1728` standard outcomes and `672/672` small-gap outcomes, along with timing, memory, and platform bindings.

## Preserved Rejection

The fixed/BigUint aggregate median ratio remains `1.129059`, above the frozen `0.90` ceiling. Evidence integrity is complete; source acceptance remains false. No threshold is changed.

## Claim Boundary

This supports one independent reconstruction of the committed Linux evidence. It does not establish a production or upstream Qiskit remedy, broad performance, quantum-hardware behavior, quantum advantage, BQP separation, solved B4/B8/B10, or new credit.
