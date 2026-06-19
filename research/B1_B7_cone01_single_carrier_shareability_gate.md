# B1/B7 Cone_01 Single-Carrier Shareability Gate

Status: `cone01_single_carrier_shareability_negative_gate`

This artifact consumes T-B1-004v and checks whether the exact carrier packets can be shared or coalesced into countable B7 resource objects.

## Summary

- Source exact packets / covered occurrences: `3` / `11`
- Carrier signatures / shareable objects: `3` / `3`
- Cross-pattern shareable signatures: `0`
- Largest signature occurrence count: `8`
- Optimistic duplicate occurrences / proxy-T reuse: `8` / `160`
- All shared objects accepted clears B7 target: `False`
- Missing occurrences if all shared objects accepted: `19`
- Accepted occurrence/proxy-T reduction: `0` / `0`
- Validation errors: `0`

## Shareability Rows

| Carrier object | Patterns | Occurrences | Cross-pattern | Optimistic reuse | Accepted reduction |
|---|---|---:|---|---:|---:|
| `theta_delta\|-1.0\|x\|target\|left\|I\|I\|I\|I\|-0.212636701233` | flat_pattern_02 | 2 | False | 20 | 0 |
| `theta_delta\|1.0\|x\|target\|right\|I\|I\|I\|I\|-0.364857351786` | flat_pattern_01 | 8 | False | 140 | 0 |
| `theta\|-1.0\|x\|target\|left\|I\|SSHSSH\|I\|SS\|-2.81346844784` | flat_pattern_03 | 1 | False | 0 | 0 |

## Claim Boundary

- The carrier packets remain exact packets from T-B1-004u.
- They split into three distinct carrier signatures, with no cross-pattern coalescence under the current signature model.
- Optimistic within-pattern reuse is 160 proxy-T, below the 600 proxy-T B7 target and not accepted by the current ledger.
- Even accepting all three carrier objects would cover only 11 occurrences and still miss by 19.
- No rewrite, semantic certificate, physical cost model, or B7 ledger improvement is claimed.
