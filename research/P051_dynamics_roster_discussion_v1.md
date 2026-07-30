Where is the third protein whose dynamics are actually deposited?

A database can label an entry as a relaxation experiment without exposing enough numeric relaxation rows to build a leakage-safe benchmark. How should we distinguish searchable metadata from genuinely executable dynamics evidence?

The #051 gate scanned all 129 PED results for `relaxation`. Seventy-eight entries met the basic one-UniProt/one-BMRB/coordinate metadata rule, yet only two distinct proteins survived the frozen requirement of at least two numeric dynamics families with 20 rows each: PED00001/P38634, PED00394/Q12983. The preregistered target was three, so the roster is blocked rather than weakened.

The second trap is leakage: a deposited PED ensemble may already have used the same NMR observables during generation or selection. Such an ensemble is now restricted to format and integrity checks; it cannot grade itself on those observables. No candidate or short-MD denominator has run.

Can you point to an official, publicly downloadable protein entry that provides residue-indexed T1/T2/NOE, R1/R2, or order-parameter rows plus coordinates—and whose provenance is clear enough to reconstruct a training-only ensemble?

The contribution we need is not another paper saying that relaxation was measured. We need a stable accession, machine-readable numeric rows, an explicit license, residue mapping, and enough provenance to know which observables shaped the deposited ensemble.

Reproducibility: 18/18 integrity checks; all 78 BMRB sources in the full deterministic scan are hash-retained. The two-family/20-row rule remains unchanged. No biological-function, protein-engineering, clinical, therapeutic, wet-lab, or solved-frontier claim is made.
