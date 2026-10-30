# Validation and Reconciliation Report

## 1. Objective

Verify that the three SQLite loading strategies produce equivalent canonical outputs when processing the same validated input dataset.

## 2. Test Configuration

- Command: `python -m pipeline.cli --rows 1000 --seed 42`
- Requested input rows: 1,000
- Random seed: 42
- Loading strategies: Full Refresh, Incremental Merge, Partition Replacement

## 3. Results

| Metric | Full Refresh | Incremental Merge | Partition Replacement |
|---|---:|---:|---:|
| Output row count | 1,000 | 1,000 | 1,000 |
| Amount total | 2,562,413.39 | 2,562,413.39 | 2,562,413.39 |
| Strategy status | Success | Success | Success |
| Matches full-refresh baseline | Yes | Yes | Yes |

Reported overall pipeline status: Success

Reported canonical output equivalence: True

Reported input validation results:
- Valid input rows: 1,000
- Rejected input rows: 0
- Duplicate rows: 0
- Generated edge-case rows quarantined: 5

*Verification note: Confirm these figures against the actual 1,000-row CLI output before treating them as final measured evidence.*

## 4. Reconciliation Approach

The pipeline compares canonical outputs from each loading strategy against the full-refresh baseline.

The canonical output contains the order ID, customer ID, order date, order month, amount, status, and update timestamp. Rows are ordered by order ID before comparison.

The report also compares output row counts and aggregate amount totals to detect differences between strategies.

## 5. Automated Test Evidence

The latest confirmed full test run completed successfully:

- Tests run: 19
- Passed: 19
- Failed: 0
- Execution time: 0.43 seconds

Coverage includes duplicate handling, conflicting duplicates, invalid data, malformed CSV rows, empty input, schema validation, incremental merge idempotency, transaction rollback, late-arriving updates, empty full-refresh protection, partition replacement, and strategy equivalence.

## 6. Conclusion

The reported 1,000-row results indicate that all three loading strategies completed successfully and produced equivalent canonical outputs for the tested dataset.

The automated test suite also passed all 19 tests in the confirmed full test run.

These results support correctness for the tested scenarios. Larger datasets and additional failure scenarios should be tested separately. Performance claims should be based on recorded benchmark measurements.

