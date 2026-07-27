import Mathlib

namespace B9

structure SpectralSummary where
  gap : Real
  width : Real
  normalizedGap : Real
  locality : Nat

section ClusterStabilizer
namespace ClusterStabilizer

def RawGapAmplifies (before after : SpectralSummary) : Prop :=
  after.gap > before.gap

def NormalizedGapInvariant (before after : SpectralSummary) : Prop :=
  after.normalizedGap = before.normalizedGap

def LocalityPreserved (before after : SpectralSummary) : Prop :=
  after.locality = before.locality

theorem uniform_scale_raw_gap_is_not_certificate
    (before after : SpectralSummary)
    (_hRaw : RawGapAmplifies before after)
    (hInvariant : NormalizedGapInvariant before after) :
    ¬ (after.normalizedGap > before.normalizedGap) := by
  intro hImp
  rw [hInvariant] at hImp
  exact (lt_irrefl before.normalizedGap) hImp

theorem cluster_stabilizer_open_uniform_reweight_obligation
    (n : Nat)
    (_hN : 4 <= n)
    (before after : SpectralSummary)
    (hLocality : LocalityPreserved before after)
    (hRaw : RawGapAmplifies before after)
    (hInvariant : NormalizedGapInvariant before after) :
    after.locality = before.locality ∧
      ¬ (after.normalizedGap > before.normalizedGap) := by
  constructor
  . exact hLocality
  . exact uniform_scale_raw_gap_is_not_certificate before after hRaw hInvariant

end ClusterStabilizer

end ClusterStabilizer

open ClusterStabilizer

section SupportSize

def HasSupportSize (summary : SpectralSummary) : Prop :=
  summary.locality = 2 ∨ summary.locality = 3

theorem locality_in_support_set (summary : SpectralSummary) (hLoc : HasSupportSize summary) :
    summary.locality = 2 ∨ summary.locality = 3 := hLoc

def MaxLocalityPreserved (before after : SpectralSummary) : Prop :=
  after.locality <= before.locality

theorem uniform_scale_preserves_max_locality
    (before after : SpectralSummary)
    (hLoc : LocalityPreserved before after) :
    MaxLocalityPreserved before after := by
  unfold MaxLocalityPreserved
  rw [hLoc]

end SupportSize

section UniformScaling

noncomputable def UniformScaleFactor : Real := 27/20

def IsUniformlyScaled (before after : SpectralSummary) : Prop :=
  after.gap = UniformScaleFactor * before.gap ∧
  after.width = UniformScaleFactor * before.width

theorem uniform_scale_factor_nonzero : UniformScaleFactor ≠ 0 := by
  norm_num [UniformScaleFactor]

theorem uniform_scale_factor_gt_one : 1 < UniformScaleFactor := by
  change (1 : Real) < 27 / 20
  apply (lt_div_iff (by norm_num : (0 : Real) < 20)).2
  norm_num

noncomputable def ComputedNormalizedGap (summary : SpectralSummary) : Real :=
  summary.gap / summary.width

def ComputedNormalizedGapInvariant (before after : SpectralSummary) : Prop :=
  ComputedNormalizedGap after = ComputedNormalizedGap before

theorem uniform_scale_preserves_computed_normalized_gap
    (before after : SpectralSummary)
    (hScale : IsUniformlyScaled before after) :
    ComputedNormalizedGapInvariant before after := by
  rcases hScale with ⟨hGap, hWidth⟩
  unfold ComputedNormalizedGapInvariant ComputedNormalizedGap
  rw [hGap, hWidth]
  exact mul_div_mul_left before.gap before.width uniform_scale_factor_nonzero

theorem uniform_scale_raw_gap_amplifies_from_positive_gap
    (before after : SpectralSummary)
    (hScale : IsUniformlyScaled before after)
    (hPositiveGap : 0 < before.gap) :
    ClusterStabilizer.RawGapAmplifies before after := by
  rcases hScale with ⟨hGap, _hWidth⟩
  unfold ClusterStabilizer.RawGapAmplifies
  rw [hGap]
  simpa using mul_lt_mul_of_pos_right uniform_scale_factor_gt_one hPositiveGap

end UniformScaling

section SpectralWidth

def SpectralWidthPreserved (before after : SpectralSummary) : Prop :=
  after.width / after.gap = before.width / before.gap

theorem uniform_scale_preserves_spectral_width_ratio
    (before after : SpectralSummary)
    (hScale : IsUniformlyScaled before after) :
    SpectralWidthPreserved before after := by
  rcases hScale with ⟨hGap, hWidth⟩
  unfold SpectralWidthPreserved
  rw [hGap, hWidth]
  exact mul_div_mul_left before.width before.gap uniform_scale_factor_nonzero

end SpectralWidth

section DerivedCertificate

theorem uniform_reweight_derived_rejection
    (before after : SpectralSummary)
    (hScale : IsUniformlyScaled before after)
    (hLocality : ClusterStabilizer.LocalityPreserved before after)
    (hPositiveGap : 0 < before.gap) :
    ClusterStabilizer.LocalityPreserved before after ∧
      ClusterStabilizer.RawGapAmplifies before after ∧
      ComputedNormalizedGapInvariant before after ∧
      SpectralWidthPreserved before after ∧
      ¬ (ComputedNormalizedGap after > ComputedNormalizedGap before) := by
  have hRaw :=
    uniform_scale_raw_gap_amplifies_from_positive_gap before after hScale hPositiveGap
  have hNormalized :=
    uniform_scale_preserves_computed_normalized_gap before after hScale
  have hWidth :=
    uniform_scale_preserves_spectral_width_ratio before after hScale
  refine ⟨hLocality, hRaw, hNormalized, hWidth, ?_⟩
  intro hImproves
  unfold ComputedNormalizedGapInvariant at hNormalized
  rw [hNormalized] at hImproves
  exact (lt_irrefl (ComputedNormalizedGap before)) hImproves

end DerivedCertificate

end B9
