# If 99% of the topology is shared, what still has to change with the phase?

Opening, steady, and closing looked like three different decoder graphs. After translating phase-local detector numbers back into circuit coordinates relative to each window, the topology turns out to be highly reusable.

The X superset needs 3,762 edges, only 0.858% more than its largest phase image. Z needs 3,756, only 0.832% more. Compared with storing three separate topologies, the unions retain about 39.2% of the total edge count. Opening and steady alone share more than 96.7% by edge-set Jaccard overlap.

But a mask alone would be wrong.

- X and Z each have 76 shared edges whose base weight changes with phase.
- 370 X and 371 Z shared rule pairs change their replacement weight.
- Fault-output dimensions grow from 229/228 at opening to 789/788 at closing.
- Growth bounds, virtual boundaries, and fault maps also remain phase-specific.

So the current route is a shared topology with phase-banked semantics: masks, base weights, resident rules, growth bounds, and fault/output maps must switch atomically at a quiescent Reset boundary. A machine-checkable mapping plan now reconstructs all six source images and passes 137/137 audit checks.

Which state would you insist on banking, and which state could safely remain shared?

1. Bank only masks, weights, and rules; derive the rest from the active graph.
2. Bank growth bounds and fault/output maps as well, accepting more storage for a smaller proof surface.
3. Avoid the semantic mux entirely and time-multiplex three independent engines.

What is the minimal invariant that proves an inactive edge can never become tight, participate in a conflict, or leak a stale correction across a phase transition?

This is still a mapping plan, not runtime-switching RTL. Complete corrections, FPGA timing/resources, p99 `<=1 us`, miss `<=1%`, full B2, scalable #023, and B7 credit remain open.
