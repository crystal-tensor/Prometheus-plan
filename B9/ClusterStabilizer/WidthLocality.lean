import Mathlib.Data.Real.Basic

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
    (hRaw : RawGapAmplifies before after)
    (hInvariant : NormalizedGapInvariant before after) :
    ¬ (after.normalizedGap > before.normalizedGap) := by
  intro hImp
  rw [hInvariant] at hImp
  exact (lt_irrefl before.normalizedGap) hImp

theorem cluster_stabilizer_open_uniform_reweight_obligation
    (n : Nat)
    (hN : 4 <= n)
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

theorem uniform_scale_preserves_normalized_gap
    (gap width scale : Real)
    (before after : SpectralSummary)
    (hBefore : before.normalizedGap = gap / width)
    (hAfter : after.normalizedGap = (scale * gap) / (scale * width))
    (hRatio : (scale * gap) / (scale * width) = gap / width) :
    ClusterStabilizer.NormalizedGapInvariant before after := by
  unfold ClusterStabilizer.NormalizedGapInvariant
  rw [hAfter, hBefore, hRatio]

end UniformScaling

section SpectralWidth

def SpectralWidthPreserved (before after : SpectralSummary) : Prop :=
  after.width / after.gap = before.width / before.gap

theorem uniform_scale_preserves_spectral_width_ratio
    (before after : SpectralSummary)
    (hScale : IsUniformlyScaled before after)
    (hRatio : (UniformScaleFactor * before.width) / (UniformScaleFactor * before.gap) = before.width / before.gap) :
    SpectralWidthPreserved before after := by
  rcases hScale with ⟨hGap, hWidth⟩
  unfold SpectralWidthPreserved
  rw [hGap, hWidth]
  exact hRatio

end SpectralWidth

end B9
