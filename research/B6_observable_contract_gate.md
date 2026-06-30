# B6 Observable Contract Gate

Status: **observable_contract_open_missing_dft_b5_rows**

## Summary

- Method: `b6_observable_contract_gate_v0`
- Requirements passed / failed: 4 / 2
- Failed requirement IDs: O5, O6
- Observable packets: 5
- DFT schema hash: `e9215a51f2736f1c29890577b201ad5980b835dd787bd9bde4f2484293f17388`
- B5 schema hash: `79217e965af5e0d4ed95f143fcfd0aa3936edef001a292f559a70cf9e688c576`
- DFT rows / B5 rows: 0 / 0

## Packets

- B6-O1-dft-row-schema: Submit DFT observable rows
- B6-O2-b5-row-schema: Submit B5-computed observable rows
- B6-O3-hash-preservation: Preserve replay hashes
- B6-O4-join-key-audit: Join observables to replayed materials
- B6-O5-claim-boundary-audit: Prevent observable rows from becoming premature discovery claims

## Requirement Results

- O1 [PASS]: backend replay source exists
- O2 [PASS]: replay hashes are preserved
- O3 [PASS]: DFT row schema is declared
- O4 [PASS]: B5 row schema is declared
- O5 [FAIL]: DFT observable rows exist
- O6 [FAIL]: B5-computed observable rows exist

## Claim Boundary

- Supported: Observable packet schemas and hash-preservation requirements are now explicit.
- Not supported: No DFT or B5 observable rows exist yet, and no material discovery or mechanism solution is claimed.
- Next gate: Submit DFT and B5 rows that satisfy the declared schemas and preserve replay hashes.
