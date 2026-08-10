# P056 ImmPort study shortlist and completeness audit v1

**Decision:** `immport_public_shortlist_ready_activation_blocked_by_authenticated_subject_intervention_visit_and_adverse_event_detail`.

## Can immune control be separated from immune toxicity?

The first #056 experiment is now narrower than “programmable immunity.” It asks whether one perturbation study can support donor-held-out prediction of a target immune-cell state while keeping three guardrails separate: cytokines, off-target cell states, and adverse events. Every layer must belong to the same donor and study. A safety signal from one study may not repair a missing safety layer in another.

The unauthenticated ImmPort directory yields two public shortlist candidates. Neither is activation-ready.

| Study | Public perturbation structure | Planned visits | Positive public assay-result counts | Public-screen decision |
|---|---|---:|---|---|
| `SDY113` | LAIV, TIV, and intradermal TIV arms | 3 | CyTOF 61; Flow Cytometry 358; ELISA 60; Luminex xMAP 374 | shortlisted; authenticated detail required |
| `SDY180` | saline, Pneunomax23, and 2009–2010 Fluzone arms | 17 | Flow Cytometry 2,208; Luminex xMAP 229 | shortlisted; authenticated detail required |

The directory identifies `SDY113` as a human clinical trial with 70 enrolled participants and `SDY180` as a human perturbation study with 46 enrolled participants. Those are study-level metadata, not eligible donor counts.

## Seven layers must meet inside one donor

| Required layer | `SDY113` | `SDY180` | Why it does or does not count |
|---|---|---|---|
| stable donor key | unavailable authenticated detail | unavailable authenticated detail | Study and arm accessions are not donor keys; demographic and biosample API probes return HTTP 401. |
| intervention and dose | partial public detail locked | partial public detail locked | Arm labels establish contrasts, but not per-subject identity, route, timing, or dose. |
| baseline-response link | partial public detail locked | partial public detail locked | Planned-visit counts are public; actual same-donor times are not. |
| target-cell-state assay layer | confirmed public | confirmed public | Each study has a positive Flow Cytometry or CyTOF result count; the exact target phenotype remains unopened. |
| cytokine guardrail assay layer | confirmed public | confirmed public | Each study has a positive Luminex/ELISA result count; the exact cytokine panel remains unopened. |
| off-target-cell-state assay layer | confirmed public | confirmed public | Cytometry exists, but a phenotype distinct from the target must still be frozen. |
| adverse-event guardrail | unavailable authenticated detail | unavailable authenticated detail | Same-study adverseEvent API probes return HTTP 401; unavailable never means no adverse event. |

Each candidate therefore has `3/7` publicly confirmed assay layers, `2/7` study-level partial layers, and `2/7` authenticated-detail layers that remain unavailable in this capture. The word “confirmed” applies only to a positive public assay-result layer, not to an eligible donor cohort or a frozen biomarker panel.

ImmPort documents subject-linked adverse-event fields including accession, causality, severity, relation to study treatment, and study-day timing. Those are exactly the fields needed by the gate, but the documented study-detail API requires an authentication/authorization token. All ten unauthenticated probes across `demographic`, `biosample`, `intervention`, `plannedVisit`, and `adverseEvent` for the two shortlisted studies returned HTTP `401`.

## Two attractive shortcuts are rejected

`SDY1058` compares H5N1 vaccine with and without AS03 across 12 planned visits and reports 487 Luminex results. Yet its public directory snapshot lists both Flow Cytometry and CyTOF with result counts of `0`. An assay method name cannot substitute for a positive result row, so the study fails the public cell-state screen.

`SDY1439` explicitly mentions clinical adverse events in its title and has six planned visits, but its public assay list contains neither qualifying cytometry nor cytokine assay methods. Its safety language cannot be joined to `SDY113` or `SDY180`. Cross-study borrowing is forbidden.

## Why the model remains unopened

No outcome, donor row, target phenotype, cytokine threshold, off-target phenotype, or adverse-event label was opened. Study-level arm labels and visit counts cannot establish a same-donor baseline-response pair. Positive assay counts cannot establish that those assays overlap on the same people or visits. An HTTP 401 is an access state, not missingness and never evidence of safety.

The formal capture passes `30/30` checks over `20` hash-bound official snapshots. A separate standard-library parser passes `15/15` checks and independently reconstructs the candidate records, assay counts, ten authenticated-detail boundaries, seven-layer matrices, rejections, and final decision. A no-network replay reproduces the result byte-for-byte.

## Next falsifier

After lawful authenticated access, reconstruct the seven-layer matrix for `SDY113` first. Before any outcome is opened:

1. prove one stable donor key links intervention, dose/route/timing, actual baseline and response visits, cytometry, cytokines, and adverse events;
2. freeze one target phenotype, one distinct off-target phenotype panel, and one cytokine panel;
3. enumerate complete donors and missingness reasons without crossing study boundaries; and
4. reject the study if any retained donor lacks an intervention/dose, actual baseline-response pair, or adverse-event linkage.

Only after that may a no-treatment or standard-treatment denominator and a linear dose-response denominator be fit under donor- and study-level holdouts. No cell from one donor may cross the split.

## Official sources

- [ImmPort Search API documentation](https://docs.immport.org/apidocumentation/shareddataapi/search/)
- [ImmPort study-detail API documentation](https://docs.immport.org/apidocumentation/shareddataapi/study/)
- [ImmPort data-model overview](https://docs.immport.org/datamodel/)
- [ImmPort adverse-event table](https://docs.immport.org/datamodel/adverse_event/)
- [ImmPort registration guidance](https://docs.immport.org/help/user-registration/)
- [ImmPort download guidance](https://docs.immport.org/download/)

Retrospective metadata and data-readiness research only. No dose, vaccine, immunotherapy, clinical-control, treatment, efficacy, safety, toxicity, clinical-utility, regulatory, or solved-frontier claim is made.
