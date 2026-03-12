### LexisNexis Daily Downloader

Automated daily scraper for LexisNexis (via the UvA library portal) using Selenium.  
It runs a fixed Dutch traffic-accident query, filters per day, downloads all “News” articles, and tracks progress in `progress.csv`.

---

### Requirements

- **Python**: 3.9+
- **Browser**: Google Chrome
- **Driver**: ChromeDriver on `PATH` (matching your Chrome version)
- **Python packages**:

```bash
pip install selenium
```

Run all commands from the `data collection` directory.

---

### Files

- `LexisNexis.py` – main Selenium scraper and downloader (what you run).
- `progress.csv` – per-day progress tracking.
- `downloads/` – where all downloaded files are stored (auto-created, grouped per day).

---

### How to run it

- **Always run from** the `data collection` folder.
- Dates are **`DD-MM-YYYY`**, and a **start + end date are required**.

Run:

```bash
python LexisNexis.py
```

You’ll then be prompted in the terminal:

```text
Enter start date (DD-MM-YYYY): 01-07-2024
Enter end date (DD-MM-YYYY): 15-07-2024
```

For each day in the range the script:

- Opens LexisNexis via the UvA portal and runs the fixed Dutch traffic-accident query.
- Filters to Dutch language and that single day.
- Downloads all “News” results in batches of up to **250** documents.
- Respects a **daily cap of 2500 downloaded documents**:
  - If today’s total (from `progress.csv`) plus the current day’s results would exceed 2500, it stops and tells you to wait until tomorrow.
- Updates `progress.csv` for that date (marks it completed, fills counts + time, and stores today as `date_scraped`).
- If some requested days are already completed, it offers to skip them; if everything in the range is completed, it exits without opening a browser.

Committed from UvA AI Chat
