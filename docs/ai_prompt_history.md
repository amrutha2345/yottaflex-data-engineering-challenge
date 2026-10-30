# AI Prompt History – Key Project Decisions

## 1. Choosing the Project Architecture

**Prompt:**

Design a modular Python data engineering pipeline to compare full refresh, incremental merge, and partition replacement. Should the implementation use separate modules for data generation, validation, loading strategies, observability, and execution? Explain the architectural trade-offs.

**Key decision:**
Use a modular Python architecture with separate responsibilities for data generation, validation, loading strategies, CLI execution, and observability.

## 2. Choosing Synthetic Data

**Prompt:**

Should the pipeline use an external dataset or generate synthetic order data? Design a reproducible dataset using a fixed random seed that supports consistent testing and benchmarking.

**Key decision:**
Use locally generated synthetic order records with a fixed seed of 42 to make benchmark runs reproducible without depending on external datasets.

## 3. Defining Data Quality Rules

**Prompt:**

Which validation rules should be applied to order records before loading them into the target database? Consider missing fields, invalid customer references, negative amounts, invalid dates, timestamps, statuses, and duplicate order IDs.

**Key decision:**
Validate records before loading and separate valid records from rejected records. Preserve rejected records for inspection rather than silently discarding them.

## 4. Deciding How to Handle Duplicates

**Prompt:**

How should the pipeline handle identical and conflicting records with the same order ID? Should it keep the earliest record, select the latest updated timestamp, or quarantine ambiguous conflicts?

**Key decision:**
Use order ID to identify duplicates, resolve eligible conflicts using update timestamps, and quarantine conflicting records when the latest timestamps are tied and the correct version cannot be determined.

## 5. Choosing the Full Refresh Implementation

**Prompt:**

How should full refresh replace the target dataset safely? Should the existing data be deleted before loading, and how can the pipeline prevent an empty input from accidentally removing all target records?

**Key decision:**
Use a transaction for full refresh and reject empty input before changing existing target data.

## 6. Choosing Incremental Merge Logic

**Prompt:**

How should SQLite UPSERT handle existing order IDs when incoming records may be newer, older, or identical? Design a condition that prevents stale records from overwriting newer records.

**Key decision:**
Use order ID as the primary key and update existing records only when the incoming `updated_at` timestamp is newer.

## 7. Defining Partition Replacement Behavior

**Prompt:**

How should partition replacement work for monthly order data? Should the pipeline delete and reload only the months present in the incoming batch? What assumptions and risks should be documented?

**Key decision:**
Use order-month partitions and replace only the partitions represented in the incoming dataset. Treat each incoming partition as a complete snapshot, not a partial update.

## 8. Choosing the Equivalence and Recovery Checks

**Prompt:**

How can the pipeline prove that all three strategies produce equivalent results? Also, how should it handle transaction failures, repeated execution, empty batches, and late-arriving records?

**Key decision:**
Compare canonical outputs against the full-refresh baseline, use transactional loading, and test failure and rerun scenarios. Report failed strategies and output mismatches explicitly.

## 9. Choosing Benchmark Metrics and Timing Scope

**Prompt:**

Which metrics should be collected to compare the three strategies fairly? Explain how to distinguish individual strategy runtimes from total pipeline elapsed time and how to interpret results from a 100,000-row synthetic dataset.

**Key decision:**
Record input, valid, rejected, and output counts, aggregate amount, strategy runtime, and equivalence status. Report total pipeline time separately because it includes work beyond the individual strategy executions.

## 10. Reviewing Implementation Risks and Submission Decisions

**Prompt:**

Review the Python pipeline implementation for potential problems involving duplicate resolution, timestamp handling, transaction boundaries, partition replacement assumptions, logging, data types, and benchmark reliability. Which findings need correction, testing, or documentation?

**Key decision:**
Use code review to identify risks and verify them against the implementation. Document unresolved limitations rather than assuming every suggested change is necessary or completed.

---

## AI Tools Used

- ChatGPT – architecture discussions, implementation guidance, debugging, testing and documentation.
- Claude – source-code review and identification of potential implementation risks.

## AI Usage Disclosure

AI tools supported technical reasoning and development decisions. The prompts above are reconstructed summaries of development conversations, not verbatim transcripts.

The final implementation, benchmark results, and test outcomes must be independently verified. The candidate is responsible for understanding and explaining the design decisions and limitations.