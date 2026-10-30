# Data Pipeline: Load Strategy Comparison

A Python-based data engineering project that implements and compares three data-loading strategies using SQLite and CSV files: **Full Refresh, Incremental Merge, and Partition Replacement**.

## 1. Project Overview

This project evaluates three approaches to loading order data into a target database. It focuses on data quality, correctness, reproducibility, transaction safety, performance measurement, and output reconciliation.

The pipeline generates synthetic order data, validates incoming records, separates rejected records, executes the three loading strategies, and compares their outputs.

## 2. Objectives

- Build a reproducible and configurable data pipeline.
- Implement three different data-loading strategies.
- Validate schemas and business rules.
- Handle duplicate and invalid records.
- Support safe reruns under documented assumptions.
- Measure strategy execution times.
- Verify output equivalence through reconciliation.
- Test normal, invalid, and edge-case scenarios.

## 3. Architecture

```text
Synthetic Data Generator
          |
          v
       CSV Input
          |
          v
    Schema Validation
          |
          v
   Business Rule Checks
       /          \
      v            v
Valid Records  Rejected Records
      |            |
      v            v
 Load Strategies  Reject CSV
      |
      +-----------------------+
      |           |           |
      v           v           v
 Full Refresh  Incremental  Partition
                 Merge      Replacement
      |           |           |
      +-----------+-----------+
                  |
                  v
       Reconciliation and Metrics
                  |
                  v
       Benchmark Report and Run Log
                  |
                  v
             SQLite Outputs
```

## 4. Loading Strategies

| Strategy | Description | Main consideration |
|---|---|---|
| Full Refresh | Replaces the target dataset with a validated snapshot. | Simple replacement, but reloads the complete dataset. |
| Incremental Merge | Inserts new records and updates existing records using `order_id`. | Updates only when the incoming timestamp is newer. |
| Partition Replacement | Deletes and reloads affected monthly partitions. | Requires complete snapshots for the partitions being replaced. |

### Key implementation decisions

- `order_id` is used as the record key.
- Incremental updates use `updated_at` to prevent stale records from overwriting newer ones.
- Empty full-refresh input is rejected to protect existing target data.
- Conflicting duplicate records with tied latest timestamps are quarantined.
- Partition replacement operates on the months represented in the incoming dataset.

## 5. Technology Stack

- Python 3
- SQLite
- CSV
- Python `unittest`
- Python standard-library modules

No external Python packages are required for the current implementation.

## 6. Project Structure

```text
yottaflex_data_engineering_challenge/
│
├── README.md
│
├── pipeline/
│   ├── __init__.py
│   ├── generator.py
│   ├── validation.py
│   ├── strategies.py
│   ├── cli.py
│   └── observability.py
│
├── tests/
│   └── test_pipeline.py
│
├── docs/
│   ├── ai_prompts.md
│   ├── data_dictionary.md
│   ├── design_tradeoffs.md
│   ├── recovery_strategy.md
│   └── performance.md
│
└── data/
    └── output/
```

Generated benchmark reports, CSV files, logs, and SQLite databases are stored in the configured output directories.

*Adjust this tree to match the files actually committed to the repository.*

## 7. Prerequisites

- Python 3.10 or later recommended.
- Windows, macOS, or Linux.
- Git (only required for repository publishing).

Check your Python installation:

```powershell
python --version
```

## 8. Installation and Execution

Clone the repository:

```powershell
git clone https://github.com/YOUR_USERNAME/yottaflex-data-engineering-challenge.git
```

Navigate into the project:

```powershell
cd yottaflex-data-engineering-challenge
```

Run the pipeline with 1,000 synthetic rows:

```powershell
python -m pipeline.cli --rows 1000 --seed 42
```

The fixed random seed supports reproducible input generation when the generator implementation remains unchanged.

### Run automated tests

```powershell
python -m unittest discover -s tests -v
```

### Run the 100,000-row benchmark

```powershell
python -m pipeline.cli --rows 100000 --seed 42 --output-dir data/bench_100000
```

## 9. Outputs

Depending on the configured output directory, the pipeline generates:

- Benchmark report (`benchmark_report.json`).
- Execution log (`run_log.csv`).
- Rejected-record CSV.
- SQLite databases containing strategy outputs.
- Run metadata and reconciliation results.

## 10. Benchmark Results

The following results were recorded from a 100,000-row synthetic dataset using seed 42.

| Metric | Recorded result |
|---|---:|
| Input rows | 100,000 |
| Valid rows | 100,000 |
| Normal-input rejected rows | 0 |
| Edge-case rejected rows | 5 |
| Failed strategies | 0 |
| Equivalent outputs | True |
| Overall status | Success |

### Strategy performance

| Strategy | Output rows | Runtime |
|---|---:|---:|
| Full Refresh | 100,000 | 0.573127 seconds |
| Incremental Merge | 100,000 | 0.546134 seconds |
| Partition Replacement | 100,000 | 0.546195 seconds |

<text>Recorded total pipeline elapsed time: 368.105375 seconds.</text>

**Timing note:** Individual strategy runtimes and total pipeline elapsed time measure different scopes. The total includes broader pipeline processing and reconciliation, so it should not be interpreted as the sum of the three strategy runtimes.

These are recorded results from one execution, not guaranteed production performance figures.

## 11. Correctness and Reconciliation

The pipeline compares the outputs of all three strategies against the full-refresh baseline.

Correctness is evaluated using:

- Canonical record ordering.
- Record-level comparison.
- Output row counts.
- Aggregate amount comparisons.
- Strategy success or failure status.

Equal row counts alone do not prove that two datasets contain identical records.

## 12. Data Quality and Validation

The validation process checks:

- Required columns and schema.
- Missing values.
- Customer references.
- Date and timestamp validity.
- Numeric and non-negative amounts.
- Valid order statuses.
- Duplicate order IDs.

Invalid records are separated from valid records and written to a reject output for inspection.

## 13. Testing

The project includes automated tests for pipeline behavior, data validation, and loading strategies.

Previously reported test evidence: **19 tests passed** in a full test run.

Run the test suite before submission to confirm the current result:

```powershell
python -m unittest discover -s tests -v
```

Additional verification should cover transaction rollback, retry behavior, late-arriving records, partition changes, and reconciliation at larger data volumes where applicable.

## 14. Assumptions and Limitations

- The dataset is synthetically generated and does not represent live customer data.
- `order_id` is the primary record key.
- Incremental merge does not infer deletions without explicit deletion events or reconciliation.
- Partition replacement assumes complete snapshots for affected monthly partitions.
- Benchmark timings depend on the local machine, database state, and execution environment.
- The recorded benchmark represents one execution and should not be treated as a production performance guarantee.
- Production deployment would require additional orchestration, monitoring, access controls, and operational recovery procedures.

## 15. Documentation

Additional project documentation:

- `docs/ai_prompts.md` – AI-assisted development prompts and key technical decisions.
- `docs/data_dictionary.md` – Dataset fields and validation expectations.
- `docs/design_tradeoffs.md` – Strategy comparison, complexity, and design decisions.
- `docs/recovery_strategy.md` – Transaction safety and recovery considerations.
- `docs/performance.md` – Benchmark results and performance interpretation.

Include only files that actually exist in the repository.

## 16. AI Usage Disclosure

ChatGPT and Claude were used as development assistants for architecture discussions, implementation guidance, debugging, testing, code review, benchmarking, and documentation.

The AI prompt history contains reconstructed summaries rather than verbatim transcripts. Implementation decisions and benchmark results should be independently verified.

## 17. Author

**Project:** Data Pipeline – Load Strategy Comparison

**Purpose:** Demonstrate foundational data engineering skills in data validation, database loading strategies, testing, reconciliation, and performance analysis.
