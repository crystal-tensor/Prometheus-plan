# If you could afford 335 qubits, which corner of a surface code would you remove?

A 449-qubit surface-code simulation passed four independent million-round tests: each used 1,024 trajectories, and the X/Z results, with and without paired-readout stress, had 0–2 failures per cell. A 287-qubit square code had already failed in stressed X. Instead of lowering the bar, we removed one corner of a slightly larger patch to keep more X protection. The resulting 335-qubit circuit passed four 1,000-round cells; its million-round test is underway.

**Which failure would you expect first: a bad readout pair near the removed check, an ordinary error string outside that corner, or a decoder-window seam?** What is the smallest test that would distinguish those explanations without looking at the final logical outcome first?

[Results, fixed acceptance rule, and independent audit](https://github.com/crystal-tensor/Prometheus-plan/blob/main/research/P023_d15_million_acceptance_and_B2_corner335_v1.md)
