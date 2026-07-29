import B9.ClusterStabilizer.SpectrumFormula

namespace B9
namespace ClusterStabilizer

noncomputable def pythagoreanFieldStrength : Real := 3 / 4

noncomputable def pythagoreanSpectralScale : Real := 5 / 4

noncomputable def tiltedLocalOperator :
    Matrix (Fin 2) (Fin 2) Complex :=
  (-1 : Complex) • pauliX +
    (pythagoreanFieldStrength : Complex) • pauliZ

def tiltedGroundVector : Fin 2 → Complex :=
  ![1, 2]

def tiltedExcitedVector : Fin 2 → Complex :=
  ![2, -1]

noncomputable def tiltedLocalEigenvalue (label : Fin 2) : Complex :=
  if label = 0 then -(5 / 4 : Complex) else (5 / 4 : Complex)

def tiltedLocalBasisMatrix :
    Matrix (Fin 2) (Fin 2) Complex :=
  !![1, 2; 2, -1]

noncomputable def tiltedLocalBasisInverse :
    Matrix (Fin 2) (Fin 2) Complex :=
  (1 / 5 : Complex) • tiltedLocalBasisMatrix

theorem tiltedLocalOperator_isHermitian :
    tiltedLocalOperator.IsHermitian := by
  apply Matrix.IsHermitian.ext
  intro row column
  fin_cases row <;> fin_cases column <;>
    norm_num [
      tiltedLocalOperator,
      pythagoreanFieldStrength,
      pauliX,
      pauliZ
    ]

theorem tilted_ground_eigenpair :
    Matrix.mulVec tiltedLocalOperator tiltedGroundVector =
      (-(5 / 4 : Complex)) • tiltedGroundVector := by
  funext row
  fin_cases row <;>
    norm_num [
      Matrix.mulVec,
      Matrix.dotProduct,
      tiltedLocalOperator,
      tiltedGroundVector,
      pythagoreanFieldStrength,
      pauliX,
      pauliZ
    ]

theorem tilted_excited_eigenpair :
    Matrix.mulVec tiltedLocalOperator tiltedExcitedVector =
      (5 / 4 : Complex) • tiltedExcitedVector := by
  funext row
  fin_cases row <;>
    norm_num [
      Matrix.mulVec,
      Matrix.dotProduct,
      tiltedLocalOperator,
      tiltedExcitedVector,
      pythagoreanFieldStrength,
      pauliX,
      pauliZ
    ]

theorem tiltedLocalBasis_mul_self :
    tiltedLocalBasisMatrix * tiltedLocalBasisMatrix =
      (5 : Complex) • (1 : Matrix (Fin 2) (Fin 2) Complex) := by
  ext row column
  fin_cases row <;> fin_cases column <;>
    norm_num [
      Matrix.mul_apply,
      Matrix.one_apply,
      tiltedLocalBasisMatrix
    ]

theorem tiltedLocalBasis_mul_inverse :
    tiltedLocalBasisMatrix * tiltedLocalBasisInverse = 1 := by
  rw [
    tiltedLocalBasisInverse,
    Matrix.mul_smul,
    tiltedLocalBasis_mul_self
  ]
  norm_num [smul_smul]

theorem tiltedLocalBasis_inverse_mul :
    tiltedLocalBasisInverse * tiltedLocalBasisMatrix = 1 := by
  rw [
    tiltedLocalBasisInverse,
    Matrix.smul_mul,
    tiltedLocalBasis_mul_self
  ]
  norm_num [smul_smul]

noncomputable def tiltedLocalBasisUnit :
    (Matrix (Fin 2) (Fin 2) Complex)ˣ where
  val := tiltedLocalBasisMatrix
  inv := tiltedLocalBasisInverse
  val_inv := tiltedLocalBasis_mul_inverse
  inv_val := tiltedLocalBasis_inverse_mul

theorem tiltedLocalOperator_mul_basis :
    tiltedLocalOperator * tiltedLocalBasisMatrix =
      tiltedLocalBasisMatrix *
        Matrix.diagonal tiltedLocalEigenvalue := by
  ext row column
  fin_cases row <;> fin_cases column <;>
    norm_num [
      Matrix.mul_apply,
      Matrix.mul_diagonal,
      Matrix.diagonal,
      tiltedLocalOperator,
      tiltedLocalBasisMatrix,
      tiltedLocalEigenvalue,
      pythagoreanFieldStrength,
      pauliX,
      pauliZ
    ]

theorem tiltedLocalBasis_diagonalizes :
    tiltedLocalBasisInverse * tiltedLocalOperator *
        tiltedLocalBasisMatrix =
      Matrix.diagonal tiltedLocalEigenvalue := by
  calc
    tiltedLocalBasisInverse * tiltedLocalOperator *
        tiltedLocalBasisMatrix =
      tiltedLocalBasisInverse *
        (tiltedLocalOperator * tiltedLocalBasisMatrix) := by
          rw [Matrix.mul_assoc]
    _ = tiltedLocalBasisInverse *
        (tiltedLocalBasisMatrix *
          Matrix.diagonal tiltedLocalEigenvalue) := by
            rw [tiltedLocalOperator_mul_basis]
    _ = (tiltedLocalBasisInverse * tiltedLocalBasisMatrix) *
        Matrix.diagonal tiltedLocalEigenvalue := by
          rw [Matrix.mul_assoc]
    _ = Matrix.diagonal tiltedLocalEigenvalue := by
      rw [tiltedLocalBasis_inverse_mul, Matrix.one_mul]

theorem tiltedLocalOperator_spectrum :
    spectrum Complex tiltedLocalOperator =
      Set.range tiltedLocalEigenvalue := by
  let unit := tiltedLocalBasisUnit
  have hDiagonal :
      (↑unit⁻¹ : Matrix (Fin 2) (Fin 2) Complex) *
          tiltedLocalOperator *
          (↑unit : Matrix (Fin 2) (Fin 2) Complex) =
        Matrix.diagonal tiltedLocalEigenvalue := by
    exact tiltedLocalBasis_diagonalizes
  calc
    spectrum Complex tiltedLocalOperator =
        spectrum Complex (
          (↑unit⁻¹ : Matrix (Fin 2) (Fin 2) Complex) *
            tiltedLocalOperator *
            (↑unit : Matrix (Fin 2) (Fin 2) Complex)) := by
      simpa using
        (spectrum.units_conjugate'
          (R := Complex)
          (a := tiltedLocalOperator)
          (u := unit)).symm
    _ = spectrum Complex (Matrix.diagonal tiltedLocalEigenvalue) := by
      rw [hDiagonal]
    _ = Set.range tiltedLocalEigenvalue := by
      exact spectrum_diagonal _

theorem pauliX_does_not_commute_with_tiltedLocalOperator :
    ¬ Commute pauliX tiltedLocalOperator := by
  intro hCommute
  have hEntry :=
    congrFun (congrFun hCommute.eq (0 : Fin 2)) (1 : Fin 2)
  norm_num [
    Matrix.mul_apply,
    tiltedLocalOperator,
    pythagoreanFieldStrength,
    pauliX,
    pauliZ
  ] at hEntry

theorem tiltedLocalOperator_not_scalar_pauliX
    (scale : Complex) :
    tiltedLocalOperator ≠ scale • pauliX := by
  intro hEqual
  have hEntry :=
    congrFun (congrFun hEqual (0 : Fin 2)) (0 : Fin 2)
  norm_num [
    tiltedLocalOperator,
    pythagoreanFieldStrength,
    pauliX,
    pauliZ
  ] at hEntry

structure PythagoreanFieldTerm where
  site : Nat
  coefficient : Real

def PythagoreanFieldTerm.support
    (term : PythagoreanFieldTerm) :
    Finset Nat :=
  {term.site}

noncomputable def pythagoreanFieldTerm
    (site : Nat) :
    PythagoreanFieldTerm where
  site := site
  coefficient := pythagoreanFieldStrength

theorem pythagorean_field_support_card
    (site : Nat) :
    ((pythagoreanFieldTerm site).support).card = 1 := by
  simp [PythagoreanFieldTerm.support]

theorem pythagorean_field_support_subset_range
    (n : Nat)
    (site : Fin n) :
    (pythagoreanFieldTerm site.val).support ⊆ Finset.range n := by
  simp [
    PythagoreanFieldTerm.support,
    pythagoreanFieldTerm,
    site.isLt
  ]

def zFieldSitePauli
    (n : Nat)
    (site q : Fin n) :
    Matrix (Fin 2) (Fin 2) Complex :=
  if q = site then pauliZ else pauliI

def zFieldPauliWord
    (n : Nat)
    (site : Fin n) :
    Matrix (QubitBasis n) (QubitBasis n) Complex :=
  pauliWordMatrix (zFieldSitePauli n site)

noncomputable def zFieldTermOperator
    (n : Nat)
    (site : Fin n) :
    Matrix (QubitBasis n) (QubitBasis n) Complex :=
  (pythagoreanFieldStrength : Complex) •
    zFieldPauliWord n site

noncomputable def zFieldOperator
    (n : Nat) :
    Matrix (QubitBasis n) (QubitBasis n) Complex :=
  ∑ site : Fin n, zFieldTermOperator n site

noncomputable def tiltedProductOperator
    (n : Nat) :
    Matrix (QubitBasis n) (QubitBasis n) Complex :=
  xChainOperator n + zFieldOperator n

noncomputable def integrableClusterControlOperator
    (n : Nat) :
    Matrix (QubitBasis n) (QubitBasis n) Complex :=
  clusterPhaseMatrix n * tiltedProductOperator n *
    clusterPhaseMatrix n

theorem xSitePauli_isHermitian
    (n : Nat)
    (site q : Fin n) :
    (xSitePauli n site q).IsHermitian := by
  unfold xSitePauli
  split_ifs
  · exact pauliX_isHermitian
  · exact pauliI_isHermitian

theorem xPauliWord_isHermitian
    (n : Nat)
    (site : Fin n) :
    (xPauliWord n site).IsHermitian := by
  exact pauliWordMatrix_isHermitian
    (xSitePauli n site)
    (xSitePauli_isHermitian n site)

theorem xChainTermOperator_isHermitian
    (n : Nat)
    (site : Fin n) :
    (xChainTermOperator n site).IsHermitian := by
  simpa [xChainTermOperator] using
    (real_coefficient_smul_isHermitian
      (-1 : Real)
      (xPauliWord n site)
      (xPauliWord_isHermitian n site))

theorem xChainOperator_isHermitian
    (n : Nat) :
    (xChainOperator n).IsHermitian := by
  apply Matrix.IsHermitian.ext
  intro row column
  simp only [xChainOperator, Matrix.sum_apply, star_sum]
  apply Finset.sum_congr rfl
  intro site _
  exact (xChainTermOperator_isHermitian n site).apply row column

theorem zFieldSitePauli_isHermitian
    (n : Nat)
    (site q : Fin n) :
    (zFieldSitePauli n site q).IsHermitian := by
  unfold zFieldSitePauli
  split_ifs
  · exact pauliZ_isHermitian
  · exact pauliI_isHermitian

theorem zFieldPauliWord_isHermitian
    (n : Nat)
    (site : Fin n) :
    (zFieldPauliWord n site).IsHermitian := by
  exact pauliWordMatrix_isHermitian
    (zFieldSitePauli n site)
    (zFieldSitePauli_isHermitian n site)

theorem zFieldTermOperator_isHermitian
    (n : Nat)
    (site : Fin n) :
    (zFieldTermOperator n site).IsHermitian := by
  exact real_coefficient_smul_isHermitian
    pythagoreanFieldStrength
    (zFieldPauliWord n site)
    (zFieldPauliWord_isHermitian n site)

theorem zFieldOperator_isHermitian
    (n : Nat) :
    (zFieldOperator n).IsHermitian := by
  apply Matrix.IsHermitian.ext
  intro row column
  simp only [zFieldOperator, Matrix.sum_apply, star_sum]
  apply Finset.sum_congr rfl
  intro site _
  exact (zFieldTermOperator_isHermitian n site).apply row column

theorem tiltedProductOperator_isHermitian
    (n : Nat) :
    (tiltedProductOperator n).IsHermitian := by
  apply Matrix.IsHermitian.ext
  intro row column
  simp only [tiltedProductOperator, Matrix.add_apply, star_add]
  rw [
    (xChainOperator_isHermitian n).apply row column,
    (zFieldOperator_isHermitian n).apply row column
  ]

noncomputable def pythagoreanControlSummary
    (n : Nat) :
    SpectralSummary where
  gap := 5 / 2
  width := (5 / 2) * n
  normalizedGap := (5 / 2) / ((5 / 2) * n)
  locality := 3

theorem pythagoreanControlSummary_gap
    (n : Nat) :
    (pythagoreanControlSummary n).gap =
      pythagoreanSpectralScale *
        (openChainExactBeforeSummary n).gap := by
  norm_num [
    pythagoreanControlSummary,
    pythagoreanSpectralScale,
    openChainExactBeforeSummary,
    openChainBeforeSummary
  ]

theorem pythagoreanControlSummary_width
    (n : Nat) :
    (pythagoreanControlSummary n).width =
      pythagoreanSpectralScale *
        (openChainExactBeforeSummary n).width := by
  norm_num [
    pythagoreanControlSummary,
    pythagoreanSpectralScale,
    openChainExactBeforeSummary,
    openChainBeforeSummary
  ]
  ring

theorem pythagoreanControlSummary_normalized
    (n : Nat)
    (hN : 0 < n) :
    ComputedNormalizedGap (pythagoreanControlSummary n) =
      1 / (n : Real) := by
  have hNReal : (n : Real) ≠ 0 := by
    exact_mod_cast (Nat.ne_of_gt hN)
  unfold ComputedNormalizedGap pythagoreanControlSummary
  field_simp [hNReal]

theorem pythagorean_noncommuting_control_boundary
    (n : Nat)
    (hN : 0 < n) :
    (¬ Commute pauliX tiltedLocalOperator) ∧
      (∀ scale : Complex,
        tiltedLocalOperator ≠ scale • pauliX) ∧
      spectrum Complex tiltedLocalOperator =
        Set.range tiltedLocalEigenvalue ∧
      (pythagoreanFieldTerm 0).support.card = 1 ∧
      ComputedNormalizedGap (pythagoreanControlSummary n) =
        1 / (n : Real) := by
  exact ⟨
    pauliX_does_not_commute_with_tiltedLocalOperator,
    tiltedLocalOperator_not_scalar_pauliX,
    tiltedLocalOperator_spectrum,
    pythagorean_field_support_card 0,
    pythagoreanControlSummary_normalized n hN
  ⟩

end ClusterStabilizer
end B9
