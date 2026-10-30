
"""SQLite implementations of three load strategies."""
from __future__ import annotations

import sqlite3
from pathlib import Path

COLUMNS = (
    "order_id",
    "customer_id",
    "order_date",
    "order_month",
    "amount",
    "status",
    "updated_at",
    "source_file",
)

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    order_date TEXT NOT NULL,
    order_month TEXT NOT NULL,
    amount REAL NOT NULL CHECK(amount >= 0),
    status TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    source_file TEXT NOT NULL
)
"""

INSERT_SQL = """
INSERT INTO orders (
    order_id, customer_id, order_date, order_month,
    amount, status, updated_at, source_file
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""

UPSERT_SQL = INSERT_SQL + """
ON CONFLICT(order_id) DO UPDATE SET
    customer_id = excluded.customer_id,
    order_date = excluded.order_date,
    order_month = excluded.order_month,
    amount = excluded.amount,
    status = excluded.status,
    updated_at = excluded.updated_at,
    source_file = excluded.source_file
WHERE julianday(excluded.updated_at) > julianday(orders.updated_at)
"""


def connect_db(path: str | Path) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path)
    try:
        conn.execute(CREATE_SQL)
        conn.commit()
        return conn
    except Exception:
        conn.close()
        raise


def tuples(rows: list[dict], source_file: str):
    for row in rows:
        yield (
            row["order_id"],
            row["customer_id"],
            row["order_date"],
            row["order_month"],
            row["amount"],
            row["status"],
            row["updated_at"],
            source_file,
        )


def run_strategy(
    strategy: str,
    db_path: str | Path,
    rows: list[dict],
    source_file: str,
) -> dict:
    allowed_strategies = {
        "full_refresh",
        "incremental_merge",
        "partition_replacement",
    }

    if strategy not in allowed_strategies:
        raise ValueError(f"Unknown strategy: {strategy}")

    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Materialize before opening the connection.
    data = list(tuples(rows, source_file))

    # An empty full refresh is rejected to protect existing target data.
    if strategy == "full_refresh" and not data:
        raise ValueError(
            "Empty full refresh rejected; target data was not changed."
        )

    conn = connect_db(path)

    try:
        with conn:
            if strategy == "full_refresh":
                conn.execute("DELETE FROM orders")
                conn.executemany(INSERT_SQL, data)

            elif strategy == "incremental_merge":
                conn.executemany(UPSERT_SQL, data)

            elif strategy == "partition_replacement":
                months = sorted({row["order_month"] for row in rows})

                # Empty partition input is a no-op.
                for month in months:
                    conn.execute(
                        "DELETE FROM orders WHERE order_month = ?",
                        (month,),
                    )

                conn.executemany(INSERT_SQL, data)

        row_count = conn.execute(
            "SELECT COUNT(*) FROM orders"
        ).fetchone()[0]

        distinct_order_count = conn.execute(
            "SELECT COUNT(DISTINCT order_id) FROM orders"
        ).fetchone()[0]

        null_key_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM orders
            WHERE order_id IS NULL OR order_id = ''
            """
        ).fetchone()[0]

        amount_sum = round(
            conn.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM orders"
            ).fetchone()[0],
            2,
        )

        if row_count != distinct_order_count or null_key_count:
            raise ValueError("Target primary-key integrity check failed")

        return {
            "row_count": row_count,
            "distinct_order_count": distinct_order_count,
            "null_key_count": null_key_count,
            "amount_sum": amount_sum,
        }

    finally:
        conn.close()


def read_canonical(db_path: str | Path) -> list[tuple]:
    conn = sqlite3.connect(db_path)

    try:
        return conn.execute(
            """
            SELECT
                order_id, customer_id, order_date, order_month,
                amount, status, updated_at
            FROM orders
            ORDER BY order_id
            """
        ).fetchall()
    finally:
        conn.close()
