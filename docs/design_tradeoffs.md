# Design and Trade-offs

## 1. Strategy Comparison

| Strategy | Work performed | Advantages | Risks and recovery |
|---|---|---|---|
| Full refresh | Delete existing target rows and reload all valid snapshot rows. | Simple execution model; target reflects the supplied snapshot. | Rewrites all target data. The delete and reload must remain in the same transaction to prevent an exception from leaving an empty or partially loaded target. |
| Incremental merge | Insert new records and update existing records by `order_id`. Updates are applied only when the incoming `updated_at` is newer. | Efficient for change batches; primary-key enforcement prevents duplicate target keys; reruns are safe for the documented merge semantics. | Requires reliable keys and timestamps. Does not infer deletions that are absent from the input batch. |
| Partition replacement | Delete existing rows in the months represented by the incoming batch, then insert the supplied rows. | Supports monthly rebuilds and targeted backfills without rewriting unaffected months. | Assumes each included month is a complete snapshot. Partial input can remove valid records. A record moving to another month requires handling its old partition separately. |

## 2. Recovery and Failure Handling

Each strategy performs its database modifications within a SQLite transaction. If an exception occurs during the transaction, SQLite rolls back the changes made within that transaction.

The runner uses isolated databases for strategy comparisons. This keeps each strategy's result independent and supports a fair comparison on a clean target.

Recovery considerations:

- Transaction rollback: Prevents a failed database write from leaving a partially committed strategy operation.
- Safe retry: Incremental merge uses the primary key and timestamp comparison to avoid duplicating records or replacing newer data with older updates.
- Full-refresh protection: An empty full-refresh input is rejected before existing target data is deleted.
- Partition recovery: Rebuild only complete monthly snapshots. Confirm the completeness of a backfill before replacing a partition.
- Cross-strategy consistency: The strategies are executed independently; they do not share one transaction. Canonical output comparison identifies differences after processing.

These guarantees cover database transactions and the implemented retry behavior. They do not imply atomic recovery across every filesystem operation, log write, or the complete multi-strategy run.

## 3. Complexity Analysis

Let:

- `n` = number of incoming valid rows
- `m` = number of existing target rows
- `p` = number of existing rows in the affected partitions

The following are high-level estimates, not universal runtime guarantees.

| Strategy | Conceptual work | Main cost driver |
|---|---|---|
| Full refresh | `O(m + n)` for clearing and reloading rows, excluding additional indexing and validation costs. | Size of the existing target and incoming snapshot. |
| Incremental merge | Typically `O(n log m)` with indexed primary-key lookups; exact behavior depends on the database and execution plan. | Number of incoming rows and the cost of locating existing keys. |
| Partition replacement | Approximately `O(p + n)` for deleting affected rows and loading the replacement rows, excluding additional indexing and validation costs. | Size of affected partitions and incoming data. |

When partition replacement affects most or all partitions, its workload can approach that of a full refresh. When only a small subset of months is rebuilt, it can avoid rewriting unaffected rows.

Actual execution time depends on SQLite behavior, indexes, transaction settings, storage, data distribution, and the volume of input and existing data.

## 4. Design Decisions

The implementation prioritizes correctness, reproducibility, and demonstrable recovery behavior over distributed-scale throughput.

- SQLite provides a lightweight local target without requiring external infrastructure.
- A fixed-seed data generator supports repeatable experiments.
- Validation and quarantine separate invalid records from accepted records.
- Canonical output comparison checks whether all three strategies produce equivalent results for the tested input and assumptions.
- Performance reports should contain measured execution times from the actual environment, rather than theoretical estimates presented as benchmarks.

## 5. Important Assumptions

1. Full refresh receives a complete snapshot.
2. Incremental merge receives records with stable order identifiers and meaningful update timestamps.
3. Partition replacement receives complete snapshots for every month it replaces.
4. The incoming dataset is validated before strategy execution.
5. Strategy equivalence applies to the tested dataset and semantics; it is not a guarantee for every possible sequence of partial updates, deletions, or partition changes.
