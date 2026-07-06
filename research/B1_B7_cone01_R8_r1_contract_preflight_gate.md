# B1/B7 Cone01 R8 R1 Contract Preflight Gate

- Target: `T-B1-004dj/T-B7-012s`
- Method: `b1_b7_cone01_r8_r1_contract_preflight_gate_v0`
- Status: `cone01_r8_r1_contract_preflight_rejects_existing_evidence`
- Preflight: `B1-B7-cone01-R8-R1-contract-preflight`
- Preflight hash: `e6d5be7ca79021780009f91fd17df8ec206db924e6d402c12472aa854bbac977`
- R7 contract hash: `ffee37b9f6d07567fb60488cec42140757903ff8cb2deec812f4195f91bd897b`

## Result

The R8 preflight gate passes 9/9 requirements by rejecting the existing evidence package against both R7 acceptance routes. This is useful negative pressure, not a solution claim.

## Route A Preflight

- Passed: `False`
- Failed predicates: `3`
- `PASS` source_r6_inventory_hash matches contract (observed `43aeb8f22af8d3043489d73b50c5d57f3779e4f4ea02798479096c3448a3149b`, required `43aeb8f22af8d3043489d73b50c5d57f3779e4f4ea02798479096c3448a3149b`)
- `PASS` line1381_off_grid_parameter_count_before == 5 (observed `5`, required `5`)
- `FAIL` line1381_off_grid_parameter_count_after == 0 (observed `5`, required `0`)
- `PASS` five-parameter repair is packet-exact (observed `1`, required `1`)
- `FAIL` full replay or symbolic equivalence for the submitted R1 artifact is present (observed `no submitted R1 artifact replay/symbolic-equivalence hash`, required `full_replay_or_symbolic_equivalence_hash`)
- `FAIL` resource and no-double-counting ledgers for the submitted R1 artifact are present (observed `no submitted R1 resource_delta_ledger_hash/no_double_counting_ledger_hash`, required `both ledger hashes`)

## Route B Preflight

- Passed: `False`
- Failed predicates: `3`
- `PASS` source_r6_inventory_hash matches contract (observed `43aeb8f22af8d3043489d73b50c5d57f3779e4f4ea02798479096c3448a3149b`, required `43aeb8f22af8d3043489d73b50c5d57f3779e4f4ea02798479096c3448a3149b`)
- `FAIL` physical_pricing_replay.cost_minus_credit <= 0 (observed `365`, required `<= 0`)
- `FAIL` physical pricing replay is accepted (observed `False`, required `True`)
- `FAIL` submitted R1 pricing and ledger hashes are present (observed `no submitted R1 physical_pricing_replay_hash/resource_delta_ledger_hash/no_double_counting_ledger_hash`, required `pricing and ledger hashes`)
- `PASS` claim boundary forbids B7 credit before resource-escape acceptance (observed `{'accepted_occurrence_removal': 0, 'accepted_proxy_t_reduction': 0, 'b7_ledger_improvement_claimed': False, 'b7_space_time_volume_credit': 0, 'resource_saving_claimed': False}`, required `zero credit until accepted`)

## Quantified Gap

- Remaining line1381 off-grid parameters to eliminate: `5`
- Current line1381 unpriced proxy-T pressure: `100`
- Physical cost-minus-credit: `365`
- Improvement needed to reach cost-minus-credit <= 0: `365`
- Accepted route count / occurrence removal / proxy-T reduction / B7 credit: `0` / `0` / `0` / `0`

## Next Atomic Work Order

- Produce a submitted R1 artifact that reduces line1381 off-grid parameter count from 5 to 0, then attach full replay or symbolic equivalence and ledgers.
- Or produce a physical-pricing replay that improves cost-minus-credit by at least 365 while preserving no-double-counting and zero-credit claim boundaries before acceptance.
- Or submit a checked negative lemma proving R1 should be abandoned and R5 rerun against R2/R3/R4.

## Requirement Results

- `P1` PASS: R7 contract gate is current and passed
- `P2` PASS: Existing evidence source files are hash-readable
- `P3` PASS: Route A preflight is evaluated against the five-parameter exact repair evidence
- `P4` PASS: Route A remains rejected because five off-grid line1381 parameters remain
- `P5` PASS: Route B preflight is evaluated against honest physical-pricing evidence
- `P6` PASS: Route B remains rejected because cost-minus-credit is positive
- `P7` PASS: No R1 accepted-route, resource, or B7 credit is created by preflight
- `P8` PASS: Preflight quantifies the next technical gap
- `P9` PASS: Preflight remains a rejection, not a negative impossibility lemma

## Claim Boundary

- Supported: R8 preflights existing line1381 evidence against the R7 contract and rejects both acceptance routes with quantified blockers.
- Not supported: No submitted R1 artifact, accepted R1 route, line1381 parameter elimination, physical-pricing win, occurrence removal, proxy-T reduction, B7 credit, resource saving, or negative impossibility lemma is supported.
- Next gate: Either eliminate the remaining five line1381 off-grid parameters with submitted replay/symbolic-equivalence and ledgers, improve physical cost-minus-credit by at least 365, or submit a checked negative lemma to reroute R5.

This preflight gate does not claim resource saving, occurrence removal, proxy-T reduction, B7 ledger improvement, FT resource credit, a negative impossibility theorem, or a solved B1/B7 problem.

## Validation

- validation_error_count: `0`
