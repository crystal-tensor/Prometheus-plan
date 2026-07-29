import B9.ClusterStabilizer.OperatorSemantics

namespace B9
namespace ClusterStabilizer

open scoped BigOperators

def finTwoSign (bit : Fin 2) : Complex :=
  (-1 : Complex) ^ bit.val

@[simp] theorem finTwoSign_zero :
    finTwoSign (0 : Fin 2) = 1 := by
  norm_num [finTwoSign]

@[simp] theorem finTwoSign_one :
    finTwoSign (1 : Fin 2) = -1 := by
  norm_num [finTwoSign]

theorem finTwoSign_add (a b : Fin 2) :
    finTwoSign (a + b) = finTwoSign a * finTwoSign b := by
  fin_cases a <;> fin_cases b <;>
    norm_num [finTwoSign, Fin.add_def, pow_two]

theorem finTwoSign_injective :
    Function.Injective finTwoSign := by
  intro a b h
  fin_cases a <;> fin_cases b <;> norm_num [finTwoSign] at h ⊢

theorem finTwoSign_one_pow_val (bit : Fin 2) :
    finTwoSign (1 : Fin 2) ^ bit.val = finTwoSign bit := by
  fin_cases bit <;> norm_num [finTwoSign]

def finTwoCharacter : AddChar (Fin 2) Complex where
  toFun := finTwoSign
  map_zero_eq_one' := finTwoSign_zero
  map_add_eq_mul' := finTwoSign_add

def coordinateCharacter
    {n : Nat}
    (q : Fin n) :
    AddChar (QubitBasis n) Complex :=
  finTwoCharacter.compAddMonoidHom
    (Pi.evalAddMonoidHom (fun _ : Fin n => Fin 2) q)

def walshCharacter
    {n : Nat}
    (label : QubitBasis n) :
    AddChar (QubitBasis n) Complex :=
  ∏ q : Fin n, (coordinateCharacter q) ^ (label q).val

@[simp] theorem coordinateCharacter_apply
    {n : Nat}
    (q : Fin n)
    (state : QubitBasis n) :
    coordinateCharacter q state = finTwoSign (state q) := by
  rfl

theorem walshCharacter_apply
    {n : Nat}
    (label state : QubitBasis n) :
    walshCharacter label state =
      ∏ q : Fin n, finTwoSign (state q) ^ (label q).val := by
  simp [walshCharacter, AddChar.prod_apply]

def singleQubitState
    {n : Nat}
    (q : Fin n) :
    QubitBasis n :=
  Pi.single q 1

theorem walshCharacter_singleQubitState
    {n : Nat}
    (label : QubitBasis n)
    (q : Fin n) :
    walshCharacter label (singleQubitState q) =
      finTwoSign (label q) := by
  rw [walshCharacter_apply]
  classical
  rw [Finset.prod_eq_single q]
  · simpa [singleQubitState] using finTwoSign_one_pow_val (label q)
  · intro p _ hp
    simp [singleQubitState, Pi.single_apply, hp, Ne.symm hp]
  · simp

theorem walshCharacter_injective
    {n : Nat} :
    Function.Injective (walshCharacter : QubitBasis n → AddChar (QubitBasis n) Complex) := by
  intro left right hCharacters
  funext q
  have hAtQ :
      walshCharacter left (singleQubitState q) =
        walshCharacter right (singleQubitState q) := by
    rw [hCharacters]
  rw [
    walshCharacter_singleQubitState,
    walshCharacter_singleQubitState
  ] at hAtQ
  exact finTwoSign_injective hAtQ

theorem walshCharacter_eq_iff
    {n : Nat}
    (left right : QubitBasis n) :
    walshCharacter left = walshCharacter right ↔ left = right :=
  walshCharacter_injective.eq_iff

theorem star_finTwoSign (bit : Fin 2) :
    star (finTwoSign bit) = finTwoSign bit := by
  fin_cases bit <;> norm_num [finTwoSign]

theorem finTwoSign_pow_add_label
    (state left right : Fin 2) :
    finTwoSign state ^ ((left + right).val) =
      finTwoSign state ^ left.val * finTwoSign state ^ right.val := by
  fin_cases state <;> fin_cases left <;> fin_cases right <;>
    norm_num [finTwoSign, Fin.add_def, pow_two]

theorem walshCharacter_add
    {n : Nat}
    (left right : QubitBasis n) :
    walshCharacter (left + right) =
      walshCharacter left * walshCharacter right := by
  ext state
  rw [AddChar.mul_apply]
  repeat rw [walshCharacter_apply]
  rw [← Finset.prod_mul_distrib]
  apply Finset.prod_congr rfl
  intro q _
  exact finTwoSign_pow_add_label (state q) (left q) (right q)

theorem star_walshCharacter_apply
    {n : Nat}
    (label state : QubitBasis n) :
    star (walshCharacter label state) = walshCharacter label state := by
  simp only [
    walshCharacter_apply,
    star_prod,
    star_pow,
    star_finTwoSign
  ]

theorem finTwo_add_eq_zero_iff_eq
    (left right : Fin 2) :
    left + right = 0 ↔ left = right := by
  fin_cases left <;> fin_cases right <;>
    norm_num [Fin.add_def]

theorem finTwo_add_one_add_one
    (bit : Fin 2) :
    bit + 1 + 1 = bit := by
  fin_cases bit <;> norm_num [Fin.add_def]

theorem qubitBasis_add_eq_zero_iff_eq
    {n : Nat}
    (left right : QubitBasis n) :
    left + right = 0 ↔ left = right := by
  constructor
  · intro h
    funext q
    exact (finTwo_add_eq_zero_iff_eq (left q) (right q)).mp
      (congrFun h q)
  · intro h
    subst right
    funext q
    exact (finTwo_add_eq_zero_iff_eq (left q) (left q)).mpr rfl

@[simp] theorem walshCharacter_zero
    {n : Nat} :
    walshCharacter (0 : QubitBasis n) = 0 := by
  ext state
  simp [walshCharacter_apply]

theorem walshCharacter_add_eq_zero_iff_eq
    {n : Nat}
    (left right : QubitBasis n) :
    walshCharacter (left + right) = 0 ↔ left = right := by
  constructor
  · intro hCharacter
    have hLabel : left + right = 0 := by
      apply walshCharacter_injective
      simpa using hCharacter
    exact (qubitBasis_add_eq_zero_iff_eq left right).mp hLabel
  · intro hEqual
    have hLabel : left + right = 0 :=
      (qubitBasis_add_eq_zero_iff_eq left right).mpr hEqual
    rw [hLabel, walshCharacter_zero]

theorem walsh_character_orthogonality
    {n : Nat}
    (left right : QubitBasis n) :
    (∑ state : QubitBasis n,
      star (walshCharacter left state) * walshCharacter right state) =
        if left = right then (2 ^ n : Complex) else 0 := by
  simp_rw [star_walshCharacter_apply]
  change (∑ state : QubitBasis n,
    (walshCharacter left * walshCharacter right) state) =
      if left = right then (2 ^ n : Complex) else 0
  rw [← walshCharacter_add]
  rw [AddChar.sum_eq_ite]
  rw [qubitBasis_card]
  by_cases hEqual : left = right
  · have hCharacter :
        walshCharacter (left + right) = 0 :=
      (walshCharacter_add_eq_zero_iff_eq left right).mpr hEqual
    rw [if_pos hCharacter, if_pos hEqual]
    norm_num [Nat.cast_pow]
  · have hCharacter :
        walshCharacter (left + right) ≠ 0 := by
      exact fun h =>
        hEqual ((walshCharacter_add_eq_zero_iff_eq left right).mp h)
    rw [if_neg hCharacter, if_neg hEqual]

theorem finTwoSign_pow_comm
    (left right : Fin 2) :
    finTwoSign left ^ right.val =
      finTwoSign right ^ left.val := by
  fin_cases left <;> fin_cases right <;> norm_num [finTwoSign]

theorem walshCharacter_apply_comm
    {n : Nat}
    (left right : QubitBasis n) :
    walshCharacter left right = walshCharacter right left := by
  repeat rw [walshCharacter_apply]
  apply Finset.prod_congr rfl
  intro q _
  exact finTwoSign_pow_comm (right q) (left q)

noncomputable def walshMatrix
    (n : Nat) :
    Matrix (QubitBasis n) (QubitBasis n) Complex :=
  fun state label => walshCharacter label state

theorem walshMatrix_conjTranspose
    (n : Nat) :
    (walshMatrix n).conjTranspose = walshMatrix n := by
  ext state label
  simp only [Matrix.conjTranspose_apply, walshMatrix]
  rw [star_walshCharacter_apply, walshCharacter_apply_comm]

theorem walshMatrix_conjTranspose_mul
    (n : Nat) :
    (walshMatrix n).conjTranspose * walshMatrix n =
      (2 ^ n : Complex) • (1 :
        Matrix (QubitBasis n) (QubitBasis n) Complex) := by
  ext left right
  simp only [
    Matrix.mul_apply,
    Matrix.conjTranspose_apply,
    walshMatrix
  ]
  rw [walsh_character_orthogonality]
  by_cases hEqual : left = right
  · subst right
    simp [Matrix.one_apply, Nat.cast_pow]
  · simp [Matrix.one_apply, hEqual]

theorem walshMatrix_mul_self
    (n : Nat) :
    walshMatrix n * walshMatrix n =
      (2 ^ n : Complex) • (1 :
        Matrix (QubitBasis n) (QubitBasis n) Complex) := by
  calc
    walshMatrix n * walshMatrix n =
        (walshMatrix n).conjTranspose * walshMatrix n := by
      rw [walshMatrix_conjTranspose]
    _ = (2 ^ n : Complex) • 1 :=
      walshMatrix_conjTranspose_mul n

theorem two_pow_complex_nonzero
    (n : Nat) :
    (2 ^ n : Complex) ≠ 0 := by
  exact pow_ne_zero n (by norm_num)

noncomputable def walshMatrixInverse
    (n : Nat) :
    Matrix (QubitBasis n) (QubitBasis n) Complex :=
  ((2 ^ n : Complex)⁻¹) • walshMatrix n

theorem walshMatrix_mul_inverse
    (n : Nat) :
    walshMatrix n * walshMatrixInverse n = 1 := by
  rw [
    walshMatrixInverse,
    Matrix.mul_smul,
    walshMatrix_mul_self
  ]
  simp [smul_smul, two_pow_complex_nonzero n]

theorem walshMatrix_inverse_mul
    (n : Nat) :
    walshMatrixInverse n * walshMatrix n = 1 := by
  rw [
    walshMatrixInverse,
    Matrix.smul_mul,
    walshMatrix_mul_self
  ]
  simp [smul_smul, two_pow_complex_nonzero n]

noncomputable def walshMatrixUnit
    (n : Nat) :
    (Matrix (QubitBasis n) (QubitBasis n) Complex)ˣ where
  val := walshMatrix n
  inv := walshMatrixInverse n
  val_inv := walshMatrix_mul_inverse n
  inv_val := walshMatrix_inverse_mul n

theorem pauliI_entry
    (row column : Fin 2) :
    pauliI row column = if row = column then 1 else 0 := by
  fin_cases row <;> fin_cases column <;> norm_num [pauliI]

theorem pauliX_entry
    (row column : Fin 2) :
    pauliX row column =
      if row = column + 1 then 1 else 0 := by
  fin_cases row <;> fin_cases column <;>
    norm_num [pauliX, Fin.add_def]

def flipState
    {n : Nat}
    (state : QubitBasis n)
    (q : Fin n) :
    QubitBasis n :=
  state + singleQubitState q

@[simp] theorem flipState_at
    {n : Nat}
    (state : QubitBasis n)
    (q : Fin n) :
    flipState state q q = state q + 1 := by
  simp [flipState, singleQubitState]

theorem flipState_away
    {n : Nat}
    (state : QubitBasis n)
    (q p : Fin n)
    (hDifferent : p ≠ q) :
    flipState state q p = state p := by
  simp [flipState, singleQubitState, Pi.single_apply, hDifferent]

theorem flipState_involutive
    {n : Nat}
    (state : QubitBasis n)
    (q : Fin n) :
    flipState (flipState state q) q = state := by
  funext p
  by_cases hSame : p = q
  · subst p
    rw [flipState_at, flipState_at]
    exact finTwo_add_one_add_one (state q)
  · repeat rw [flipState_away _ _ _ hSame]

def xSitePauli
    (n : Nat)
    (i q : Fin n) :
    Matrix (Fin 2) (Fin 2) Complex :=
  if q = i then pauliX else pauliI

def xPauliWord
    (n : Nat)
    (i : Fin n) :
    Matrix (QubitBasis n) (QubitBasis n) Complex :=
  pauliWordMatrix (xSitePauli n i)

theorem xPauliWord_entry
    (n : Nat)
    (i : Fin n)
    (row column : QubitBasis n) :
    xPauliWord n i row column =
      if row = flipState column i then 1 else 0 := by
  classical
  unfold xPauliWord pauliWordMatrix
  by_cases hMatch : row = flipState column i
  · rw [if_pos hMatch]
    subst row
    apply Finset.prod_eq_one
    intro q _
    by_cases hCenter : q = i
    · subst q
      simp [xSitePauli, pauliX_entry]
    · rw [xSitePauli]
      simp only [if_neg hCenter]
      rw [pauliI_entry, if_pos]
      exact flipState_away column i q hCenter
  · rw [if_neg hMatch]
    have hCoordinate :
        ∃ q : Fin n, row q ≠ flipState column i q := by
      by_contra hNoCoordinate
      push_neg at hNoCoordinate
      exact hMatch (funext hNoCoordinate)
    obtain ⟨q, hq⟩ := hCoordinate
    apply Finset.prod_eq_zero (Finset.mem_univ q)
    by_cases hCenter : q = i
    · subst q
      rw [xSitePauli, if_pos rfl, pauliX_entry, if_neg]
      simpa using hq
    · rw [xSitePauli, if_neg hCenter, pauliI_entry, if_neg]
      intro hRowColumn
      apply hq
      rw [flipState_away column i q hCenter]
      exact hRowColumn

theorem walshCharacter_flipState
    {n : Nat}
    (label state : QubitBasis n)
    (q : Fin n) :
    walshCharacter label (flipState state q) =
      finTwoSign (label q) * walshCharacter label state := by
  rw [
    flipState,
    AddChar.map_add_eq_mul,
    walshCharacter_singleQubitState,
    mul_comm
  ]

theorem xPauliWord_mulVec_walsh
    (n : Nat)
    (i : Fin n)
    (label : QubitBasis n) :
    Matrix.mulVec (xPauliWord n i)
        (fun state => walshCharacter label state) =
      finTwoSign (label i) •
        (fun state => walshCharacter label state) := by
  funext row
  rw [Matrix.mulVec, Matrix.dotProduct]
  classical
  rw [Finset.sum_eq_single (flipState row i)]
  · rw [xPauliWord_entry, if_pos]
    · simp [walshCharacter_flipState]
    · exact (flipState_involutive row i).symm
  · intro column _ hDifferent
    rw [xPauliWord_entry, if_neg]
    · simp
    · intro hRow
      apply hDifferent
      calc
        column = flipState (flipState column i) i :=
          (flipState_involutive column i).symm
        _ = flipState row i := by rw [← hRow]
  · simp

noncomputable def xChainTermOperator
    (n : Nat)
    (i : Fin n) :
    Matrix (QubitBasis n) (QubitBasis n) Complex :=
  (-1 : Complex) • xPauliWord n i

noncomputable def xChainOperator
    (n : Nat) :
    Matrix (QubitBasis n) (QubitBasis n) Complex :=
  ∑ i : Fin n, xChainTermOperator n i

noncomputable def openChainEigenvalue
    {n : Nat}
    (label : QubitBasis n) :
    Complex :=
  -∑ i : Fin n, finTwoSign (label i)

theorem xChainOperator_mulVec_walsh
    (n : Nat)
    (label : QubitBasis n) :
    Matrix.mulVec (xChainOperator n)
        (fun state => walshCharacter label state) =
      openChainEigenvalue label •
        (fun state => walshCharacter label state) := by
  funext row
  simp only [
    xChainOperator,
    xChainTermOperator,
    Matrix.mulVec,
    Matrix.dotProduct,
    Matrix.sum_apply,
    Matrix.smul_apply,
    Pi.smul_apply,
    smul_eq_mul
  ]
  change
    (∑ column : QubitBasis n,
      (∑ i : Fin n, (-1 : Complex) * xPauliWord n i row column) *
        walshCharacter label column) =
      openChainEigenvalue label * walshCharacter label row
  simp_rw [Finset.sum_mul]
  rw [Finset.sum_comm]
  calc
    (∑ i : Fin n, ∑ column : QubitBasis n,
      ((-1 : Complex) * xPauliWord n i row column) *
        walshCharacter label column) =
        ∑ i : Fin n, (-1 : Complex) *
          (∑ column : QubitBasis n,
            xPauliWord n i row column *
              walshCharacter label column) := by
      apply Finset.sum_congr rfl
      intro i _
      rw [Finset.mul_sum]
      apply Finset.sum_congr rfl
      intro column _
      ring
    _ = ∑ i : Fin n, (-1 : Complex) *
        (finTwoSign (label i) * walshCharacter label row) := by
      apply Finset.sum_congr rfl
      intro i _
      congr 1
      exact congrFun (xPauliWord_mulVec_walsh n i label) row
    _ = openChainEigenvalue label * walshCharacter label row := by
      rw [openChainEigenvalue]
      simp only [one_mul, neg_one_mul]
      rw [Finset.sum_neg_distrib, ← Finset.sum_mul]
      ring

theorem xChainOperator_mul_walshMatrix
    (n : Nat) :
    xChainOperator n * walshMatrix n =
      walshMatrix n * Matrix.diagonal
        (openChainEigenvalue : QubitBasis n → Complex) := by
  ext row label
  have hEigen :=
    congrFun (xChainOperator_mulVec_walsh n label) row
  change
    Matrix.mulVec (xChainOperator n)
        (fun state => walshCharacter label state) row =
      (walshMatrix n * Matrix.diagonal
        (openChainEigenvalue : QubitBasis n → Complex)) row label
  rw [hEigen, Matrix.mul_diagonal]
  simp [walshMatrix, mul_comm]

theorem walsh_diagonalizes_xChainOperator
    (n : Nat) :
    walshMatrixInverse n * xChainOperator n * walshMatrix n =
      Matrix.diagonal
        (openChainEigenvalue : QubitBasis n → Complex) := by
  calc
    walshMatrixInverse n * xChainOperator n * walshMatrix n =
        walshMatrixInverse n *
          (xChainOperator n * walshMatrix n) := by
      rw [Matrix.mul_assoc]
    _ = walshMatrixInverse n *
        (walshMatrix n * Matrix.diagonal
          (openChainEigenvalue : QubitBasis n → Complex)) := by
      rw [xChainOperator_mul_walshMatrix]
    _ = (walshMatrixInverse n * walshMatrix n) *
        Matrix.diagonal
          (openChainEigenvalue : QubitBasis n → Complex) := by
      rw [Matrix.mul_assoc]
    _ = Matrix.diagonal
        (openChainEigenvalue : QubitBasis n → Complex) := by
      rw [walshMatrix_inverse_mul, Matrix.one_mul]

theorem xChainOperator_spectrum
    (n : Nat) :
    spectrum Complex (xChainOperator n) =
      Set.range (openChainEigenvalue : QubitBasis n → Complex) := by
  let unit := walshMatrixUnit n
  have hConjugated :
      (↑unit⁻¹ :
        Matrix (QubitBasis n) (QubitBasis n) Complex) *
          xChainOperator n *
          (↑unit :
            Matrix (QubitBasis n) (QubitBasis n) Complex) =
        Matrix.diagonal
          (openChainEigenvalue : QubitBasis n → Complex) := by
    exact walsh_diagonalizes_xChainOperator n
  calc
    spectrum Complex (xChainOperator n) =
        spectrum Complex (
          (↑unit⁻¹ :
            Matrix (QubitBasis n) (QubitBasis n) Complex) *
            xChainOperator n *
            (↑unit :
              Matrix (QubitBasis n) (QubitBasis n) Complex)) := by
      simpa using
        (spectrum.units_conjugate'
          (R := Complex)
          (a := xChainOperator n)
          (u := unit)).symm
    _ = spectrum Complex (Matrix.diagonal
        (openChainEigenvalue : QubitBasis n → Complex)) := by
      rw [hConjugated]
    _ = Set.range
        (openChainEigenvalue : QubitBasis n → Complex) := by
      exact spectrum_diagonal _

def edgeLeft
    {n : Nat}
    (edge : Fin (n - 1)) :
    Fin n :=
  ⟨edge.val, by omega⟩

def edgeRight
    {n : Nat}
    (edge : Fin (n - 1)) :
    Fin n :=
  ⟨edge.val + 1, by omega⟩

theorem edgeLeft_ne_edgeRight
    {n : Nat}
    (edge : Fin (n - 1)) :
    edgeLeft edge ≠ edgeRight edge := by
  intro hEqual
  have hVal := congrArg Fin.val hEqual
  simp [edgeLeft, edgeRight] at hVal

theorem edgeLeft_injective
    {n : Nat} :
    Function.Injective (edgeLeft : Fin (n - 1) → Fin n) := by
  intro left right hEqual
  apply Fin.ext
  simpa [edgeLeft] using congrArg Fin.val hEqual

theorem edgeRight_injective
    {n : Nat} :
    Function.Injective (edgeRight : Fin (n - 1) → Fin n) := by
  intro left right hEqual
  apply Fin.ext
  have hVal := congrArg Fin.val hEqual
  simp [edgeRight] at hVal
  omega

def clusterParity
    {n : Nat}
    (state : QubitBasis n) :
    Fin 2 :=
  ∑ edge : Fin (n - 1),
    state (edgeLeft edge) * state (edgeRight edge)

def clusterCrossParity
    {n : Nat}
    (left right : QubitBasis n) :
    Fin 2 :=
  ∑ edge : Fin (n - 1),
    (left (edgeLeft edge) * right (edgeRight edge) +
      right (edgeLeft edge) * left (edgeRight edge))

theorem clusterParity_add
    {n : Nat}
    (left right : QubitBasis n) :
    clusterParity (left + right) =
      clusterParity left + clusterParity right +
        clusterCrossParity left right := by
  unfold clusterParity clusterCrossParity
  simp only [Pi.add_apply]
  simp_rw [add_mul, mul_add]
  simp only [Finset.sum_add_distrib]
  ring

theorem singleQubit_clusterParity_zero
    {n : Nat}
    (q : Fin n) :
    clusterParity (singleQubitState q) = 0 := by
  unfold clusterParity
  apply Finset.sum_eq_zero
  intro edge _
  by_cases hLeft : edgeLeft edge = q
  · have hRight : edgeRight edge ≠ q := by
      intro hEqual
      exact edgeLeft_ne_edgeRight edge (hLeft.trans hEqual.symm)
    simp [singleQubitState, Pi.single_apply, hLeft, hRight]
  · simp [singleQubitState, Pi.single_apply, hLeft]

def incidentParity
    {n : Nat}
    (state : QubitBasis n)
    (q : Fin n) :
    Fin 2 :=
  clusterCrossParity state (singleQubitState q)

def leftIncidentEdge
    {n : Nat}
    (q : Fin n)
    (hLeft : 0 < q.val) :
    Fin (n - 1) :=
  ⟨q.val - 1, by omega⟩

def rightIncidentEdge
    {n : Nat}
    (q : Fin n)
    (hRight : q.val + 1 < n) :
    Fin (n - 1) :=
  ⟨q.val, by omega⟩

@[simp] theorem edgeRight_leftIncidentEdge
    {n : Nat}
    (q : Fin n)
    (hLeft : 0 < q.val) :
    edgeRight (leftIncidentEdge q hLeft) = q := by
  apply Fin.ext
  simp [edgeRight, leftIncidentEdge]
  omega

@[simp] theorem edgeLeft_rightIncidentEdge
    {n : Nat}
    (q : Fin n)
    (hRight : q.val + 1 < n) :
    edgeLeft (rightIncidentEdge q hRight) = q := by
  apply Fin.ext
  simp [edgeLeft, rightIncidentEdge]

def leftNeighborBit
    {n : Nat}
    (state : QubitBasis n)
    (q : Fin n) :
    Fin 2 :=
  if hLeft : 0 < q.val then
    state ⟨q.val - 1, by omega⟩
  else
    0

def rightNeighborBit
    {n : Nat}
    (state : QubitBasis n)
    (q : Fin n) :
    Fin 2 :=
  if hRight : q.val + 1 < n then
    state ⟨q.val + 1, hRight⟩
  else
    0

def explicitIncidentParity
    {n : Nat}
    (state : QubitBasis n)
    (q : Fin n) :
    Fin 2 :=
  leftNeighborBit state q + rightNeighborBit state q

theorem incidentParity_eq_explicit
    {n : Nat}
    (state : QubitBasis n)
    (q : Fin n) :
    incidentParity state q = explicitIncidentParity state q := by
  unfold incidentParity clusterCrossParity explicitIncidentParity
  rw [Finset.sum_add_distrib]
  congr 1
  · by_cases hLeft : 0 < q.val
    · let edge := leftIncidentEdge q hLeft
      have hPredicate :
          ∀ candidate : Fin (n - 1),
            edgeRight candidate = q ↔ candidate = edge := by
        intro candidate
        constructor
        · intro hCandidate
          exact edgeRight_injective
            (hCandidate.trans (edgeRight_leftIncidentEdge q hLeft).symm)
        · intro hCandidate
          subst candidate
          exact edgeRight_leftIncidentEdge q hLeft
      simp only [
        singleQubitState,
        Pi.single_apply,
        mul_ite,
        mul_one,
        mul_zero
      ]
      simp_rw [hPredicate]
      rw [Fintype.sum_ite_eq']
      simp [leftNeighborBit, hLeft, edgeLeft, leftIncidentEdge]
      apply congrArg state
      apply Fin.ext
      simp [edge, edgeLeft, leftIncidentEdge]
    · have hNoEdge :
          ∀ candidate : Fin (n - 1), edgeRight candidate ≠ q := by
        intro candidate hCandidate
        have hVal := congrArg Fin.val hCandidate
        simp [edgeRight] at hVal
        omega
      simp only [
        singleQubitState,
        Pi.single_apply,
        mul_ite,
        mul_one,
        mul_zero
      ]
      simp_rw [if_neg (hNoEdge _)]
      simp [leftNeighborBit, hLeft]
  · by_cases hRight : q.val + 1 < n
    · let edge := rightIncidentEdge q hRight
      have hPredicate :
          ∀ candidate : Fin (n - 1),
            edgeLeft candidate = q ↔ candidate = edge := by
        intro candidate
        constructor
        · intro hCandidate
          exact edgeLeft_injective
            (hCandidate.trans (edgeLeft_rightIncidentEdge q hRight).symm)
        · intro hCandidate
          subst candidate
          exact edgeLeft_rightIncidentEdge q hRight
      simp only [
        singleQubitState,
        Pi.single_apply,
        ite_mul,
        one_mul,
        zero_mul
      ]
      simp_rw [hPredicate]
      rw [Fintype.sum_ite_eq']
      simp [rightNeighborBit, hRight, edgeRight, rightIncidentEdge]
      apply congrArg state
      apply Fin.ext
      simp [edge, edgeRight, rightIncidentEdge]
    · have hNoEdge :
          ∀ candidate : Fin (n - 1), edgeLeft candidate ≠ q := by
        intro candidate hCandidate
        have hVal := congrArg Fin.val hCandidate
        simp [edgeLeft] at hVal
        omega
      simp only [
        singleQubitState,
        Pi.single_apply,
        ite_mul,
        one_mul,
        zero_mul
      ]
      simp_rw [if_neg (hNoEdge _)]
      simp [rightNeighborBit, hRight]

theorem clusterParity_flip_add
    {n : Nat}
    (state : QubitBasis n)
    (q : Fin n) :
    clusterParity (flipState state q) + clusterParity state =
      incidentParity state q := by
  rw [
    flipState,
    clusterParity_add,
    singleQubit_clusterParity_zero
  ]
  unfold incidentParity
  have hSelfCancel :
      clusterParity state + clusterParity state = 0 := by
    apply (finTwo_add_eq_zero_iff_eq
      (clusterParity state) (clusterParity state)).mpr
    rfl
  rw [add_zero]
  calc
    clusterParity state + clusterCrossParity state (singleQubitState q) +
        clusterParity state =
      (clusterParity state + clusterParity state) +
        clusterCrossParity state (singleQubitState q) := by
      ac_rfl
    _ = clusterCrossParity state (singleQubitState q) := by
      rw [hSelfCancel, zero_add]

def clusterPhase
    {n : Nat}
    (state : QubitBasis n) :
    Complex :=
  finTwoSign (clusterParity state)

def incidentPhase
    {n : Nat}
    (state : QubitBasis n)
    (q : Fin n) :
    Complex :=
  finTwoSign (incidentParity state q)

theorem clusterPhase_flip_mul
    {n : Nat}
    (state : QubitBasis n)
    (q : Fin n) :
    clusterPhase (flipState state q) * clusterPhase state =
      incidentPhase state q := by
  rw [
    clusterPhase,
    clusterPhase,
    incidentPhase,
    ← finTwoSign_add,
    clusterParity_flip_add
  ]

theorem mem_openChainZSites_iff
    (n i q : Nat) :
    q ∈ openChainZSites n i ↔
      (i ≠ 0 ∧ q = i - 1) ∨
        (i + 1 < n ∧ q = i + 1) := by
  by_cases hLeft : i = 0
  · subst i
    by_cases hRight : 1 < n <;>
      simp [openChainZSites, hRight]
  · by_cases hRight : i + 1 < n <;>
      simp [openChainZSites, hLeft, hRight]

def leftNeighborIndex
    {n : Nat}
    (q : Fin n)
    (hLeft : 0 < q.val) :
    Fin n :=
  ⟨q.val - 1, by omega⟩

def rightNeighborIndex
    {n : Nat}
    (q : Fin n)
    (hRight : q.val + 1 < n) :
    Fin n :=
  ⟨q.val + 1, hRight⟩

theorem fintype_prod_two_indicator
    {index value : Type*}
    [Fintype index]
    [DecidableEq index]
    [CommMonoid value]
    (left right : index)
    (hDifferent : left ≠ right)
    (f : index → value) :
    (∏ q : index,
      if q = left ∨ q = right then f q else 1) =
        f left * f right := by
  calc
    (∏ q : index,
      if q = left ∨ q = right then f q else 1) =
        ∏ q : index,
          (if q = left then f q else 1) *
            (if q = right then f q else 1) := by
      apply Finset.prod_congr rfl
      intro q _
      by_cases hQLeft : q = left
      · subst q
        simp [hDifferent]
      · by_cases hQRight : q = right
        · subst q
          simp [hDifferent, hQLeft]
        · simp [hQLeft, hQRight]
    _ = (∏ q : index, if q = left then f q else 1) *
        (∏ q : index, if q = right then f q else 1) := by
      rw [Finset.prod_mul_distrib]
    _ = f left * f right := by
      rw [Fintype.prod_ite_eq', Fintype.prod_ite_eq']

def openChainNeighborPhase
    (n : Nat)
    (i : Fin n)
    (state : QubitBasis n) :
    Complex :=
  ∏ q : Fin n,
    if q.val ∈ openChainZSites n i.val then
      finTwoSign (state q)
    else
      1

theorem openChainNeighborPhase_eq_incidentPhase
    (n : Nat)
    (i : Fin n)
    (state : QubitBasis n) :
    openChainNeighborPhase n i state =
      incidentPhase state i := by
  rw [incidentPhase, incidentParity_eq_explicit]
  unfold explicitIncidentParity openChainNeighborPhase
  by_cases hLeft : 0 < i.val
  · have hLeftNonzero : i.val ≠ 0 := by omega
    let left := leftNeighborIndex i hLeft
    by_cases hRight : i.val + 1 < n
    · let right := rightNeighborIndex i hRight
      have hDifferent : left ≠ right := by
        intro hEqual
        have hVal := congrArg Fin.val hEqual
        simp [left, right, leftNeighborIndex, rightNeighborIndex] at hVal
      have hMembership :
          ∀ q : Fin n,
            q.val ∈ openChainZSites n i.val ↔
              q = left ∨ q = right := by
        intro q
        rw [mem_openChainZSites_iff]
        constructor
        · rintro (⟨_, hQLeft⟩ | ⟨_, hQRight⟩)
          · left
            apply Fin.ext
            simpa [left, leftNeighborIndex] using hQLeft
          · right
            apply Fin.ext
            simpa [right, rightNeighborIndex] using hQRight
        · rintro (rfl | rfl)
          · left
            refine ⟨hLeftNonzero, ?_⟩
            simp [left, leftNeighborIndex]
          · right
            refine ⟨hRight, ?_⟩
            simp [right, rightNeighborIndex]
      simp_rw [hMembership]
      rw [fintype_prod_two_indicator left right hDifferent]
      simp [
        leftNeighborBit,
        rightNeighborBit,
        hLeft,
        hRight,
        left,
        right,
        leftNeighborIndex,
        rightNeighborIndex,
        finTwoSign_add
      ]
    · have hMembership :
          ∀ q : Fin n,
            q.val ∈ openChainZSites n i.val ↔
              q = left := by
        intro q
        rw [mem_openChainZSites_iff]
        constructor
        · rintro (⟨_, hQLeft⟩ | ⟨hImpossible, _⟩)
          · apply Fin.ext
            simpa [left, leftNeighborIndex] using hQLeft
          · exact (hRight hImpossible).elim
        · rintro rfl
          left
          refine ⟨hLeftNonzero, ?_⟩
          simp [left, leftNeighborIndex]
      simp_rw [hMembership]
      rw [Fintype.prod_ite_eq']
      simp [
        leftNeighborBit,
        rightNeighborBit,
        hLeft,
        hRight,
        left,
        leftNeighborIndex
      ]
  · have hLeftZero : i.val = 0 := by omega
    by_cases hRight : i.val + 1 < n
    · let right := rightNeighborIndex i hRight
      have hMembership :
          ∀ q : Fin n,
            q.val ∈ openChainZSites n i.val ↔
              q = right := by
        intro q
        rw [mem_openChainZSites_iff]
        constructor
        · rintro (⟨hImpossible, _⟩ | ⟨_, hQRight⟩)
          · exact (hImpossible hLeftZero).elim
          · apply Fin.ext
            simpa [right, rightNeighborIndex] using hQRight
        · rintro rfl
          right
          refine ⟨hRight, ?_⟩
          simp [right, rightNeighborIndex]
      simp_rw [hMembership]
      rw [Fintype.prod_ite_eq']
      simp [
        leftNeighborBit,
        rightNeighborBit,
        hLeft,
        hRight,
        right,
        rightNeighborIndex
      ]
    · have hMembership :
          ∀ q : Fin n,
            q.val ∉ openChainZSites n i.val := by
        intro q hMember
        rw [mem_openChainZSites_iff] at hMember
        rcases hMember with hMember | hMember
        · exact hMember.1 hLeftZero
        · exact hRight hMember.1
      simp_rw [if_neg (hMembership _)]
      simp [
        leftNeighborBit,
        rightNeighborBit,
        hLeft,
        hRight
      ]

theorem pauliZ_entry
    (row column : Fin 2) :
    pauliZ row column =
      if row = column then finTwoSign row else 0 := by
  fin_cases row <;> fin_cases column <;>
    norm_num [pauliZ, finTwoSign]

theorem openChain_center_not_zSite
    (n : Nat)
    (i : Fin n) :
    i.val ∉ openChainZSites n i.val := by
  rw [mem_openChainZSites_iff]
  omega

theorem openChainPauliWord_entry
    (n : Nat)
    (i : Fin n)
    (row column : QubitBasis n) :
    openChainPauliWord n i row column =
      if row = flipState column i then
        openChainNeighborPhase n i column
      else
        0 := by
  classical
  unfold openChainPauliWord pauliWordMatrix openChainNeighborPhase
  by_cases hMatch : row = flipState column i
  · rw [if_pos hMatch]
    subst row
    apply Finset.prod_congr rfl
    intro q _
    by_cases hCenter : q = i
    · subst q
      rw [openChainSitePauli_at_center, pauliX_entry]
      simp [
        flipState_at,
        openChain_center_not_zSite
      ]
    · by_cases hZSite : q.val ∈ openChainZSites n i.val
      · rw [
          openChainSitePauli_at_zSite n i q hCenter hZSite,
          pauliZ_entry,
          if_pos
        ]
        · simp [hZSite, flipState_away column i q hCenter]
        · exact flipState_away column i q hCenter
      · rw [
          openChainSitePauli_away_from_term n i q hCenter hZSite,
          pauliI_entry,
          if_pos
        ]
        · simp [hZSite]
        · exact flipState_away column i q hCenter
  · rw [if_neg hMatch]
    have hCoordinate :
        ∃ q : Fin n, row q ≠ flipState column i q := by
      by_contra hNoCoordinate
      push_neg at hNoCoordinate
      exact hMatch (funext hNoCoordinate)
    obtain ⟨q, hq⟩ := hCoordinate
    apply Finset.prod_eq_zero (Finset.mem_univ q)
    by_cases hCenter : q = i
    · subst q
      rw [
        openChainSitePauli_at_center,
        pauliX_entry,
        if_neg
      ]
      simpa using hq
    · have hRowColumn : row q ≠ column q := by
        intro hEqual
        apply hq
        rw [flipState_away column i q hCenter]
        exact hEqual
      by_cases hZSite : q.val ∈ openChainZSites n i.val
      · rw [
          openChainSitePauli_at_zSite n i q hCenter hZSite,
          pauliZ_entry,
          if_neg hRowColumn
        ]
      · rw [
          openChainSitePauli_away_from_term n i q hCenter hZSite,
          pauliI_entry,
          if_neg hRowColumn
        ]

theorem finTwoSign_mul_self
    (bit : Fin 2) :
    finTwoSign bit * finTwoSign bit = 1 := by
  fin_cases bit <;> norm_num [finTwoSign]

theorem clusterPhase_mul_self
    {n : Nat}
    (state : QubitBasis n) :
    clusterPhase state * clusterPhase state = 1 := by
  unfold clusterPhase
  exact finTwoSign_mul_self (clusterParity state)

noncomputable def clusterPhaseMatrix
    (n : Nat) :
    Matrix (QubitBasis n) (QubitBasis n) Complex :=
  Matrix.diagonal clusterPhase

theorem clusterPhaseMatrix_mul_self
    (n : Nat) :
    clusterPhaseMatrix n * clusterPhaseMatrix n = 1 := by
  rw [clusterPhaseMatrix, Matrix.diagonal_mul_diagonal]
  ext row column
  by_cases hEqual : row = column
  · subst column
    simp [clusterPhase_mul_self]
  · simp [Matrix.one_apply, Matrix.diagonal, hEqual]

noncomputable def clusterPhaseMatrixUnit
    (n : Nat) :
    (Matrix (QubitBasis n) (QubitBasis n) Complex)ˣ where
  val := clusterPhaseMatrix n
  inv := clusterPhaseMatrix n
  val_inv := clusterPhaseMatrix_mul_self n
  inv_val := clusterPhaseMatrix_mul_self n

theorem clusterPhase_conjugates_xPauliWord
    (n : Nat)
    (i : Fin n) :
    clusterPhaseMatrix n * xPauliWord n i * clusterPhaseMatrix n =
      openChainPauliWord n i := by
  ext row column
  rw [
    clusterPhaseMatrix,
    Matrix.mul_diagonal,
    Matrix.diagonal_mul,
    xPauliWord_entry,
    openChainPauliWord_entry
  ]
  by_cases hMatch : row = flipState column i
  · rw [if_pos hMatch, if_pos hMatch]
    subst row
    rw [
      mul_one,
      clusterPhase_flip_mul,
      ← openChainNeighborPhase_eq_incidentPhase
    ]
  · rw [if_neg hMatch, if_neg hMatch]
    ring

theorem clusterPhase_conjugates_xChainTerm
    (n : Nat)
    (i : Fin n) :
    clusterPhaseMatrix n * xChainTermOperator n i *
        clusterPhaseMatrix n =
      openChainTermOperator n i := by
  ext row column
  simp only [
    xChainTermOperator,
    openChainTermOperator,
    openChainHamiltonian,
    openChainTerm,
    Matrix.smul_apply,
    smul_eq_mul
  ]
  have hWord :=
    congrFun (congrFun
      (clusterPhase_conjugates_xPauliWord n i) row) column
  norm_num at hWord ⊢
  exact hWord

theorem clusterPhase_conjugates_xChainOperator
    (n : Nat) :
    clusterPhaseMatrix n * xChainOperator n *
        clusterPhaseMatrix n =
      openChainOperator n := by
  unfold xChainOperator openChainOperator
  rw [Finset.mul_sum, Finset.sum_mul]
  apply Finset.sum_congr rfl
  intro i _
  exact clusterPhase_conjugates_xChainTerm n i

theorem openChainOperator_spectrum_formula
    (n : Nat) :
    spectrum Complex (openChainOperator n) =
      Set.range (openChainEigenvalue : QubitBasis n → Complex) := by
  let unit := clusterPhaseMatrixUnit n
  have hConjugated :
      (↑unit :
        Matrix (QubitBasis n) (QubitBasis n) Complex) *
          xChainOperator n *
          (↑unit⁻¹ :
            Matrix (QubitBasis n) (QubitBasis n) Complex) =
        openChainOperator n := by
    exact clusterPhase_conjugates_xChainOperator n
  calc
    spectrum Complex (openChainOperator n) =
        spectrum Complex (
          (↑unit :
            Matrix (QubitBasis n) (QubitBasis n) Complex) *
            xChainOperator n *
            (↑unit⁻¹ :
              Matrix (QubitBasis n) (QubitBasis n) Complex)) := by
      rw [hConjugated]
    _ = spectrum Complex (xChainOperator n) := by
      exact spectrum.units_conjugate
    _ = Set.range
        (openChainEigenvalue : QubitBasis n → Complex) :=
      xChainOperator_spectrum n

def labelWeight
    {n : Nat}
    (label : QubitBasis n) :
    Nat :=
  ∑ q : Fin n, (label q).val

def labelSupport
    {n : Nat}
    (label : QubitBasis n) :
    Finset (Fin n) :=
  Finset.univ.filter (fun q => label q = 1)

def labelOfSupport
    {n : Nat}
    (support : Finset (Fin n)) :
    QubitBasis n :=
  fun q => if q ∈ support then 1 else 0

theorem finTwo_indicator_one
    (bit : Fin 2) :
    (if bit = 1 then (1 : Fin 2) else 0) = bit := by
  fin_cases bit <;> rfl

theorem labelOfSupport_labelSupport
    {n : Nat}
    (label : QubitBasis n) :
    labelOfSupport (labelSupport label) = label := by
  funext q
  simp [labelOfSupport, labelSupport, finTwo_indicator_one]

theorem labelSupport_labelOfSupport
    {n : Nat}
    (support : Finset (Fin n)) :
    labelSupport (labelOfSupport support) = support := by
  ext q
  simp [labelSupport, labelOfSupport]

def labelSupportEquiv
    (n : Nat) :
    QubitBasis n ≃ Finset (Fin n) where
  toFun := labelSupport
  invFun := labelOfSupport
  left_inv := labelOfSupport_labelSupport
  right_inv := labelSupport_labelOfSupport

theorem finTwo_val_eq_indicator
    (bit : Fin 2) :
    bit.val = if bit = 1 then 1 else 0 := by
  fin_cases bit <;> norm_num

theorem labelWeight_eq_support_card
    {n : Nat}
    (label : QubitBasis n) :
    labelWeight label = (labelSupport label).card := by
  classical
  simp only [labelWeight, finTwo_val_eq_indicator]
  simp [labelSupport]

theorem finTwoSign_eq_one_sub_two_val
    (bit : Fin 2) :
    finTwoSign bit =
      1 - 2 * (bit.val : Complex) := by
  fin_cases bit <;> norm_num [finTwoSign]

theorem openChainEigenvalue_eq_weight
    {n : Nat}
    (label : QubitBasis n) :
    openChainEigenvalue label =
      ((2 * (labelWeight label : Int) - n : Int) : Complex) := by
  unfold openChainEigenvalue labelWeight
  simp_rw [finTwoSign_eq_one_sub_two_val]
  push_cast
  rw [Finset.sum_sub_distrib]
  simp
  rw [Finset.mul_sum]

def labelsOfWeightEquiv
    (n k : Nat) :
    {label : QubitBasis n // labelWeight label = k} ≃
      {support : Finset (Fin n) // support.card = k} :=
  (labelSupportEquiv n).subtypeEquiv
    (fun label => by
      change labelWeight label = k ↔ (labelSupport label).card = k
      rw [labelWeight_eq_support_card])

theorem labelWeight_multiplicity
    (n k : Nat) :
    Fintype.card {label : QubitBasis n // labelWeight label = k} =
      Nat.choose n k := by
  rw [Fintype.card_congr (labelsOfWeightEquiv n k)]
  simp

def openChainEnergy
    {n : Nat}
    (label : QubitBasis n) :
    Int :=
  2 * (labelWeight label : Int) - n

theorem openChainEigenvalue_eq_energy
    {n : Nat}
    (label : QubitBasis n) :
    openChainEigenvalue label = (openChainEnergy label : Complex) := by
  exact openChainEigenvalue_eq_weight label

theorem labelWeight_le
    {n : Nat}
    (label : QubitBasis n) :
    labelWeight label ≤ n := by
  rw [labelWeight_eq_support_card]
  simpa [labelSupport] using
    Finset.card_le_card
      (Finset.filter_subset
        (fun q : Fin n => label q = 1)
        Finset.univ)

theorem openChainEnergy_lower_bound
    {n : Nat}
    (label : QubitBasis n) :
    -(n : Int) ≤ openChainEnergy label := by
  unfold openChainEnergy
  omega

theorem openChainEnergy_upper_bound
    {n : Nat}
    (label : QubitBasis n) :
    openChainEnergy label ≤ (n : Int) := by
  have hWeight := labelWeight_le label
  unfold openChainEnergy
  omega

theorem labelWeight_zero
    (n : Nat) :
    labelWeight (0 : QubitBasis n) = 0 := by
  simp [labelWeight]

def allOneLabel
    (n : Nat) :
    QubitBasis n :=
  fun _ => 1

theorem labelWeight_allOne
    (n : Nat) :
    labelWeight (allOneLabel n) = n := by
  simp [labelWeight, allOneLabel]

theorem openChainEnergy_ground
    (n : Nat) :
    openChainEnergy (0 : QubitBasis n) = -(n : Int) := by
  simp [openChainEnergy, labelWeight_zero]

theorem openChainEnergy_top
    (n : Nat) :
    openChainEnergy (allOneLabel n) = (n : Int) := by
  rw [openChainEnergy, labelWeight_allOne]
  ring

theorem labelWeight_singleton
    {n : Nat}
    (q : Fin n) :
    labelWeight (labelOfSupport {q}) = 1 := by
  rw [labelWeight_eq_support_card, labelSupport_labelOfSupport]
  simp

theorem openChainEnergy_first_excited
    {n : Nat}
    (q : Fin n) :
    openChainEnergy (labelOfSupport {q}) = 2 - (n : Int) := by
  simp [openChainEnergy, labelWeight_singleton]

theorem openChain_raw_gap_formula
    {n : Nat}
    (q : Fin n) :
    openChainEnergy (labelOfSupport {q}) -
        openChainEnergy (0 : QubitBasis n) =
      2 := by
  rw [openChainEnergy_first_excited, openChainEnergy_ground]
  ring

theorem openChain_width_formula
    (n : Nat) :
    openChainEnergy (allOneLabel n) -
        openChainEnergy (0 : QubitBasis n) =
      2 * (n : Int) := by
  rw [openChainEnergy_top, openChainEnergy_ground]
  ring

noncomputable def openChainExactBeforeSummary
    (n : Nat) :
    SpectralSummary :=
  openChainBeforeSummary n 2 (2 * (n : Real))

noncomputable def openChainExactAfterSummary
    (n : Nat) :
    SpectralSummary :=
  openChainAfterSummary n 2 (2 * (n : Real))

theorem openChainExactBeforeSummary_gap
    (n : Nat) :
    (openChainExactBeforeSummary n).gap = 2 := by
  rfl

theorem openChainExactBeforeSummary_width
    (n : Nat) :
    (openChainExactBeforeSummary n).width = 2 * (n : Real) := by
  rfl

theorem openChainExactBeforeSummary_normalized
    (n : Nat)
    (hN : 0 < n) :
    B9.ComputedNormalizedGap (openChainExactBeforeSummary n) =
      1 / (n : Real) := by
  have hNReal : (n : Real) ≠ 0 := by
    exact_mod_cast (Nat.ne_of_gt hN)
  unfold B9.ComputedNormalizedGap openChainExactBeforeSummary
    openChainBeforeSummary
  field_simp [hNReal]

theorem openChain_exact_spectrum_reweight_boundary
    (n : Nat)
    (hN : 4 ≤ n) :
    spectrum Complex (openChainOperator n) =
        Set.range (openChainEigenvalue : QubitBasis n → Complex) ∧
      (∀ k : Nat,
        Fintype.card
          {label : QubitBasis n // labelWeight label = k} =
            Nat.choose n k) ∧
      (openChainExactBeforeSummary n).gap = 2 ∧
      (openChainExactBeforeSummary n).width = 2 * (n : Real) ∧
      RawGapAmplifies
        (openChainExactBeforeSummary n)
        (openChainExactAfterSummary n) ∧
      B9.ComputedNormalizedGapInvariant
        (openChainExactBeforeSummary n)
        (openChainExactAfterSummary n) ∧
      ¬ (
        B9.ComputedNormalizedGap (openChainExactAfterSummary n) >
          B9.ComputedNormalizedGap (openChainExactBeforeSummary n)
      ) := by
  have hBoundary :=
    open_chain_uniform_reweight_instantiates_r187
      n hN 2 (2 * (n : Real)) (by norm_num)
  rcases hBoundary with
    ⟨_hSupportBound, _hInterior, _hLocality,
      hRaw, hNormalized, _hWidthRatio, hNoImprovement⟩
  exact ⟨
    openChainOperator_spectrum_formula n,
    labelWeight_multiplicity n,
    openChainExactBeforeSummary_gap n,
    openChainExactBeforeSummary_width n,
    hRaw,
    hNormalized,
    hNoImprovement
  ⟩

end ClusterStabilizer
end B9
