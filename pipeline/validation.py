
"""Input parsing, business-rule validation, duplicate handling and quarantine."""
from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

REQUIRED_COLUMNS = [
    "order_id",
    "customer_id",
    "order_date",
    "amount",
    "status",
    "updated_at",
]

ALLOWED_STATUSES = {"pending", "paid", "shipped", "cancelled"}


@dataclass
class ValidationResult:
    valid_rows: list[dict]
    rejects: list[dict]
    input_count: int
    duplicate_count: int = 0


def validate_csv(
    path: str | Path,
    known_customers: set[str],
) -> ValidationResult:
    path = Path(path)
    candidates: list[dict] = []
    rejects: list[dict] = []
    input_count = 0
    duplicate_count = 0

    def quarantine(line_no: int, raw: dict, reason: str) -> None:
        rejects.append({
            "source_file": path.name,
            "source_row": line_no,
            "order_id": (raw.get("order_id") or "").strip()
            if isinstance(raw.get("order_id"), str)
            else "",
            "reason": reason,
            "raw_record": json.dumps({str(key): value for key, value in raw.items()}, sort_keys=True,default=str,),
        })

    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)

        if reader.fieldnames is None:
            return ValidationResult(
                valid_rows=[],
                rejects=[{
                    "source_file": path.name,
                    "source_row": 0,
                    "order_id": "",
                    "reason": "empty_file_or_missing_header",
                    "raw_record": "",
                }],
                input_count=0,
            )

        missing = sorted(set(REQUIRED_COLUMNS) - set(reader.fieldnames))
        unexpected = sorted(set(reader.fieldnames) - set(REQUIRED_COLUMNS))

        if missing or unexpected:
            raise ValueError(
                f"Schema mismatch; missing={missing}, unexpected={unexpected}"
            )

        for line_no, raw in enumerate(reader, start=2):
            input_count += 1

            # DictReader uses None for extra fields and missing trailing values.
            if None in raw or any(value is None for value in raw.values()):
                quarantine(line_no, raw, "malformed_csv_row")
                continue

            row = {
                key: value.strip() if isinstance(value, str) else ""
                for key, value in raw.items()
            }

            required = (
                "order_id",
                "customer_id",
                "order_date",
                "amount",
                "status",
                "updated_at",
            )

            if any(not row.get(key) for key in required):
                quarantine(line_no, raw, "missing_required_field")
                continue

            if row["customer_id"] not in known_customers:
                quarantine(line_no, raw, "invalid_customer_reference")
                continue

            try:
                parsed_date = date.fromisoformat(row["order_date"])
                amount = float(row["amount"])
                timestamp = datetime.fromisoformat(
                    row["updated_at"].replace("Z", "+00:00")
                )

                if not math.isfinite(amount):
                    raise ValueError("amount must be finite")

                if timestamp.tzinfo is None or timestamp.utcoffset() is None:
                    raise ValueError("timestamp must include timezone")

            except (ValueError, TypeError, OverflowError):
                quarantine(
                    line_no, raw, "invalid_date_amount_or_timestamp"
                )
                continue

            if amount < 0:
                quarantine(line_no, raw, "negative_amount")
                continue

            if row["status"] not in ALLOWED_STATUSES:
                quarantine(line_no, raw, "invalid_status")
                continue

            row["amount"] = round(amount, 2)
            row["order_month"] = parsed_date.strftime("%Y-%m")
            row["_source_row"] = line_no
            row["_raw"] = raw
            row["_timestamp"] = timestamp
            candidates.append(row)

    # Group valid candidates by business key.
    groups: dict[str, list[dict]] = {}
    for row in candidates:
        groups.setdefault(row["order_id"], []).append(row)

    valid_rows: list[dict] = []

    for order_id in sorted(groups):
        group = groups[order_id]

        if len(group) == 1:
            winner = group[0]
        else:
            duplicate_count += len(group) - 1

            def business_values(row: dict) -> tuple:
                return (
                    row["customer_id"],
                    row["order_date"],
                    row["amount"],
                    row["status"],
                    row["order_month"],
                )

            values = {business_values(row) for row in group}

            if len(values) == 1:
                winner = min(group, key=lambda row: row["_source_row"])

                for duplicate in group:
                    if duplicate is not winner:
                        quarantine(
                            duplicate["_source_row"],
                            duplicate["_raw"],
                            "duplicate_order_id",
                        )
            else:
                latest_time = max(row["_timestamp"] for row in group)
                latest = [
                    row for row in group
                    if row["_timestamp"] == latest_time
                ]

                latest_values = {business_values(row) for row in latest}

                if len(latest_values) != 1:
                    for row in group:
                        quarantine(
                            row["_source_row"],
                            row["_raw"],
                            "ambiguous_conflicting_duplicate_order_id",
                        )
                    continue

                winner = min(latest, key=lambda row: row["_source_row"])

                for duplicate in group:
                    if duplicate is not winner:
                        quarantine(
                            duplicate["_source_row"],
                            duplicate["_raw"],
                            "superseded_duplicate_order_id",
                        )

        valid_rows.append({
            key: value
            for key, value in winner.items()
            if not key.startswith("_")
        })

    valid_rows.sort(key=lambda row: row["order_id"])
    rejects.sort(key=lambda row: (row["source_row"], row["reason"]))

    return ValidationResult(
        valid_rows=valid_rows,
        rejects=rejects,
        input_count=input_count,
        duplicate_count=duplicate_count,
    )
