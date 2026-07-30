# P051 public protein-dynamics roster v1

**Decision:** `blocked_insufficient_machine_readable_dynamic_observables`.

## What the access gate asked

Can a benchmark roster be assembled from public machine-readable sources without letting an ensemble trained on every restraint grade itself? The deterministic scan starts from the complete PED `relaxation` search, requires one UniProt accession, one BMRB cross-reference, at least two numeric dynamics-observable families, and a downloadable coordinate ensemble.

## Selected roster

| PED | UniProt | BMRB | Qualifying dynamic families | Coordinate models |
|---|---|---|---|---:|
| [PED00001](https://proteinensemble.org/entries/PED00001) | [P38634](https://www.uniprot.org/uniprotkb/P38634/entry) | [16659](https://bmrb.io/data_library/summary/index.php?bmrbId=16659) | heteronuclear_noe (74), t1 (74), t2 (74) | 11 |
| [PED00394](https://proteinensemble.org/entries/PED00394) | [Q12983](https://www.uniprot.org/uniprotkb/Q12983/entry) | [7288](https://bmrb.io/data_library/summary/index.php?bmrbId=7288) | heteronuclear_noe (38), t1 (38), t2 (38) | 16 |

The number in parentheses is the machine-parsed count of numeric rows in that BMRB observable family. Every screened source before the deterministic scan ended, plus selected PED metadata and coordinate archives, is retained with SHA-256 hashes.

## The important leakage result

A PED entry can label an experiment as `relaxation` without its linked BMRB file containing numeric relaxation loops. More importantly, a deposited PED ensemble may already have been generated or selected using those same observables. It is therefore a source-format and integrity reference only: it cannot predict an observable as held-out evidence if that observable helped construct the ensemble.

Any future candidate must be regenerated from training observables only. Leave-one-protein-out evaluation must exclude every observable from the held-out UniProt accession while fitting model choices. Single-structure and short-MD denominators must share the same public inputs, forward models, and sampling ledger.

## What is—and is not—ready

- Formal source/access checks: `18/18`
- PED search rows retained: `129`
- Metadata-eligible BMRB sources screened in the full deterministic scan: `78`
- Candidate ensemble executed: `false`
- Short-MD denominator executed: `false`

The roster is blocked at two of three required distinct proteins. The next step is to add a separately preregistered public source layer or locate another official BMRB/PED deposition that satisfies the unchanged two-family, 20-row rule. The threshold is not weakened and no model execution begins.

This packet does not evaluate AlphaFold, a force field, an ensemble generator, or biological function.

## Official sources

- [PED API v5 specification](https://proteinensemble.org/assets/openapi.yaml) — programmatic entry search and downloadable coordinate assets under CC BY 4.0.
- [BMRB data policy](https://bmrb.io/bmrb/data_accepted.shtml) — public-domain NMR data including relaxation and order-parameter categories.

No protein-engineering, clinical, therapeutic, wet-lab, or solved-frontier claim is made.
