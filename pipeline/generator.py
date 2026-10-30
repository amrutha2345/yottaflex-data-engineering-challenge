"""Fixed-seed synthetic source data generator."""
from __future__ import annotations
import csv, random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from .validation import REQUIRED_COLUMNS

STATUSES = ["pending", "paid", "shipped", "cancelled"]

def generate_csv(path: str | Path, rows: int = 1000, seed: int = 42) -> set[str]:
    if rows < 0:
        raise ValueError("rows must be >= 0")
    rng = random.Random(seed)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    customers = {f"C{n:05d}" for n in range(1, max(2, min(rows // 3 + 2, 10001)))}
    start = date(2025, 1, 1)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REQUIRED_COLUMNS)
        writer.writeheader()
        for i in range(rows):
            d = start + timedelta(days=rng.randrange(0, 365))
            updated = datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(days=(d-start).days, minutes=rng.randrange(0, 1440))
            writer.writerow({
                "order_id": f"O{i+1:07d}", "customer_id": rng.choice(sorted(customers)),
                "order_date": d.isoformat(), "amount": f"{rng.uniform(0, 5000):.2f}",
                "status": rng.choice(STATUSES), "updated_at": updated.isoformat().replace("+00:00", "Z")
            })
    return customers

def write_edge_case_csv(path: str | Path):
    """Small hand-crafted batch for validation demonstrations."""
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        ["O0000001","C00001","2025-01-01","10.00","paid","2025-01-02T10:00:00Z"],
        ["O0000001","C00001","2025-01-01","10.00","paid","2025-01-02T10:00:00Z"], # duplicate
        ["O0000002","","2025-01-02","12.00","pending","2025-01-02T10:00:00Z"], # null
        ["O0000003","C99999","2025-01-03","5.00","paid","2025-01-02T10:00:00Z"], # bad FK
        ["O0000004","C00001","2025-01-04","-1.00","paid","2025-01-02T10:00:00Z"], # negative
        ["O0000005","C00001","not-a-date","8.00","paid","2025-01-02T10:00:00Z"], # malformed
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(REQUIRED_COLUMNS); w.writerows(rows)
