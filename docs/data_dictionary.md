# Data Dictionary

## Dataset: Orders

Each row represents an order record processed by the data engineering pipeline. The pipeline validates source records, applies duplicate-handling rules, derives a monthly partition key, and loads accepted records using one of three strategies: full refresh, incremental merge, or partition replacement.

### 1. Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `order_id` | String | Yes | Unique order identifier and target-table primary key. |
| `customer_id` | String | Yes | Customer identifier. Must match a known customer reference. |
| `order_date` | ISO date string | Yes | Date the order was placed, formatted as `YYYY-MM-DD`. |
| `order_month` | String | Derived | Monthly partition key derived from `order_date`, formatted as `YYYY-MM`. |
| `amount` | Numeric | Yes | Order amount. Must be numeric, finite, and greater than or equal to zero. |
| `status` | String | Yes | Order status. Accepted values are `pending`, `paid`, `shipped`, and `cancelled`. |
| `updated_at` | ISO 8601 timestamp string | Yes | Timestamp of the latest order update. Must include a timezone. |
| `source_file` | String | Yes | Name of the source file from which the accepted record originated. |

### 2. Keys and Relationships

- **Primary key:** `order_id`
- **Partition key:** `order_month`
- **Customer reference:** `customer_id`, validated against the known customer set supplied to the validation process.

The target table enforces uniqueness through the `order_id` primary key. Customer reference validation is performed by the application; the target schema does not define a database foreign-key constraint.

### 3. Validation Rules

1. The input must contain all required columns.
2. Missing or unexpected schema columns cause validation to fail fast.
3. Required field values must not be null or blank.
4. Malformed CSV records, including rows with extra fields, are quarantined with a rejection reason.
5. `order_date` must be a valid ISO date.
6. `order_month` is derived from `order_date` and must reflect the same calendar month.
7. `amount` must be numeric, finite, and non-negative.
8. `status` must belong to the allowed status set.
9. `updated_at` must be a valid timezone-aware ISO 8601 timestamp.
10. `customer_id` must reference a known customer.
11. Duplicate order IDs are handled according to the implemented duplicate policy.

### 4. Duplicate-Handling Policy

- Exact duplicates: One record is retained; additional duplicate occurrences are rejected.
- **Conflicting duplicates:** The record with the latest `updated_at` is retained when the latest timestamp identifies an unambiguous record.
- Tied latest timestamps: Conflicting records tied at the latest timestamp are quarantined.
- **Incremental merge:** An existing record is updated only when the incoming timestamp is newer than the stored timestamp. Older or equal-timestamp updates are ignored.

These rules support deterministic processing and reduce the risk of older data overwriting newer records.

### 5. Reject and Quarantine Data

Rejected records are separated from accepted records. The reject output retains available source-record details and records a rejection reason to support investigation and correction.

The pipeline distinguishes between:

- Normal input rejects: Invalid records found in the generated source dataset.
- Edge-case rejects: Invalid records deliberately generated to demonstrate validation behavior.
- Total quarantined records: The combined count of normal input rejects and edge-case rejects, as reported by the current CLI.

Duplicate records and other validation failures may contribute to reject counts according to the validation policy.

### 6. Output Metrics

| Metric | Meaning |
|---|---|
| `input_count` | Number of records read from the normal source dataset. |
| `valid_count` | Number of accepted records from the normal source dataset. |
| `reject_count` | Number of rejected records from the normal source dataset. |
| `edge_case_reject_count` | Number of rejected records in the deliberately generated edge-case dataset. |
| `quarantined_row_count` | Combined number of normal-input and edge-case records quarantined by the current CLI. |
| `output_count` | Number of records in the target table after processing. |
| `amount_sum` | Sum of the target table's order amounts. |
| `elapsed_seconds` | Observed elapsed time for a strategy run. |
| `status` | Indicates whether the strategy completed successfully or failed. |
| `failure_reason` | Description of the error when a strategy fails, if captured by the report. |
| `equivalent_outputs` | Indicates whether the canonical outputs of the three strategies match. |

Metrics should be interpreted according to their specific counting definitions. In particular, `input_count` does not include the separate edge-case dataset.

### 7. Data Quality and Reconciliation

For each completed run:

1. Reconcile normal source counts using the pipeline's counting definitions.
2. Compare the canonical output records from all three strategies.
3. Verify primary-key uniqueness and absence of null keys.
4. Compare business aggregates, including total order amount and, where implemented, monthly totals.
5. Record observed execution times and strategy status.
6. Investigate any mismatched records, unexplained count differences, or failed strategies.

The CLI benchmarks strategies using freshly initialized target databases. Its benchmark therefore compares clean-target processing rather than measuring the cost of updating an already populated production target.

### 8. Known Assumptions and Limitations

- Customer references are checked against the customer set supplied to validation.
- Incremental merge assumes that a later `updated_at` timestamp represents a newer version of an order.
- Partition replacement assumes the incoming batch contains the complete snapshot for each month being replaced. Partial monthly batches could otherwise remove valid existing records.
- An empty full-refresh batch is rejected to protect existing target data.
- Performance figures represent the environment and dataset size used for the specific benchmark run; they should not be generalized without further testing.
