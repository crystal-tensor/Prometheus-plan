# B3/B10 F1 Assembled Rows Gate

- Target: `T-B3-039/T-B10-015z`
- Method: `b3_b10_f1_assembled_rows_gate_v0`
- Status: `f1_three_remaining_rows_assembled_zero_credit`
- Row bundle hash: `64907f6c4fcdedede9e6edb0386a88bda478fc16ab06e462e3c68b1cfb2b5b53`
- Source shards: 65/65
- Assembled rows: 3/3
- F1 candidate rows: 4/4

## Result

The gate assembles the H2O, N2, and LiH row-level covariance summaries from the completed shard batches and pairs them with the existing H2 pilot candidate. It passes 8/10 requirements and intentionally fails ['P9', 'P10'] because no four-row F1 artifact has been accepted and no same-access denominator win or B3/B10 credit is allowed.

## Row Metrics

- Total assembled groups: 32251
- Total nonzero covariance pairs: 128544
- Total variance sum: 84.00917219228485
- Accepted full-covariance rows: 0
- Denominator wins: 0

## Requirements

- `P1` PASS: F1 row packet gate is current
- `P2` PASS: H2 pilot candidate row remains available
- `P3` PASS: H2O/N2/LiH shard batch gates validate
- `P4` PASS: All 65 source shards are present in the assembled row bundle
- `P5` PASS: H2O/N2/LiH rows are assembled from all completed shard batches
- `P6` PASS: Four F1 candidate rows are now present before acceptance
- `P7` PASS: Row and bundle hashes are replay-bound
- `P8` PASS: Assembled rows retain source replay and claim-boundary hashes
- `P9` FAIL: Four-row F1 artifact has been submitted and accepted
- `P10` FAIL: Same-access denominator win or B3/B10 credit is allowed

## Claim Boundary

- Supported: Three remaining F1 full-covariance rows were assembled from the completed H2O/N2/LiH shard batches and paired with the existing H2 pilot candidate as a four-row candidate bundle.
- Not supported: This is not an accepted F1 artifact, not a same-access denominator win, not B3/B10 credit, and not quantum advantage.
