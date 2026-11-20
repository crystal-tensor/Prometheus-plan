# B2/B7/#023 phase-superset mapping plan v1

## Question

If opening, steady, and closing can share more than 99% of the largest topology, why is runtime phase switching still not free?

## Canonical topology mapping

The six frozen X/Z Micro Blossom images use phase-local detector and edge numbering. The mapping plan recompiles the exact accepted windows, translates every detector into its circuit coordinate relative to the window start, and builds one canonical topology per basis. It observes zero new stochastic samples.

For X, the union contains 1,147 vertices and 3,762 edges, only 2.87% and 0.858% above the largest closing image. For Z, it contains 1,142 vertices and 3,756 edges, 2.79% and 0.832% above the largest image. The union edge counts are only 39.17% and 39.15% of three separately stored phase topologies.

Opening and steady share 2,890 X edges and 2,886 Z edges, with Jaccard overlap 96.85% and 96.75%. Closing introduces the larger boundary tail, but its edge overlap with steady remains 2,952 in both bases.

## Why a mask alone is incorrect

Topology sharing does not imply semantic sharing:

- each basis has 76 shared canonical edges whose base weight changes with phase;
- 370 X and 371 Z shared source/target rule pairs have phase-dependent replacement weights;
- X fault-output dimensions are 229/246/789 for opening/steady/closing, while Z is 228/246/788;
- vertex growth bounds, virtual-boundary participation, and fault maps are phase-specific.

The selected route is therefore a masked superset with phase-banked base weights, resident rules, growth bounds, and fault/output maps. Phase selection must be atomic, and a phase transition is legal only at a quiescent reset boundary.

## Machine-checkable plan

The plan stores injective local-to-superset vertex and edge maps, phase masks, local-order base weights, vertex growth bounds, translated active resident rules, and fault IDs for all six images. Every translated rule source and target remains inside its phase mask.

The audit reconstructs every source-image endpoint, weight, growth entry, fault map, and active rule and passes `137/137`. Plan evidence ID: `38031dd8b61ff8d0a1a326b13eb5bd7a931084f4d72d62936cc14991091cc1cc`. Result evidence ID: `6c536a2323d0c562d06b5d4a865756950803c3d54ab955eee2f8691ad1a05684`.

## Claim boundary

No masked-superset RTL, runtime phase switch, complete correction comparison, FPGA Fmax, LUT/BRAM, routing closure, or update-plus-decode p99 has been demonstrated. Consequently p99 `<=1 us`, miss `<=1%`, full B2, scalable #023, and B7 resource credit remain false, false, false, false, and zero.

The next gate is a one-basis superset RTL prototype that selects all phase-banked semantics atomically at Reset, rejects inactive selectors and targets, and replays opening-to-steady-to-closing transitions against the three independent frozen images.
