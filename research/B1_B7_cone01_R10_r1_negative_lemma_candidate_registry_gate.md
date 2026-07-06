# B1/B7 Cone01 R10 R1 Negative-Lemma Candidate Registry Gate

- Target: `T-B1-004dl/T-B7-012u`
- Method: `b1_b7_cone01_r10_r1_negative_lemma_candidate_registry_gate_v0`
- Status: `cone01_r10_negative_lemma_candidate_registry_ready_no_checked_lemma`
- Registry: `B1-B7-cone01-R10-R1-negative-lemma-candidate-registry`
- Registry hash: `c58910245e32ab5738959a711de1e903951a59dc96cfe9ee390b5c514c7fbf54`
- R9 pressure hash: `6d91bce5a09c4407ef9d7bcac0a81a5983c186dc23b3c98edb1a91b4a4ef4505`

## Result

The R10 registry gate passes 10/10 requirements. It converts R9 pressure into falsifiable negative-lemma candidates, but does not claim that any candidate has been checked.

## Candidate Negative Lemmas

### NL-C01 - Route-contract rejection lemma candidate

- Pressure family: `contract_preflight`
- Covered domain: The current R1 contract routes A and B under the R7 submission contract and R8 preflight predicates.
- Falsification tests: `3`
- Acceptance conditions: `3`

### NL-C02 - Leave-out parameter elimination lemma candidate

- Pressure family: `parameter_removal`
- Covered domain: All nonempty leave-out subsets of the five current line1381 off-grid parameters covered by R9 leave-out pressure.
- Falsification tests: `3`
- Acceptance conditions: `3`

### NL-C03 - Bounded context absorption lemma candidate

- Pressure family: `context_absorption`
- Covered domain: Signed-grid context absorption attempts for widths 1 through 5 over the current line1381 parameter domain.
- Falsification tests: `3`
- Acceptance conditions: `3`

### NL-C04 - Commutation-corridor replay lemma candidate

- Pressure family: `commutation_corridor`
- Covered domain: Best-context replay candidates under the current commutation-corridor references.
- Falsification tests: `3`
- Acceptance conditions: `3`

### NL-C05 - Physical Route-B deficit lemma candidate

- Pressure family: `physical_pricing`
- Covered domain: Current physical-pricing ledger used by R8/R9 for Route B.
- Falsification tests: `3`
- Acceptance conditions: `3`

## External PR Packets

- `R10-PR01` Formalize the covered R1 domain (Theory Agent): machine-readable domain manifest plus human-readable scope note
- `R10-PR02` Independently replay the R9 source hashes (Audit Agent): replay transcript binding R8/R9 hashes and source paths
- `R10-PR03` Write a proof skeleton for one candidate (Formal Methods Agent): checked or checkable proof skeleton with open obligations
- `R10-PR04` Attack the candidates with a route-clearing artifact (Compiler Agent): R1 artifact attempting to clear Route A or Route B
- `R10-PR05` Build the negative-lemma acceptance packet (Maintainer Agent): acceptance packet separating candidate, checked lemma, and reroute decision

## Decision

- Checked negative lemma present: `False`
- Reroute allowed: `False`
- R5 reroute authorized: `False`

## Requirement Results

- `C1` PASS: R9 pressure is validation-clean and still blocks reroute
- `C2` PASS: Registry contains five candidate negative lemmas
- `C3` PASS: Candidates cover contract, parameter, context, commutation, and physical pressure families
- `C4` PASS: Every candidate is falsifiable
- `C5` PASS: Every candidate has acceptance conditions
- `C6` PASS: Registry binds R8, R9, and R9 report source hashes
- `C7` PASS: External PR packets separate theory, audit, compiler, formal, and maintainer work
- `C8` PASS: Registry explicitly refuses to upgrade candidates into checked lemmas
- `C9` PASS: Registry preserves zero resource and B7 credit claims
- `C10` PASS: Next gate is a checked lemma or an R1 Route A/B clearing artifact

## Claim Boundary

- Supported: R10 turns R9 reroute pressure into five falsifiable negative-lemma candidates and five external PR packets.
- Not supported: No candidate is a checked negative lemma. No R5 reroute, R1 solution, occurrence removal, proxy-T reduction, B7 credit, resource saving, or impossibility theorem is supported.
- Next gate: Submit a checked negative lemma artifact for at least one candidate, or falsify the registry by clearing R8 Route A or Route B.

This registry gate does not claim resource saving, occurrence removal, proxy-T reduction, B7 ledger improvement, FT resource credit, a checked impossibility theorem, an R5 reroute, or a solved B1/B7 problem.

## Validation

- validation_error_count: `0`
