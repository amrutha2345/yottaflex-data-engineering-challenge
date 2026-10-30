# Data Pipeline: Load Strategy Comparison

## Overview

This project implements and compares three data-loading strategies using Python, SQLite, and CSV files:

1. **Full Refresh** — replaces the target dataset with a validated snapshot.
2. **Incremental Merge** — inserts new records and updates existing records using `order_id`.
3. **Partition Replacement** — replaces affected monthly partitions.

The pipeline validates input records, separates invalid records into a reject file, records operational metrics, and compares strategy outputs for correctness.

## Objectives

- Build a reproducible, configurable data pipeline.
- Validate schemas and business rules.
- Handle duplicate and invalid records.
- Make reruns safe under documented assumptions.
- Compare load strategies using runtime and reconciliation results.
- Test normal, empty, and invalid-input scenarios.

## Architecture

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
      /         \
     v           v
 Valid Records   Rejected Records
     |           |
     v           v
 Load Strategies Reject CSV
     |
     +---------------------+
     |          |          |
     v          v          v
 Full       Incremental  Partition
 Refresh      Merge     Replacement
     |          |          |
     +----------+----------+
                |
                v
     Reconciliation and Metrics
                |
                v
 Benchmark Report, Run Log, SQLite
```

## Technology Stack

- Python 3
- SQLite
- CSV
- Python `unittest`
- Standard-library modules

No external Python packages are required for the current implementation.

## Project Structure

```text
yottaflex_data_engineering_challenge/
├── README.md
├── pipeline/
│   ├── __init__.py
│   ├── validation.py
│   ├── strategies.py
│   ├── generator.py
│   └── cli.py
├── tests/
│   └── test_pipeline.py
├── docs/
│   ├── data_dictionary.md
│   ├── design_tradeoffs.md
│   └── test_evidence.txt
└── data/
    └── output/
```

Generated files may appear in additional data directories depending on the CLI configuration.

## Prerequisites

- Python 3.10 or later recommended.
- Windows PowerShell, Command Prompt, macOS Terminal, or Linux shell.
- Git is needed only when publishing the repository.

Check Python:

```powershell
python --version
```

## Setup and Run

Open a terminal in the project root directory.

Run the pipeline with 1,000 synthetic rows and a fixed random seed:

```powershell
python -m pipeline.cli --rows 1000 --seed 42
```

Run the automated tests:

```powershell
python -m unittest discover -s tests -v
```

The fixed seed makes synthetic input generation reproducible when the generator implementation remains unchanged.

## Outputs

Inspect the generated output directory for:

- Benchmark report containing run metadata and strategy timings.
- Run log containing strategy status and row counts.
- Rejected-record CSV, if any records fail validation.
- SQLite databases containing strategy output tables.

Exact filenames depend on the current CLI implementation.

## Correctness and Reconciliation

The pipeline compares the outputs produced by the three strategies against the full-refresh result. Correctness should be assessed using primary keys and record values, as well as row counts and business aggregates.

Equal row counts alone do not prove that two datasets contain identical records.

## Assumptions and Limitations

- The input is treated according to the documented snapshot semantics.
- `order_id` is the record key.
- Incremental merge does not infer deletions without explicit deletion events or reconciliation.
- Partition replacement requires complete snapshots for the partitions being replaced.
- Runtime measurements are environment-dependent and should be repeated at multiple input sizes.
- Production deployment would require additional monitoring, durable orchestration, access controls, and recovery testing.

## Testing

The current test suite covers successful processing, empty input, validation failures, missing schema columns, and incremental-merge idempotency.

Additional tests should verify transaction rollback, retry behavior, late-arriving records, partition changes, and reconciliation at larger data volumes.

## Design Documentation

See:

- `docs/data_dictionary.md` for field definitions and validation expectations.
- `docs/design_tradeoffs.md` for strategy comparison, complexity, and recovery considerations.
- `docs/test_evidence.txt` for recorded test evidence.

## Reproducibility

Use the same seed and row count to reproduce the same generated input under the same generator version. Record the command, environment, and actual timing results when comparing strategies.

## Author Notes

This project is an entry-level data engineering exercise demonstrating data validation, loading strategies, testing, reconciliation, and performance measurement.
