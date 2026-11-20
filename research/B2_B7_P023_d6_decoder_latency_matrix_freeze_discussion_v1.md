Can a decoder be real time only when 256 memories wait in line?

The 71-active-qubit distance-6 candidate has cleared its strict X/Z reliability verifier—but its correlation-aware decoder was timed in batches of 256. That is useful throughput evidence, not yet a real-time claim.

Before measuring anything new, we are freezing a batch-size matrix on the exact first 1,024 syndromes from each verified basis:

- independent MWPM versus two-pass correlated matching;
- batch sizes 1, 4, 16, 64, and 256;
- nine timed repetitions per row after warmup;
- identical detector data and exact prediction-hash checks;
- a literature-grounded 1 microsecond/round software backlog proxy.

The outcome cannot promote a hardware deadline. The experiment is offline, uses complete 1,000-round blocks, and excludes communication, control, feedback, online windowing, and tail response time.

Questions before execution:

- If batch 256 passes but batch 1 fails, is that a scalable throughput win or a latency failure?
- Should every hardware platform declare its own syndrome-cycle budget instead of using 1 microsecond/round?
- Should 26 saved physical qubits and extra classical work remain a Pareto pair rather than being collapsed into one score?
- What minimum online-window and tail-latency evidence should be mandatory before calling a QEC decoder real time?

After this public freeze, the runner will reproduce all eight source chunk hashes and execute exactly the declared 20-row timing matrix.
