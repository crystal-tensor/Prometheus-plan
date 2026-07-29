import B9.ClusterStabilizer.NoncommutingControl

namespace B9
namespace ClusterStabilizer

noncomputable def overlapCoupling : Real := 1 / 2

def nearestNeighborSupport (left : Nat) : Finset Nat :=
  {left, left + 1}

theorem nearest_neighbor_support_card
    (left : Nat) :
    (nearestNeighborSupport left).card = 2 := by
  simp [nearestNeighborSupport]

theorem adjacent_bond_support_intersection
    (left : Nat) :
    nearestNeighborSupport left ∩
        nearestNeighborSupport (left + 1) =
      {left + 1} := by
  ext q
  simp [nearestNeighborSupport]
  omega

theorem adjacent_bond_supports_overlap
    (left : Nat) :
    (nearestNeighborSupport left ∩
        nearestNeighborSupport (left + 1)).Nonempty := by
  rw [adjacent_bond_support_intersection]
  simp

theorem first_two_bonds_cover_three_sites :
    nearestNeighborSupport 0 ∪ nearestNeighborSupport 1 =
      {0, 1, 2} := by
  ext q
  simp [nearestNeighborSupport]

def openChainBondSet (n : Nat) :
    Finset (Fin n × Fin n) :=
  Finset.univ.filter fun bond =>
    bond.2.val = bond.1.val + 1

def zzBondSitePauli
    (n : Nat)
    (bond : Fin n × Fin n)
    (q : Fin n) :
    Matrix (Fin 2) (Fin 2) Complex :=
  if q = bond.1 ∨ q = bond.2 then pauliZ else pauliI

def zzBondPauliWord
    (n : Nat)
    (bond : Fin n × Fin n) :
    Matrix (QubitBasis n) (QubitBasis n) Complex :=
  pauliWordMatrix (zzBondSitePauli n bond)

noncomputable def zzBondTermOperator
    (n : Nat)
    (bond : Fin n × Fin n) :
    Matrix (QubitBasis n) (QubitBasis n) Complex :=
  (overlapCoupling : Complex) •
    zzBondPauliWord n bond

noncomputable def zzInteractionOperator
    (n : Nat) :
    Matrix (QubitBasis n) (QubitBasis n) Complex :=
  ∑ bond ∈ openChainBondSet n,
    zzBondTermOperator n bond

noncomputable def overlappingControlOperator
    (n : Nat) :
    Matrix (QubitBasis n) (QubitBasis n) Complex :=
  tiltedProductOperator n + zzInteractionOperator n

theorem zzBondSitePauli_isHermitian
    (n : Nat)
    (bond : Fin n × Fin n)
    (q : Fin n) :
    (zzBondSitePauli n bond q).IsHermitian := by
  unfold zzBondSitePauli
  split_ifs
  · exact pauliZ_isHermitian
  · exact pauliI_isHermitian

theorem zzBondPauliWord_isHermitian
    (n : Nat)
    (bond : Fin n × Fin n) :
    (zzBondPauliWord n bond).IsHermitian := by
  exact pauliWordMatrix_isHermitian
    (zzBondSitePauli n bond)
    (zzBondSitePauli_isHermitian n bond)

theorem zzBondTermOperator_isHermitian
    (n : Nat)
    (bond : Fin n × Fin n) :
    (zzBondTermOperator n bond).IsHermitian := by
  exact real_coefficient_smul_isHermitian
    overlapCoupling
    (zzBondPauliWord n bond)
    (zzBondPauliWord_isHermitian n bond)

theorem zzInteractionOperator_isHermitian
    (n : Nat) :
    (zzInteractionOperator n).IsHermitian := by
  apply Matrix.IsHermitian.ext
  intro row column
  simp only [
    zzInteractionOperator,
    Matrix.sum_apply,
    star_sum
  ]
  apply Finset.sum_congr rfl
  intro bond _
  exact (zzBondTermOperator_isHermitian n bond).apply row column

theorem overlappingControlOperator_isHermitian
    (n : Nat) :
    (overlappingControlOperator n).IsHermitian := by
  apply Matrix.IsHermitian.ext
  intro row column
  simp only [
    overlappingControlOperator,
    Matrix.add_apply,
    star_add
  ]
  rw [
    (tiltedProductOperator_isHermitian n).apply row column,
    (zzInteractionOperator_isHermitian n).apply row column
  ]

noncomputable def twoQubitLeftTiltedOperator :
    Matrix (Fin 4) (Fin 4) Complex :=
  !![
    3 / 4, 0, -1, 0;
    0, 3 / 4, 0, -1;
    -1, 0, -3 / 4, 0;
    0, -1, 0, -3 / 4
  ]

def twoQubitZZOperator :
    Matrix (Fin 4) (Fin 4) Complex :=
  !![
    1, 0, 0, 0;
    0, -1, 0, 0;
    0, 0, -1, 0;
    0, 0, 0, 1
  ]

theorem twoQubitLeftTiltedOperator_isHermitian :
    twoQubitLeftTiltedOperator.IsHermitian := by
  apply Matrix.IsHermitian.ext
  intro row column
  fin_cases row <;> fin_cases column <;>
    norm_num [twoQubitLeftTiltedOperator]

theorem twoQubitZZOperator_isHermitian :
    twoQubitZZOperator.IsHermitian := by
  apply Matrix.IsHermitian.ext
  intro row column
  fin_cases row <;> fin_cases column <;>
    norm_num [twoQubitZZOperator]

theorem twoQubit_left_tilted_does_not_commute_with_zz :
    ¬ Commute twoQubitLeftTiltedOperator twoQubitZZOperator := by
  intro hCommute
  have hEntry :=
    congrFun
      (congrFun hCommute.eq (0 : Fin 4))
      (2 : Fin 4)
  norm_num [
    Matrix.mul_apply,
    Fin.sum_univ_succ,
    twoQubitLeftTiltedOperator,
    twoQubitZZOperator
  ] at hEntry

theorem overlapCoupling_nonzero :
    overlapCoupling ≠ 0 := by
  norm_num [overlapCoupling]

theorem overlapping_control_structural_boundary :
    overlapCoupling ≠ 0 ∧
      (nearestNeighborSupport 0).card = 2 ∧
      (nearestNeighborSupport 0 ∩
        nearestNeighborSupport 1).Nonempty ∧
      nearestNeighborSupport 0 ∪ nearestNeighborSupport 1 =
        {0, 1, 2} ∧
      ¬ Commute
        twoQubitLeftTiltedOperator
        twoQubitZZOperator := by
  exact ⟨
    overlapCoupling_nonzero,
    nearest_neighbor_support_card 0,
    adjacent_bond_supports_overlap 0,
    first_two_bonds_cover_three_sites,
    twoQubit_left_tilted_does_not_commute_with_zz
  ⟩

end ClusterStabilizer
end B9
