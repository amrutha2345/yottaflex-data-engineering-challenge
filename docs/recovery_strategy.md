# Recovery Strategy

## 1. Failure Handling

The pipeline validates input data before loading accepted records into the target database. Invalid records are rejected or quarantined according to the implemented validation rules, while valid records proceed to the selected load strategy.

Database modifications are performed within SQLite transactions. If a database operation fails during a load transaction, the transaction is rolled back so that uncommitted changes from that transaction are not retained.

Schema errors, such as missing or unexpected columns, cause validation to fail fast. Invalid records, such as malformed rows, duplicate records, invalid amounts, and unknown customer references, are handled according to the validation and duplicate-resolution policies.

## 2. Retry Strategy

A failed run can be retried using the same input file and configuration. The input should remain unchanged during a retry to support reproducibility.

- Full refresh: Reloads the target from the supplied snapshot. Empty input is rejected before existing target data is deleted.
- Incremental merge: Uses `order_id` as the primary key and updates an existing record only when the incoming `updated_at` timestamp is newer. Reprocessing the same input does not create duplicate target keys.
- Partition replacement: Replaces the months represented in the input. The input must contain a complete snapshot for every month being replaced.

A retry should use the same source data and intended strategy. If the source data or configuration changes, the resulting output may also change.

## 3. Restart Strategy

The current implementation restarts processing by rerunning the pipeline from its input file. It does not implement checkpoint-based continuation from the middle of a failed run.

Each strategy performs its database modifications within a transaction. A failed database transaction rolls back its uncommitted changes. The pipeline can then be rerun after the underlying issue has been corrected.

The transaction guarantee applies to the database load operation. It does not imply atomicity across all pipeline stages, log writes, report generation, or multiple independent strategy runs.

## 4. Backfill Strategy

Historical records can be reprocessed by supplying the relevant historical input.

- Full refresh: Use when the input represents the complete dataset that should exist in the target.
- Incremental merge: Use when records should be inserted or updated according to `order_id` and `updated_at`.
- Partition replacement: Use when complete snapshots are available for the affected months.

Before performing partition replacement, verify that the input contains every expected record for each affected month. Otherwise, existing records absent from the incoming snapshot may be deleted.

For records whose `order_date` changes to another month, ensure the old partition is also handled appropriately. The current partition-replacement approach operates on the months represented by the incoming rows and does not independently discover all previous locations of changed records.

## 5. Operational Verification

After a run or recovery attempt:

1. Review pipeline logs for errors and failed strategy events.
2. Review validation, rejection, and quarantine counts.
3. Compare source and target row counts using the pipeline's documented counting definitions.
4. Compare canonical records across strategies and verify key integrity.
5. Compare business aggregates, including total order amount and monthly totals where available.
6. Review `run_log.csv` and `benchmark_report.json`.
7. Confirm that all required strategies completed successfully and that the outputs are equivalent for the tested input.

Do not treat equal row counts alone as proof of correctness. Differences in keys, field values, or business aggregates may still exist.

## 6. Current Limitations

The current pipeline does not implement:

- Automatic retry with backoff.
- Checkpoint-based recovery or resumption.
- Scheduled or automated historical backfills.
- A shared atomic transaction across all three strategies.
- Automatic change-data capture for deletions or records moved between partitions.

Recovery is initiated manually by rerunning the CLI with the intended input and configuration. These limitations should be considered when adapting the prototype for production use.
