import B9.ClusterStabilizer.WidthLocality

namespace B9
namespace ClusterStabilizer

structure OpenChainTerm where
  center : Nat
  zSites : Finset Nat
  coefficient : Real

def OpenChainTerm.support (term : OpenChainTerm) : Finset Nat :=
  insert term.center term.zSites

def openChainZSites (n i : Nat) : Finset Nat :=
  (if i = 0 then ∅ else {i - 1}) ∪
    if i + 1 < n then {i + 1} else ∅

def openChainTerm (n i : Nat) : OpenChainTerm where
  center := i
  zSites := openChainZSites n i
  coefficient := -1

def openChainSupport (n i : Nat) : Finset Nat :=
  (openChainTerm n i).support

def OpenChainHamiltonian (n : Nat) :=
  Fin n → OpenChainTerm

def openChainHamiltonian (n : Nat) : OpenChainHamiltonian n :=
  fun i => openChainTerm n i

theorem open_chain_term_count (n : Nat) :
    Fintype.card (Fin n) = n := by
  simp

theorem open_chain_support_subset_range
    (n i : Nat)
    (hIndex : i < n) :
    openChainSupport n i ⊆ Finset.range n := by
  intro q hq
  unfold openChainSupport OpenChainTerm.support openChainTerm openChainZSites at hq
  split_ifs at hq <;> simp at hq
  all_goals simp
  all_goals omega

theorem open_chain_support_card_le_three (n i : Nat) :
    (openChainSupport n i).card ≤ 3 := by
  change (
    insert i (
      (if i = 0 then (∅ : Finset Nat) else {i - 1}) ∪
        if i + 1 < n then {i + 1} else (∅ : Finset Nat)
    )
  ).card ≤ 3
  have hLeft :
      (if i = 0 then ∅ else ({i - 1} : Finset Nat)).card ≤ 1 := by
    split_ifs <;> simp
  have hRight :
      (if i + 1 < n then ({i + 1} : Finset Nat) else ∅).card ≤ 1 := by
    split_ifs <;> simp
  calc
    (insert i (
      (if i = 0 then (∅ : Finset Nat) else {i - 1}) ∪
        if i + 1 < n then {i + 1} else (∅ : Finset Nat)
    )).card ≤ (
      (if i = 0 then (∅ : Finset Nat) else {i - 1}) ∪
        if i + 1 < n then {i + 1} else (∅ : Finset Nat)
    ).card + 1 := Finset.card_insert_le _ _
    _ ≤ (
      (if i = 0 then ∅ else {i - 1} : Finset Nat).card +
        (if i + 1 < n then {i + 1} else ∅ : Finset Nat).card
    ) + 1 := Nat.add_le_add_right (Finset.card_union_le _ _) 1
    _ ≤ 3 := by omega

theorem open_chain_left_boundary_support
    (n : Nat)
    (hN : 2 ≤ n) :
    openChainSupport n 0 = {0, 1} := by
  have hRight : 1 < n := by omega
  simp [openChainSupport, OpenChainTerm.support, openChainTerm, openChainZSites, hRight]

theorem open_chain_interior_support
    (n i : Nat)
    (hLeft : 0 < i)
    (hRight : i + 1 < n) :
    openChainSupport n i = {i - 1, i, i + 1} := by
  ext q
  have hNonzero : i ≠ 0 := by omega
  simp [
    openChainSupport,
    OpenChainTerm.support,
    openChainTerm,
    openChainZSites,
    hNonzero,
    hRight
  ]
  tauto

theorem open_chain_right_boundary_support
    (n : Nat)
    (hN : 2 ≤ n) :
    openChainSupport n (n - 1) = {n - 2, n - 1} := by
  ext q
  have hNonzero : n - 1 ≠ 0 := by omega
  have hNoRight : ¬ (n - 1 + 1 < n) := by omega
  simp [
    openChainSupport,
    OpenChainTerm.support,
    openChainTerm,
    openChainZSites,
    hNonzero,
    hNoRight
  ]
  tauto

theorem open_chain_interior_one_attains_three
    (n : Nat)
    (hN : 4 ≤ n) :
    (openChainSupport n 1).card = 3 := by
  rw [open_chain_interior_support n 1 (by omega) (by omega)]
  norm_num

def openChainSupportCardProfile (n : Nat) : List Nat :=
  (List.range n).map fun i => (openChainSupport n i).card

theorem open_chain_support_card_profile_length (n : Nat) :
    (openChainSupportCardProfile n).length = n := by
  simp [openChainSupportCardProfile]

noncomputable def reweightOpenChainTerm (term : OpenChainTerm) : OpenChainTerm where
  center := term.center
  zSites := term.zSites
  coefficient := B9.UniformScaleFactor * term.coefficient

noncomputable def reweightedOpenChainHamiltonian (n : Nat) : OpenChainHamiltonian n :=
  fun i => reweightOpenChainTerm (openChainHamiltonian n i)

@[simp] theorem reweight_open_chain_term_support (term : OpenChainTerm) :
    (reweightOpenChainTerm term).support = term.support := by
  rfl

theorem open_chain_reweight_preserves_every_support
    (n : Nat)
    (i : Fin n) :
    (reweightedOpenChainHamiltonian n i).support =
      (openChainHamiltonian n i).support := by
  rfl

noncomputable def openChainBeforeSummary
    (_n : Nat)
    (gap width : Real) :
    SpectralSummary where
  gap := gap
  width := width
  normalizedGap := gap / width
  locality := 3

noncomputable def openChainAfterSummary
    (_n : Nat)
    (gap width : Real) :
    SpectralSummary where
  gap := B9.UniformScaleFactor * gap
  width := B9.UniformScaleFactor * width
  normalizedGap :=
    (B9.UniformScaleFactor * gap) / (B9.UniformScaleFactor * width)
  locality := 3

theorem open_chain_summaries_are_uniformly_scaled
    (n : Nat)
    (gap width : Real) :
    B9.IsUniformlyScaled
      (openChainBeforeSummary n gap width)
      (openChainAfterSummary n gap width) := by
  exact ⟨rfl, rfl⟩

theorem open_chain_summaries_preserve_locality
    (n : Nat)
    (gap width : Real) :
    LocalityPreserved
      (openChainBeforeSummary n gap width)
      (openChainAfterSummary n gap width) := by
  rfl

theorem open_chain_uniform_reweight_instantiates_r187
    (n : Nat)
    (hN : 4 ≤ n)
    (gap width : Real)
    (hPositiveGap : 0 < gap) :
    (∀ i : Fin n, (openChainSupport n i).card ≤ 3) ∧
      (∃ i : Fin n, (openChainSupport n i).card = 3) ∧
      LocalityPreserved
        (openChainBeforeSummary n gap width)
        (openChainAfterSummary n gap width) ∧
      RawGapAmplifies
        (openChainBeforeSummary n gap width)
        (openChainAfterSummary n gap width) ∧
      B9.ComputedNormalizedGapInvariant
        (openChainBeforeSummary n gap width)
        (openChainAfterSummary n gap width) ∧
      B9.SpectralWidthPreserved
        (openChainBeforeSummary n gap width)
        (openChainAfterSummary n gap width) ∧
      ¬ (
        B9.ComputedNormalizedGap (openChainAfterSummary n gap width) >
          B9.ComputedNormalizedGap (openChainBeforeSummary n gap width)
      ) := by
  have hDerived :=
    B9.uniform_reweight_derived_rejection
      (openChainBeforeSummary n gap width)
      (openChainAfterSummary n gap width)
      (open_chain_summaries_are_uniformly_scaled n gap width)
      (open_chain_summaries_preserve_locality n gap width)
      (by simpa [openChainBeforeSummary] using hPositiveGap)
  refine ⟨?_, ?_, hDerived⟩
  . intro i
    exact open_chain_support_card_le_three n i
  . have hOne : 1 < n := by omega
    refine ⟨⟨1, hOne⟩, ?_⟩
    exact open_chain_interior_one_attains_three n hN

#eval IO.println (
  "R188_PROFILE n=4 support_cards=" ++ reprStr (openChainSupportCardProfile 4)
)
#eval IO.println (
  "R188_PROFILE n=5 support_cards=" ++ reprStr (openChainSupportCardProfile 5)
)
#eval IO.println (
  "R188_PROFILE n=6 support_cards=" ++ reprStr (openChainSupportCardProfile 6)
)

end ClusterStabilizer
end B9
