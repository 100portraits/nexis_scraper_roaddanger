from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path


PROGRESS_CSV = Path("progress.csv")
START_DATE = date(2025, 1, 1)
END_DATE = date(2025, 12, 31)


def init_progress_csv() -> None:
    """Create or overwrite progress.csv with one row per day in 2025 (DD-MM-YYYY)."""
    fieldnames = ["date", "completed", "num_docs", "num_downloaded", "time_taken"]
    current = START_DATE

    with PROGRESS_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        while current <= END_DATE:
            writer.writerow(
                {
                    "date": current.strftime("%d-%m-%Y"),
                    "completed": "False",
                    "num_docs": "0",
                    "num_downloaded": "0",
                    "time_taken": "0.0",
                }
            )
            current += timedelta(days=1)


if __name__ == "__main__":
    init_progress_csv()

