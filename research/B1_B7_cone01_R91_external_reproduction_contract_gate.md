# B1/B7 Cone01 R91 External Reproduction Contract Gate

- Target: `T-B1-004go/T-B7-015x`
- Upstream target: `T-B1-004gn/T-B7-015w`
- Method: `b1_b7_cone01_r91_external_reproduction_contract_gate_v0`
- Status: `cone01_r91_external_reproduction_contract_open_no_submission_yet`
- Model status: `r90_review_exported_as_external_reproduction_contract_no_new_credit`

## Result

R91 exports the R89/R90 one-unit proxy credit into a fillable external
reproduction or falsification contract. It defines the required fields for
a third-party submission, emits a template, and rejects the current empty
submission until independent environment, command transcript, target-row
recomputation, and double-count evidence are supplied.

No external reproduction is accepted yet. No falsification is accepted yet.
No new credit is granted. The R89/R90 one-unit proxy credit remains the only
counted B7 credit and remains bounded to `1.20x` proxy FT/STV scope.

## Key Counters

- Required fields: `28`
- Production-required fields: `14`
- Accepted review modes: `5`
- External submission accepted: `False`
- Preflight failed gates: `6`
- Missing production fields: `12`
- Accepted external reproductions: `0`
- Accepted external falsifications: `0`
- New credit delta: `0`
- 1.20x margin inherited from R90: `8`
- 1.25x margin inherited from R90: `-224`

## Requirements

- `A1` PASS: R91 binds the R90 result, review ledger, verdict, and blocker queue
- `A2` PASS: R91 emits an external reproduction contract with required schema
- `A3` PASS: R91 emits a fillable external submission template
- `A4` PASS: R91 rejects the current empty submission before external evidence exists
- `A5` PASS: R91 grants no new credit and keeps stronger claims closed
- `A6` PASS: R91 emits blockers for external submission, double-count attack, and stronger B7 evidence

## Artifacts

- Result JSON: `results/B1_B7_cone01_R91_external_reproduction_contract_gate_v0.json`
- Contract: `results/B1_B7_cone01_o3_f4_exit_route_submissions/R91-G1-external-reproduction-contract.json`
- Template: `results/B1_B7_cone01_o3_f4_exit_route_submissions/R91-G1-external-reproduction-submission.template.json`
- Empty submission: `results/B1_B7_cone01_o3_f4_exit_route_submissions/R91-G1-external-reproduction-empty-submission.json`
- Preflight verdict: `results/B1_B7_cone01_o3_f4_exit_route_submissions/R91-G1-external-reproduction-preflight.verdict.json`
- Stdout: `results/B1_B7_cone01_o3_f4_exit_route_submissions/R91-G1-external-reproduction-contract.stdout.txt`
- Blocker queue: `results/B1_B7_cone01_o3_f4_exit_route_submissions/R91-G1-external-reproduction-blocker-queue.json`

## Claim Boundary

R91 is a collaboration contract, not a new technical credit. It accepts
no external submission yet, grants no new B7 credit, does not close the
1.25x gap, and does not close O3, physical-layout, resource-saving, or
product-readiness claims.
