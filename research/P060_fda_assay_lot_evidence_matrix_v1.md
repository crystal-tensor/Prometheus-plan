# P060 FDA assay-and-lot evidence matrix v1

**Decision:** `fda_guidance_evidence_matrix_ready_protocol_activation_blocked_by_product_specific_assays_thresholds_lot_data_and_blinded_lab_execution`.

## Can a high on-target number still be a failed editing result?

Yes. The #060 gate now treats on-target correction as one row in a 15-row evidence matrix, not as a safety verdict. The matrix maps the January 2024 FDA final genome-editing guidance, the April 2026 NGS safety draft, and the June 2026 prior-knowledge draft into a protocol-only failure system.

The two 2026 documents are explicitly **draft, not for implementation**, and contain non-binding recommendations. This packet therefore does not convert draft wording into law, approval criteria, or a claim of FDA compliance.

## One abstract product class, no executable edit

The frozen label `P060-EXV-DSB-01` means only a conceptual ex vivo autologous human somatic-cell product using a single-locus nuclease-dependent double-strand-break editor with transient non-integrating delivery. The target, sequence, guide, editor identity, disease, dose, culture conditions, delivery recipe, and wet-lab procedure are intentionally withheld.

That abstract class is enough to trigger long-read assessment of larger unintended on-target changes, multi-method off-target nomination, independent confirmation, human-variation analysis, and chromosomal-translocation testing without publishing an operational editing protocol.

## Fifteen rows that cannot be averaged away

| ID | Evidence domain | FDA anchor | What must be frozen before results |
|---|---|---|---|
| `E01` | product and component identity | 2024 final, 2026 prior-knowledge draft | `product_specific_acceptance_criteria_required_before_results` |
| `E02` | manufacturing lot release | 2024 final, 2026 prior-knowledge draft | `lot_specific_release_specifications_required_before_results` |
| `E03` | functional potency | 2024 final | `functional_correction_and_noninferiority_margins_required_before_results` |
| `E04` | on-target intended and unintended outcomes | 2024 final, 2026 NGS draft | `depth_quality_and_edit_rate_criteria_required_before_results` |
| `E05` | off-target nomination | 2024 final, 2026 NGS draft | `nomination_parameters_and_candidate_union_rule_required_before_results` |
| `E06` | off-target confirmation | 2024 final, 2026 NGS draft | `sensitivity_filtering_and_subset_rules_required_before_nomination_results` |
| `E07` | human genetic variation | 2026 NGS draft | `database_population_and_frequency_rules_required_before_results` |
| `E08` | chromosomal integrity | 2024 final, 2026 NGS draft | `event_definition_detection_and_noninferiority_rules_required_before_results` |
| `E09` | residual editor and persistence | 2024 final, 2026 prior-knowledge draft | `residual_and_persistence_limits_required_before_results` |
| `E10` | viability and cell function | 2024 final, 2026 prior-knowledge draft | `viability_and_function_noninferiority_margins_required_before_results` |
| `E11` | immunogenicity | 2024 final | `assay_and_acceptance_criteria_required_before_results` |
| `E12` | oncogenicity and clonal behavior | 2024 final | `observation_window_and_event_rules_required_before_results` |
| `E13` | stability | 2024 final, 2026 prior-knowledge draft | `timepoints_trends_and_acceptance_criteria_required_before_results` |
| `E14` | scale change and comparability | 2024 final, 2026 prior-knowledge draft | `quality_attribute_specific_equivalence_or_noninferiority_margins_required_before_results` |
| `E15` | long-term follow-up trigger | 2024 final | `trigger_duration_and_reporting_plan_required_before_clinical_promotion` |

Every row must have its assay, input, sensitivity, quality/depth criteria, analysis parameters, categorical or numeric threshold, non-inferiority margin, timepoint, and failure rule frozen before arm labels or outcomes are opened. FDA does not provide one universal number that proves a genome-editing product safe or scalable.

## Four arms, three lots, two blinded laboratories

The four arms are unedited cells, mock delivery, the current standard editor/delivery system, and the candidate. All are assessed at matched assay versions, inputs, sequencing sensitivity, bioinformatics versions, timepoints, and reporting rules.

The internal gate requires three independent manufacturing lots and two blinded confirmation laboratories. These are preregistered engineering floors, **not FDA universal minima**. A single failed safety row in any lot rejects promotion; a mean cannot hide the failure. Off-target nomination is locked before confirmation samples and labels are opened.

## Discovery is not confirmation

The 2024 final guidance recommends multiple off-target methods, including in-silico, biochemical, cellular, and genome-wide analysis, using relevant human cells and multiple donors where possible. The 2026 NGS draft separates nomination from confirmation, recommends multiple biological replicates, warns against stringent filtering, and calls for predetermined sequencing depth and quality capable of evaluating low-frequency events.

The frozen matrix retains the union of nominated sites. Every site must be confirmed, or a subset rule must be scientifically justified and frozen before nomination results. Edited/unedited pairs, read counts, edit frequencies, coordinates, functional context, reference databases, quality/depth/alignment criteria, tools, versions, and command-line records all remain part of the evidence.

## Prior knowledge can transfer a method, not a safety conclusion

The June 2026 draft distinguishes public knowledge from platform knowledge and allows scientifically justified reuse of methods, manufacturing experience, sequencing technology, pipeline structure, and some quality metrics. It also requires applicability justification, sufficiently granular sources, and bridging or confirmatory data as appropriate.

Identity and potency testing remain product-specific. Primary-product long-term real-time stability cannot be replaced by prior knowledge. Comparability must assess each relevant quality attribute, and sequence-specific off-target/genomic-integrity results cannot be borrowed merely because two products look related.

## What is ready—and what is not

The formal parser passes **39/39** checks over **9** hash-bound official-origin text snapshots. The 15-row evidence vocabulary, four arms, lot/lab split, matched-sensitivity rule, prior-knowledge boundary, and fail-closed aggregation are ready.

Product-specific assays, numeric thresholds, lot data, and blinded laboratory confirmation do not exist in this packet. No wet-lab edit, sequence, cell result, product, patient, animal, safety, efficacy, scalability, regulatory, approval, or solved-frontier claim is made.

## Official sources

- [FDA 2024 final guidance page](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/human-gene-therapy-products-incorporating-human-genome-editing)
- [FDA 2024 final guidance PDF](https://www.fda.gov/media/156894/download)
- [FDA 2026 NGS draft page](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/safety-assessment-genome-editing-human-gene-therapy-products-using-next-generation-sequencing)
- [FDA 2026 NGS draft PDF](https://www.fda.gov/media/191966/download)
- [FDA 2026 prior-knowledge draft page](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/leveraging-prior-knowledge-development-human-gene-therapy-products-incorporating-genome-editing)
- [FDA 2026 prior-knowledge draft PDF](https://www.fda.gov/media/192810/download)

Snapshot boundary: the shell transport was redirected to FDA abuse detection, so normalized official-origin text was captured through a relay with explicit origin markers and hashes. No raw-FDA-PDF-byte identity is claimed.
