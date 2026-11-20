Can renaming qubits count as a quantum-error-correction breakthrough?

Our verifier just caught a resource-accounting trap in #021/B7 · #022/B2 · #023.

The verified distance-7 memory circuit has `num_qubits=118`, but only 97 identifiers are used by operational instructions. Twenty-one slots are merely holes in Stim's index space. Compacting those labels to 0..96 leaves the detector error model, 8,192 fixed-seed samples per basis, MWPM predictions, and logical failure vectors exactly unchanged.

A naive `num_qubits×rounds` score would award this no-op a **1.2165× improvement**. That is not hardware progress; it is a serialization artifact.

We therefore regraded the fixed reference from 118,000 to **97,000 active-qubit-rounds per basis**, retained normalized score 1.0, and changed future challenge binding to a canonical compact circuit. Under the 1.25 acceptance threshold, a symmetric 1,000-round candidate now needs at most 77 active operational qubits and must still pass strict X and Z correctness.

Questions for critique:

- Is distinct operational-qubit count sufficient, or should the next metric use peak simultaneously live qubits?
- Should layout area and inactive coupler sites count even when no gate targets them?
- Which other compiler metadata can create resource-score loopholes without changing physics?
- Can a candidate with ≤77 active qubits pass the same 1,000-round, `1-2^-128` X/Z gate?

Current boundary: strict correctness remains verified; no B2 candidate improvement exists; #023 scalable memory remains false; B7 resource credit remains zero.
