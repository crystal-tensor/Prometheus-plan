import B9.ClusterStabilizer.OpenChainHamiltonian

namespace B9
namespace ClusterStabilizer

open scoped Pointwise

abbrev QubitBasis (n : Nat) := Fin n -> Fin 2

theorem qubitBasis_card (n : Nat) :
    Fintype.card (QubitBasis n) = 2 ^ n := by
  simp [QubitBasis]

def pauliI : Matrix (Fin 2) (Fin 2) Complex :=
  !![1, 0; 0, 1]

def pauliX : Matrix (Fin 2) (Fin 2) Complex :=
  !![0, 1; 1, 0]

def pauliZ : Matrix (Fin 2) (Fin 2) Complex :=
  !![1, 0; 0, -1]

theorem pauliI_isHermitian : pauliI.IsHermitian := by
  apply Matrix.IsHermitian.ext
  intro i j
  fin_cases i <;> fin_cases j <;> norm_num [pauliI]

theorem pauliX_isHermitian : pauliX.IsHermitian := by
  apply Matrix.IsHermitian.ext
  intro i j
  fin_cases i <;> fin_cases j <;> norm_num [pauliX]

theorem pauliZ_isHermitian : pauliZ.IsHermitian := by
  apply Matrix.IsHermitian.ext
  intro i j
  fin_cases i <;> fin_cases j <;> norm_num [pauliZ]

def pauliWordMatrix
    {n : Nat}
    (ops : Fin n -> Matrix (Fin 2) (Fin 2) Complex) :
    Matrix (QubitBasis n) (QubitBasis n) Complex :=
  fun row column => Finset.univ.prod fun q => ops q (row q) (column q)

theorem pauliWordMatrix_isHermitian
    {n : Nat}
    (ops : Fin n -> Matrix (Fin 2) (Fin 2) Complex)
    (hOps : forall q, (ops q).IsHermitian) :
    (pauliWordMatrix ops).IsHermitian := by
  apply Matrix.IsHermitian.ext
  intro row column
  simp only [pauliWordMatrix, star_prod]
  apply Finset.prod_congr rfl
  intro q _
  exact (hOps q).apply (row q) (column q)

def openChainSitePauli
    (n : Nat)
    (i q : Fin n) :
    Matrix (Fin 2) (Fin 2) Complex :=
  if q = i then pauliX
  else if q.val ∈ openChainZSites n i.val then pauliZ
  else pauliI

@[simp] theorem openChainSitePauli_at_center
    (n : Nat)
    (i : Fin n) :
    openChainSitePauli n i i = pauliX := by
  simp [openChainSitePauli]

theorem openChainSitePauli_at_zSite
    (n : Nat)
    (i q : Fin n)
    (hDifferent : q ≠ i)
    (hZSite : q.val ∈ openChainZSites n i.val) :
    openChainSitePauli n i q = pauliZ := by
  simp [openChainSitePauli, hDifferent, hZSite]

theorem openChainSitePauli_away_from_term
    (n : Nat)
    (i q : Fin n)
    (hDifferent : q ≠ i)
    (hNotZSite : q.val ∉ openChainZSites n i.val) :
    openChainSitePauli n i q = pauliI := by
  simp [openChainSitePauli, hDifferent, hNotZSite]

theorem openChainSitePauli_isHermitian
    (n : Nat)
    (i q : Fin n) :
    (openChainSitePauli n i q).IsHermitian := by
  unfold openChainSitePauli
  split_ifs
  · exact pauliX_isHermitian
  · exact pauliZ_isHermitian
  · exact pauliI_isHermitian

def openChainPauliWord
    (n : Nat)
    (i : Fin n) :
    Matrix (QubitBasis n) (QubitBasis n) Complex :=
  pauliWordMatrix (openChainSitePauli n i)

theorem openChainPauliWord_isHermitian
    (n : Nat)
    (i : Fin n) :
    (openChainPauliWord n i).IsHermitian := by
  exact pauliWordMatrix_isHermitian
    (openChainSitePauli n i)
    (openChainSitePauli_isHermitian n i)

noncomputable def openChainTermOperator
    (n : Nat)
    (i : Fin n) :
    Matrix (QubitBasis n) (QubitBasis n) Complex :=
  ((openChainHamiltonian n i).coefficient : Complex) •
    openChainPauliWord n i

noncomputable def reweightedOpenChainTermOperator
    (n : Nat)
    (i : Fin n) :
    Matrix (QubitBasis n) (QubitBasis n) Complex :=
  ((reweightedOpenChainHamiltonian n i).coefficient : Complex) •
    openChainPauliWord n i

theorem real_coefficient_smul_isHermitian
    {n : Nat}
    (coefficient : Real)
    (word : Matrix (QubitBasis n) (QubitBasis n) Complex)
    (hWord : word.IsHermitian) :
    (((coefficient : Complex) • word)).IsHermitian := by
  apply Matrix.IsHermitian.ext
  intro row column
  change
    star ((coefficient : Complex) * word column row) =
      (coefficient : Complex) * word row column
  rw [star_mul]
  rw [hWord.apply row column]
  simp [mul_comm]

theorem openChainTermOperator_isHermitian
    (n : Nat)
    (i : Fin n) :
    (openChainTermOperator n i).IsHermitian := by
  exact real_coefficient_smul_isHermitian
    (openChainHamiltonian n i).coefficient
    (openChainPauliWord n i)
    (openChainPauliWord_isHermitian n i)

theorem reweightedOpenChainTermOperator_isHermitian
    (n : Nat)
    (i : Fin n) :
    (reweightedOpenChainTermOperator n i).IsHermitian := by
  exact real_coefficient_smul_isHermitian
    (reweightedOpenChainHamiltonian n i).coefficient
    (openChainPauliWord n i)
    (openChainPauliWord_isHermitian n i)

noncomputable def openChainOperator
    (n : Nat) :
    Matrix (QubitBasis n) (QubitBasis n) Complex :=
  ∑ i : Fin n, openChainTermOperator n i

noncomputable def reweightedOpenChainOperator
    (n : Nat) :
    Matrix (QubitBasis n) (QubitBasis n) Complex :=
  ∑ i : Fin n, reweightedOpenChainTermOperator n i

theorem openChainOperator_isHermitian
    (n : Nat) :
    (openChainOperator n).IsHermitian := by
  apply Matrix.IsHermitian.ext
  intro row column
  simp only [openChainOperator, Matrix.sum_apply, star_sum]
  apply Finset.sum_congr rfl
  intro i _
  exact (openChainTermOperator_isHermitian n i).apply row column

theorem reweightedOpenChainOperator_isHermitian
    (n : Nat) :
    (reweightedOpenChainOperator n).IsHermitian := by
  apply Matrix.IsHermitian.ext
  intro row column
  simp only [reweightedOpenChainOperator, Matrix.sum_apply, star_sum]
  apply Finset.sum_congr rfl
  intro i _
  exact (reweightedOpenChainTermOperator_isHermitian n i).apply row column

noncomputable def uniformScaleComplex : Complex :=
  (B9.UniformScaleFactor : Complex)

theorem uniformScaleComplex_nonzero :
    uniformScaleComplex ≠ 0 := by
  unfold uniformScaleComplex
  exact_mod_cast B9.uniform_scale_factor_nonzero

theorem reweighted_term_operator_eq_smul
    (n : Nat)
    (i : Fin n) :
    reweightedOpenChainTermOperator n i =
      uniformScaleComplex • openChainTermOperator n i := by
  ext row column
  norm_num [
    reweightedOpenChainTermOperator,
    openChainTermOperator,
    reweightedOpenChainHamiltonian,
    reweightOpenChainTerm,
    openChainHamiltonian,
    openChainTerm,
    uniformScaleComplex,
    B9.UniformScaleFactor
  ]

theorem reweighted_operator_eq_smul
    (n : Nat) :
    reweightedOpenChainOperator n =
      uniformScaleComplex • openChainOperator n := by
  unfold reweightedOpenChainOperator openChainOperator
  rw [Finset.smul_sum]
  apply Finset.sum_congr rfl
  intro i _
  exact reweighted_term_operator_eq_smul n i

theorem reweighted_operator_spectrum_eq_smul
    (n : Nat) :
    spectrum Complex (reweightedOpenChainOperator n) =
      uniformScaleComplex • spectrum Complex (openChainOperator n) := by
  rw [reweighted_operator_eq_smul]
  simpa [uniformScaleComplex] using
    spectrum.unit_smul_eq_smul
      (openChainOperator n)
      (Units.mk0 uniformScaleComplex uniformScaleComplex_nonzero)

end ClusterStabilizer
end B9
