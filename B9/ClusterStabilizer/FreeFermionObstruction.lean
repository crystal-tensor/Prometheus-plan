import B9.ClusterStabilizer.OverlappingControl

namespace B9
namespace ClusterStabilizer

abbrev SpinVector := Fin 3 → ℚ

def spinDot (left right : SpinVector) : ℚ :=
  ∑ axis, left axis * right axis

def tiltedFieldVector : SpinVector :=
  ![-1, 0, 3 / 4]

def isingCouplingAxis : SpinVector :=
  ![0, 0, 1]

def standardJWQuadraticAxisCondition
    (fieldAxis couplingAxis : SpinVector) : Prop :=
  spinDot fieldAxis couplingAxis = 0

def fieldCouplingSquaredAlignment : ℚ :=
  (spinDot tiltedFieldVector isingCouplingAxis) ^ 2 /
    (spinDot tiltedFieldVector tiltedFieldVector *
      spinDot isingCouplingAxis isingCouplingAxis)

theorem tilted_field_dot_ising_axis :
    spinDot tiltedFieldVector isingCouplingAxis = 3 / 4 := by
  norm_num [
    spinDot,
    tiltedFieldVector,
    isingCouplingAxis,
    Fin.sum_univ_succ
  ]

theorem tilted_field_norm_squared :
    spinDot tiltedFieldVector tiltedFieldVector = 25 / 16 := by
  norm_num [
    spinDot,
    tiltedFieldVector,
    Fin.sum_univ_succ
  ]

theorem ising_axis_norm_squared :
    spinDot isingCouplingAxis isingCouplingAxis = 1 := by
  norm_num [
    spinDot,
    isingCouplingAxis,
    Fin.sum_univ_succ
  ]

theorem field_coupling_squared_alignment :
    fieldCouplingSquaredAlignment = 9 / 25 := by
  norm_num [
    fieldCouplingSquaredAlignment,
    tilted_field_dot_ising_axis,
    tilted_field_norm_squared,
    ising_axis_norm_squared
  ]

theorem dot_preserving_map_keeps_field_coupling_overlap
    (rotate : SpinVector → SpinVector)
    (hDot :
      ∀ left right,
        spinDot (rotate left) (rotate right) =
          spinDot left right) :
    spinDot
        (rotate tiltedFieldVector)
        (rotate isingCouplingAxis) =
      3 / 4 := by
  rw [
    hDot,
    tilted_field_dot_ising_axis
  ]

theorem no_dot_preserving_rotation_satisfies_standard_jw_condition
    (rotate : SpinVector → SpinVector)
    (hDot :
      ∀ left right,
        spinDot (rotate left) (rotate right) =
          spinDot left right) :
    ¬ standardJWQuadraticAxisCondition
      (rotate tiltedFieldVector)
      (rotate isingCouplingAxis) := by
  intro hCondition
  unfold standardJWQuadraticAxisCondition at hCondition
  have hOverlap :=
    dot_preserving_map_keeps_field_coupling_overlap rotate hDot
  linarith

theorem standard_jw_rotation_obstruction_boundary
    (rotate : SpinVector → SpinVector)
    (hDot :
      ∀ left right,
        spinDot (rotate left) (rotate right) =
          spinDot left right) :
    spinDot tiltedFieldVector isingCouplingAxis = 3 / 4 ∧
      fieldCouplingSquaredAlignment = 9 / 25 ∧
      ¬ standardJWQuadraticAxisCondition
        (rotate tiltedFieldVector)
        (rotate isingCouplingAxis) := by
  exact ⟨
    tilted_field_dot_ising_axis,
    field_coupling_squared_alignment,
    no_dot_preserving_rotation_satisfies_standard_jw_condition rotate hDot
  ⟩

end ClusterStabilizer
end B9
