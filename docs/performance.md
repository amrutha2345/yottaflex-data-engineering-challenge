# Performance Benchmark Report

## 1. Objective

Compare three data-loading strategies using the same reproducible synthetic dataset:

- Full refresh
- Incremental merge
- Partition replacement

The benchmark checks execution time, output row counts, aggregate reconciliation, and output equivalence.

## 2. Benchmark Configuration

| Parameter | Value |
|---|---|
| Dataset size | 100,000 rows |
| Random seed | 42 |
| Data source | Locally generated synthetic order data |
| Storage | SQLite |
| Run ID | `a30ba8bd-15a5-49da-bc29-cea2202aec1d` |
| Run date | October 29, 2026 |
| Overall status | Success |

### Reproduce the benchmark

Run from the project root:

```powershell
python -m pipeline.cli --rows 100000 --seed 42 --output-dir data/bench_100000
```

## 3. Results

| Strategy | Output rows | Runtime (seconds) | Status |
|---|---:|---:|---|
| Full refresh | 100,000 | 0.573127 | Success |
| Incremental merge | 100,000 | 0.546134 | Success |
| Partition replacement | 100,000 | 0.546195 | Success |

All three strategies reported the same aggregate amount sum: **249,186,007.79**. The dataset does not specify a currency.

## 4. Validation and Reconciliation

The benchmark report recorded:

- Input rows: 100,000
- Valid rows: 100,000
- Rejected normal-input rows: 0
- Duplicate count in normal input: 0
- Edge-case rejects: 5
- Quarantined rows: 5
- Failed strategies: none
- Equivalent outputs: `true`

All three strategies produced 100,000 rows and matched the full-refresh baseline.

The five quarantined records came from the separate edge-case input. They are not rejections from the normal 100,000-row dataset.

## 5. Timing Definitions

The pipeline uses `time.perf_counter()` to measure elapsed time.

Strategy runtime measures the timed work for an individual strategy, including its setup and canonical output read.

Pipeline elapsed time measures from the start of the main pipeline timer until the report object is constructed. It includes data generation, validation, strategy execution, reconciliation, and other work before report construction. It excludes the final run-log and benchmark-report writes and printing.

The reported `total_elapsed_seconds` was 368.105375 seconds, approximately 6 minutes and 8 seconds. This metric has a broader scope than the individual strategy runtimes and should not be compared directly with them.

## 6. Interpretation

In this run, incremental merge and partition replacement had slightly lower measured runtimes than full refresh.

- Incremental merge was approximately 0.027 seconds faster than full refresh.
- Partition replacement was approximately 0.027 seconds faster than full refresh.

These are observations from one run, not conclusive evidence that either strategy is generally faster. Repeated trials would be needed for a more reliable comparison.

The benchmark demonstrates output equivalence for the tested synthetic dataset. It does not establish performance on real production data.

## 7. Limitations

- Data is synthetic and generated locally, not sourced from Kaggle or a live business system.
- Results represent one measured run; repeated trials and summary statistics would strengthen the comparison.
- Performance can vary with hardware, storage, Python version, and dataset characteristics.
- The benchmark uses clean target databases and does not fully represent repeated incremental updates against an existing production target.
- Partition replacement assumes the input contains a complete snapshot for every partition being replaced.

## 8. Conclusion

The 100,000-row benchmark completed successfully. All three strategies processed the expected number of rows, reported no strategy failures, and produced equivalent outputs according to the pipeline's reconciliation check.

Strategy runtimes and end-to-end pipeline elapsed time are reported separately because they measure different scopes.
