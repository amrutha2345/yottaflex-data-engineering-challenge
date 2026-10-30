
import csv
import sqlite3
import tempfile
import unittest
from pathlib import Path

from pipeline.generator import generate_csv, write_edge_case_csv
from pipeline.validation import validate_csv
from pipeline.strategies import run_strategy, read_canonical


CSV_FIELDS = [
    "order_id",
    "customer_id",
    "order_date",
    "amount",
    "status",
    "updated_at",
]


def make_row(
    order_id="O001",
    customer_id="C00001",
    order_date="2026-01-15",
    amount="100.00",
    status="paid",
    updated_at="2026-01-15T10:00:00+00:00",
):
    """Create a CSV-compatible order row."""
    return {
        "order_id": order_id,
        "customer_id": customer_id,
        "order_date": order_date,
        "amount": amount,
        "status": status,
        "updated_at": updated_at,
    }


def strategy_row(**kwargs):
    """Create strategy input including the derived partition field."""
    row = make_row(**kwargs)
    row["order_month"] = row["order_date"][:7]
    return row


def write_rows(path, rows):
    """Write test rows using the expected input CSV schema."""
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.csv_path = self.root / "orders.csv"
        self.customers = generate_csv(self.csv_path, 30, 7)

    def tearDown(self):
        self.tmp.cleanup()

    def test_happy_path_and_strategy_equivalence(self):
        result = validate_csv(self.csv_path, self.customers)

        self.assertEqual(len(result.valid_rows), 30)
        self.assertEqual(result.rejects, [])

        outputs = []

        for strategy in (
            "full_refresh",
            "incremental_merge",
            "partition_replacement",
        ):
            db = self.root / f"{strategy}.db"
            run_strategy(
                strategy, db, result.valid_rows, self.csv_path.name
            )
            outputs.append(read_canonical(db))

        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(outputs[0], outputs[2])

    def test_generator_is_reproducible(self):
        first = self.root / "first.csv"
        second = self.root / "second.csv"

        generate_csv(first, 20, 42)
        generate_csv(second, 20, 42)

        self.assertEqual(
            first.read_text(encoding="utf-8"),
            second.read_text(encoding="utf-8"),
        )

    def test_duplicate_null_invalid_reference_and_domain_rules(self):
        path = self.root / "edges.csv"
        write_edge_case_csv(path)

        result = validate_csv(path, {"C00001"})
        reasons = {item["reason"] for item in result.rejects}

        self.assertTrue(
            any("duplicate" in reason for reason in reasons),
            f"Expected a duplicate-related rejection; got {reasons}",
        )
        self.assertIn("missing_required_field", reasons)
        self.assertIn("invalid_customer_reference", reasons)
        self.assertIn("negative_amount", reasons)
        self.assertIn("invalid_date_amount_or_timestamp", reasons)

    def test_invalid_status_is_quarantined(self):
        path = self.root / "invalid_status.csv"
        write_rows(path, [make_row(status="unknown_status")])

        result = validate_csv(path, {"C00001"})

        self.assertEqual(len(result.valid_rows), 0)
        self.assertEqual(len(result.rejects), 1)
        self.assertIn("invalid_status", result.rejects[0]["reason"])

    def test_nan_and_infinite_amounts_are_rejected(self):
        path = self.root / "nonfinite.csv"
        write_rows(
            path,
            [
                make_row(order_id="O001", amount="NaN"),
                make_row(order_id="O002", amount="inf"),
            ],
        )

        result = validate_csv(path, {"C00001"})

        self.assertEqual(len(result.valid_rows), 0)
        self.assertEqual(len(result.rejects), 2)

    def test_exact_duplicate_keeps_one_record(self):
        path = self.root / "duplicates.csv"
        row = make_row()

        write_rows(path, [row, row.copy()])
        result = validate_csv(path, {"C00001"})

        self.assertEqual(len(result.valid_rows), 1)
        self.assertEqual(len(result.rejects), 1)
        self.assertIn("duplicate", result.rejects[0]["reason"])

    def test_conflicting_duplicate_keeps_latest_timestamp(self):
        path = self.root / "conflicting_duplicates.csv"

        older = make_row(
            amount="100.00",
            updated_at="2026-01-15T10:00:00+00:00",
        )
        newer = make_row(
            amount="250.00",
            updated_at="2026-01-15T11:00:00+00:00",
        )

        write_rows(path, [older, newer])
        result = validate_csv(path, {"C00001"})

        self.assertEqual(len(result.valid_rows), 1)
        self.assertEqual(float(result.valid_rows[0]["amount"]), 250.00)
        self.assertEqual(len(result.rejects), 1)

    def test_conflicting_duplicate_with_tied_latest_timestamp_is_quarantined(self):
        path = self.root / "tied_duplicates.csv"
        timestamp = "2026-01-15T10:00:00+00:00"

        first = make_row(amount="100.00", updated_at=timestamp)
        second = make_row(amount="200.00", updated_at=timestamp)

        write_rows(path, [first, second])
        result = validate_csv(path, {"C00001"})

        self.assertEqual(len(result.valid_rows), 0)
        self.assertEqual(len(result.rejects), 2)

    def test_empty_input(self):
        path = self.root / "empty.csv"
        write_rows(path, [])

        result = validate_csv(path, {"C00001"})

        self.assertEqual(result.valid_rows, [])
        self.assertEqual(result.rejects, [])
        self.assertEqual(result.input_count, 0)

    def test_empty_file_without_header_is_reported(self):
        path = self.root / "no_header.csv"
        path.write_text("", encoding="utf-8")

        result = validate_csv(path, {"C00001"})

        self.assertEqual(result.valid_rows, [])
        self.assertEqual(len(result.rejects), 1)

    def test_missing_schema_column_fails_fast(self):
        path = self.root / "bad_schema.csv"
        path.write_text(
            "order_id,customer_id\nO001,C00001\n",
            encoding="utf-8",
        )

        with self.assertRaises(ValueError):
            validate_csv(path, {"C00001"})

    def test_unexpected_extra_column_fails_fast(self):
        path = self.root / "extra_column.csv"
        path.write_text(
            "order_id,customer_id,order_date,amount,status,updated_at,extra\n"
            "O001,C00001,2026-01-15,100.00,paid,"
            "2026-01-15T10:00:00+00:00,unexpected\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "Schema mismatch"):
            validate_csv(path, {"C00001"})

    def test_malformed_row_with_extra_field_is_quarantined(self):
        path = self.root / "malformed.csv"
        path.write_text(
            "order_id,customer_id,order_date,amount,status,updated_at\n"
            "O001,C00001,2026-01-15,100.00,paid,"
            "2026-01-15T10:00:00+00:00,unexpected\n",
            encoding="utf-8",
        )

        result = validate_csv(path, {"C00001"})

        self.assertEqual(result.valid_rows, [])
        self.assertEqual(len(result.rejects), 1)
        self.assertEqual(
            result.rejects[0]["reason"], "malformed_csv_row"
        )

    def test_rerun_is_idempotent_for_merge(self):
        result = validate_csv(self.csv_path, self.customers)
        db = self.root / "merge.db"

        first = run_strategy(
            "incremental_merge", db, result.valid_rows, self.csv_path.name
        )
        first_rows = read_canonical(db)

        second = run_strategy(
            "incremental_merge", db, result.valid_rows, self.csv_path.name
        )
        second_rows = read_canonical(db)

        self.assertEqual(first["row_count"], second["row_count"])
        self.assertEqual(first["amount_sum"], second["amount_sum"])
        self.assertEqual(first_rows, second_rows)

    def test_incremental_merge_rolls_back_failed_batch(self):
        db = self.root / "rollback.db"

        original = strategy_row(order_id="O001", amount="100.00")
        run_strategy("full_refresh", db, [original], "initial.csv")
        original_rows = read_canonical(db)

        valid_new = strategy_row(order_id="O002", amount="200.00")
        invalid = strategy_row(order_id="O003", amount="-10.00")

        with self.assertRaises(sqlite3.IntegrityError):
            run_strategy(
                "incremental_merge",
                db,
                [valid_new, invalid],
                "failed_batch.csv",
            )

        self.assertEqual(read_canonical(db), original_rows)

        retry_row = strategy_row(order_id="O002", amount="200.00")
        run_strategy(
            "incremental_merge", db, [retry_row], "retry.csv"
        )

        final_rows = read_canonical(db)
        self.assertEqual(len(final_rows), 2)
        self.assertEqual(
            {row[0] for row in final_rows},
            {"O001", "O002"},
        )

    def test_empty_full_refresh_does_not_delete_existing_data(self):
        db = self.root / "empty_refresh.db"
        original = strategy_row(order_id="O001", amount="100.00")

        run_strategy("full_refresh", db, [original], "initial.csv")
        before = read_canonical(db)

        with self.assertRaisesRegex(ValueError, "Empty full refresh"):
            run_strategy("full_refresh", db, [], "empty.csv")

        self.assertEqual(read_canonical(db), before)

    def test_late_arriving_older_update_is_ignored(self):
        db = self.root / "late_arrival.db"

        newer = strategy_row(
            order_id="O001",
            amount="250.00",
            updated_at="2026-01-15T11:00:00+00:00",
        )
        older = strategy_row(
            order_id="O001",
            amount="100.00",
            updated_at="2026-01-15T10:00:00+00:00",
        )

        run_strategy("full_refresh", db, [newer], "newer.csv")
        run_strategy("incremental_merge", db, [older], "late.csv")

        rows = read_canonical(db)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][4], 250.0)

    def test_partition_replacement_preserves_unaffected_months(self):
        db = self.root / "partition.db"

        january_old = strategy_row(
            order_id="JAN001",
            order_date="2026-01-10",
            amount="100.00",
        )
        february_existing = strategy_row(
            order_id="FEB001",
            order_date="2026-02-10",
            amount="200.00",
        )

        run_strategy(
            "full_refresh",
            db,
            [january_old, february_existing],
            "initial.csv",
        )

        # The January input represents the complete January snapshot.
        january_new = strategy_row(
            order_id="JAN002",
            order_date="2026-01-20",
            amount="300.00",
        )

        run_strategy(
            "partition_replacement",
            db,
            [january_new],
            "january_snapshot.csv",
        )

        rows = read_canonical(db)
        order_ids = {row[0] for row in rows}

        self.assertEqual(order_ids, {"JAN002", "FEB001"})

    def test_unknown_strategy_fails_clearly(self):
        db = self.root / "unknown.db"

        with self.assertRaises(ValueError):
            run_strategy("unknown_strategy", db, [], "orders.csv")


if __name__ == "__main__":
    unittest.main()
