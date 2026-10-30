
"""Generate data, validate it, and benchmark three load strategies."""
from __future__ import annotations

import argparse
import csv
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .generator import generate_csv, write_edge_case_csv
from .observability import setup_logging, log_event
from .validation import validate_csv
from .strategies import run_strategy, read_canonical


STRATEGIES = (
    "full_refresh",
    "incremental_merge",
    "partition_replacement",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    """Write dictionaries to CSV, including headers for empty results."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate data and benchmark three load strategies."
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=1000,
        help="Number of synthetic input rows (must be >= 0).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible data generation.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/output"),
        help="Directory for input, rejects, reports, logs, and databases.",
    )

    args = parser.parse_args()

    if args.rows < 0:
        parser.error("--rows must be zero or greater.")

    if not str(args.output_dir).strip():
        parser.error("--output-dir cannot be empty.")

    args.output_dir = args.output_dir.expanduser().resolve()
    return args


def main() -> None:
    args = parse_args()
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)

    run_id = str(uuid.uuid4())
    logger = setup_logging(out)

    log_event(
        logger,
        "pipeline_started",
        run_id=run_id,
        requested_rows=args.rows,
        seed=args.seed,
        output_dir=str(out),
    )

    started_pipeline = time.perf_counter()

    try:
        # Step 1: Generate source data and deliberately invalid examples.
        source = out / "orders_source.csv"
        customers = generate_csv(source, args.rows, args.seed)

        edge = out / "edge_cases.csv"
        write_edge_case_csv(edge)

        # Step 2: Validate the normal source and edge-case input separately.
        validation = validate_csv(source, customers)
        edge_validation = validate_csv(edge, customers)

        all_rejects = validation.rejects + edge_validation.rejects

        write_csv(
            out / "rejects.csv",
            all_rejects,
            [
                "source_file",
                "source_row",
                "order_id",
                "reason",
                "raw_record",
            ],
        )

        duplicate_count = getattr(validation, "duplicate_count", 0)

        log_event(
            logger,
            "validation_completed",
            run_id=run_id,
            input_count=validation.input_count,
            valid_count=len(validation.valid_rows),
            reject_count=len(validation.rejects),
            edge_case_reject_count=len(edge_validation.rejects),
            duplicate_count=duplicate_count,
        )

        # Step 3: Benchmark each strategy against a clean target database.
        source_file = source.name
        log_rows: list[dict] = []
        strategy_outputs: dict[str, list[tuple]] = {}
        strategy_metrics: dict[str, dict] = {}

        for strategy in STRATEGIES:
            strategy_started_at = now_iso()
            t0 = time.perf_counter()
            db = out / f"{strategy}.sqlite"

            log_event(
                logger,
                "strategy_started",
                run_id=run_id,
                strategy=strategy,
            )

            try:
                # Clean targets make the three benchmark runs comparable.
                if db.exists():
                    db.unlink()

                metrics = run_strategy(
                    strategy,
                    db,
                    validation.valid_rows,
                    source_file,
                )

                canonical = read_canonical(db)
                elapsed = round(time.perf_counter() - t0, 6)

                strategy_outputs[strategy] = canonical
                strategy_metrics[strategy] = metrics

                strategy_row = {
                    "run_id": run_id,
                    "strategy": strategy,
                    "started_at": strategy_started_at,
                    "ended_at": now_iso(),
                    "status": "success",
                    "input_count": validation.input_count,
                    "valid_count": len(validation.valid_rows),
                    "output_count": metrics["row_count"],
                    "rejected_count": len(validation.rejects),
                    "duplicate_count": duplicate_count,
                    "amount_sum": metrics["amount_sum"],
                    "elapsed_seconds": elapsed,
                    "failure_reason": "",
                }
                log_rows.append(strategy_row)

                log_event(
                    logger,
                    "strategy_completed",
                    run_id=run_id,
                    strategy=strategy,
                    status="success",
                    input_count=validation.input_count,
                    valid_count=len(validation.valid_rows),
                    rejected_count=len(validation.rejects),
                    duplicate_count=duplicate_count,
                    output_count=metrics["row_count"],
                    amount_sum=metrics["amount_sum"],
                    elapsed_seconds=elapsed,
                )

            except Exception as exc:
                elapsed = round(time.perf_counter() - t0, 6)

                log_rows.append({
                    "run_id": run_id,
                    "strategy": strategy,
                    "started_at": strategy_started_at,
                    "ended_at": now_iso(),
                    "status": "failed",
                    "input_count": validation.input_count,
                    "valid_count": len(validation.valid_rows),
                    "output_count": 0,
                    "rejected_count": len(validation.rejects),
                    "duplicate_count": duplicate_count,
                    "amount_sum": "",
                    "elapsed_seconds": elapsed,
                    "failure_reason": f"{type(exc).__name__}: {exc}",
                })

                log_event(
                    logger,
                    "strategy_failed",
                    run_id=run_id,
                    strategy=strategy,
                    status="failed",
                    elapsed_seconds=elapsed,
                    error_type=type(exc).__name__,
                    failure_reason=str(exc),
                )

        # Step 4: Compare every successful output with full refresh.
        baseline = strategy_outputs.get("full_refresh")
        strategy_report: dict[str, dict] = {}

        for row in log_rows:
            name = row["strategy"]
            output = strategy_outputs.get(name)

            strategy_report[name] = {
                **row,
                "matches_full_refresh": (
                    output == baseline
                    if output is not None and baseline is not None
                    else False
                ),
            }

        equivalent_outputs = (
            len(strategy_outputs) == len(STRATEGIES)
            and baseline is not None
            and all(
                strategy_outputs[name] == baseline
                for name in STRATEGIES
            )
        )

        failed_strategies = [
            row["strategy"]
            for row in log_rows
            if row["status"] != "success"
        ]

        report = {
            "run_id": run_id,
            "generated_at": now_iso(),
            "seed": args.seed,
            "requested_rows": args.rows,
            "input_count": validation.input_count,
            "valid_count": len(validation.valid_rows),
            "reject_count": len(validation.rejects),
            "edge_case_reject_count": len(edge_validation.rejects),
            "duplicate_count": duplicate_count,
            "quarantined_row_count": len(all_rejects),
            "failed_strategies": failed_strategies,
            "strategies": strategy_report,
            "equivalent_outputs": equivalent_outputs,
            "overall_status": (
                "success" if equivalent_outputs else "failed"
            ),
            "total_elapsed_seconds": round(
                time.perf_counter() - started_pipeline, 6
            ),
        }

        # Step 5: Persist the run log and summary report.
        write_csv(
            out / "run_log.csv",
            log_rows,
            [
                "run_id",
                "strategy",
                "started_at",
                "ended_at",
                "status",
                "input_count",
                "valid_count",
                "output_count",
                "rejected_count",
                "duplicate_count",
                "amount_sum",
                "elapsed_seconds",
                "failure_reason",
            ],
        )

        (out / "benchmark_report.json").write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )

        log_event(
            logger,
            "pipeline_completed",
            run_id=run_id,
            overall_status=report["overall_status"],
            equivalent_outputs=equivalent_outputs,
            failed_strategies=failed_strategies,
            input_count=validation.input_count,
            valid_count=len(validation.valid_rows),
            reject_count=len(validation.rejects),
            duplicate_count=duplicate_count,
            total_elapsed_seconds=report["total_elapsed_seconds"],
        )

        print(json.dumps(report, indent=2))

        if not equivalent_outputs:
            raise SystemExit(
                "Validation failed: one or more strategies failed or "
                "produced different outputs. Check pipeline.log, "
                "run_log.csv, and benchmark_report.json."
            )

    except SystemExit:
        raise
    except Exception as exc:
        log_event(
            logger,
            "pipeline_failed",
            run_id=run_id,
            error_type=type(exc).__name__,
            failure_reason=str(exc),
        )
        raise


if __name__ == "__main__":
    main()
