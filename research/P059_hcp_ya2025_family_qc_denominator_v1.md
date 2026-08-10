# P059 HCP-YA 2025 subject-family/QC manifest and nuisance-only denominator v1

**Decision:** `hcp_ya2025_public_contract_ready_execution_blocked_by_registered_data_access_restricted_family_fields_and_current_processed_roster`.

## Can a connectome predict cognition after its easiest shortcuts are removed?

The #059 activation gate is now executable as a contract but not as a participant analysis. The frozen target is `CogFluidComp_Unadj`, the NIH Toolbox Fluid Cognition Composite on its unadjusted scale. Exact age, gender, and education enter the nuisance denominator instead of hiding age adjustment inside the outcome.

The official 2025 release reports **1,071 processed subjects**, including **45 processed retest subjects**, **1,113 subjects with imaging**, and **1,206 with phenotypic data**. Those are release counts, not an eligible cohort. The primary cohort still requires all four resting-state runs, the current cleaned product, both mean motion files per run, resolved family membership, allowed QC state, anatomy fields, and a complete outcome.

## What must be beaten before one edge can count?

The nuisance-only denominator contains:

- restricted exact age, gender, and education;
- per-run mean absolute and relative RMS motion, four-run availability, and across-run summaries;
- fMRI reconstruction version, resting-state completeness, and separate QC A-E indicators; and
- intracranial volume plus all **68** bilateral FreeSurfer regional cortical-thickness fields.

No functional-connectivity edge, subject ID, family ID, retest-derived feature, or test-family outcome may enter this denominator. Both the nuisance model and the nuisance-plus-connectome model use ridge regression; every imputation, scaling, threshold, and penalty is fit inside training families only.

## Which connectome is actually frozen?

The feature source is the 2025 product `rfMRI_REST_Atlas_MSMAll_hp2000_clean_rclean_tclean.dtseries.nii`, not the 2017 S1200 processing. Official Appendix III exposes the combined file, all four run-specific files, and `Movement_AbsoluteRMS_mean.txt` plus `Movement_RelativeRMS_mean.txt` for each run.

The candidate averages time series within the HCP-MMP1.0 atlas, which has **180 cortical areas per hemisphere**. It then concatenates run-wise demeaned data, computes Pearson correlations, and applies Fisher z, producing **360 choose 2 = 64,620** undirected edges. The 2025 release explicitly warns against mixing its processing with S1200 2017.

## Family structure is a split key, not a nuisance label

`Family_ID` groups biological siblings sharing at least one parent; HCP explicitly warns that it does not establish a shared rearing environment. `Mother_ID`, `Father_ID`, `HasGT`, and `ZygosityGT` remain verification fields. Family structure and exact age require restricted approval.

Every `Family_ID` is assigned deterministically to a 70/15/15 train/validation/test partition. Missing or unresolved family IDs are rejected; they are never converted into synthetic singletons. Retest participants are excluded from primary cognition prediction and used only for reliability.

## Why 46 is not 45

The public 2017 retest interval CSV contains **46 unique subjects**, with month-bin counts `{"11": 3, "2": 5, "3": 9, "4": 6, "5": 14, "6": 4, "7": 3, "8": 2}`. The separate BALSA retest project also says 46 subjects were retested. The 2025 release, however, exposes only **45 processed retest subjects** meeting its processing condition. The exact current 45-of-46 crosswalk is not established by the unauthenticated public evidence, so the legacy roster cannot be silently reused.

## QC codes are not a clean-bill field

The S1200 QC page reports 157 imaging subjects with one or more A-E codes and warns that absence of a code does not imply absence of an issue. It also says fMRI and dMRI were only very rarely excluded for motion.

The primary manifest excludes A (focal anatomical anomaly), B (segmentation/surface error), and C (head-coil instability). D and E may remain only when the frozen 2025 cleaned product is present, with their indicators retained in the nuisance denominator. A sensitivity replay drops every A-E-coded subject. Reconstruction versions `r177` and `r227` are also retained because HCP documents a notable fMRI signature.

## The falsifiable gate

The primary statistic is `delta_mae = MAE(nuisance-only) - MAE(nuisance-plus-connectome)` on untouched test families. It passes only if the family-clustered 95% bootstrap interval has a lower bound above zero.

Two reliability checks must also pass: median edgewise ICC(2,1) across the current test/retest cohort must be at least **0.40**, and the family-clustered lower bound for within-subject minus between-subject connectome similarity must exceed zero. The 0.40 threshold is a preregistered engineering floor, not a clinical standard.

A motion-matched replay may use motion, run availability, reconstruction version, and QC only—never cognition or connectivity. Its `delta_mae` interval must remain above zero and its point estimate must retain at least 80% of the primary gain.

## What is and is not ready

The formal parser passes **37/37** checks over **15** hash-bound official snapshots. The public contract is ready. Execution remains blocked by registered imaging access, approved restricted family/demographic access, and reconstruction of the exact current processed roster. No participant row, image, connectome, cognition outcome, model, diagnosis, identity inference, causal cognition, clinical-utility, or solved-frontier claim is produced.

## Official sources

- [HCP-YA 2025 release](https://www.humanconnectome.org/study/hcp-young-adult/document/hcp-young-adult-2025-release)
- [HCP-YA data releases](https://humanconnectome.org/study/hcp-young-adult/data-releases)
- [HCP-YA data dictionary CSV](https://wiki.humanconnectome.org/docs/assets/HCP_S1200_DataDictionary_Oct_30_2023.csv)
- [Family-structure and retest update](https://www.humanconnectome.org/study/hcp-young-adult/article/s1200-family-structure-test-retest-interval-updates)
- [HCP-YA QC issue codes](https://wiki.humanconnectome.org/docs/HCP%20Subjects%20with%20Identified%20Quality%20Control%20Issues%20%28QC_Issue%20measure%20codes%20explained%29.html)
- [HCP-YA known issues](https://wiki.humanconnectome.org/docs/HCP%20Data%20Release%20Updates%20Known%20Issues%20and%20Planned%20fixes.html)
- [Open and restricted data-use terms](https://www.humanconnectome.org/study/hcp-young-adult/data-use-terms)
- [HCP-MMP1.0 overview](https://humanconnectome.org/study/hcp-young-adult/article/nature-article-cortical-brain-maps-at-the-highest-resolution-to-date)
- [HCP-YA 2025 Appendix III](https://humanconnectome.org/storage/app/media/documentation/HCP-YA2025/HCP-YA_2025_Release_Appendix_III.pdf)
