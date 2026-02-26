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

- `LexisNexis.py` – main Selenium scraper and downloader.
- `progress.csv` – per-day progress tracking.
- `downloads/` – root folder where all downloaded files are stored (auto-created).

---

### 1. Run the scraper

#### Full 2025 range (default)

```bash
python LexisNexis.py
```

Equivalent to:

```bash
python LexisNexis.py --start-date 01-01-2025 --end-date 31-12-2025
```

#### Custom date range

Dates are **`DD-MM-YYYY`**:

```bash
python LexisNexis.py --start-date 01-03-2025 --end-date 15-03-2025
```

The script will, for each day in the range:

- Open LexisNexis via the UvA portal.
- Run the fixed search query:

  ```text
  (verkeersongeval or aanrijding or ongeluk or crash or botsing or verkeersongeluk)
  ```

- Filter:
  - Language: Dutch.
  - Timeline: that single day only.
- Download **all “News” results** in batches of at most **250** documents:
  - 1–250, 251–500, 501–N, … (as needed).
- Wait for each batch’s “Downloaden is gereed” notification before continuing.
- Update the row in `progress.csv` for that date.

---

### 2. Download folders

- All files are initially downloaded into `./downloads/`.
- After each day finishes, any new files from that day are moved into a dated subfolder:

```text
downloads/
  01-03-2025/
    <downloaded files...>
  02-03-2025/
    <downloaded files...>
  ...
```

This keeps downloads grouped by date, regardless of LexisNexis’ internal filenames.

---

### 3. Parallel scraping (sharing the work)

To bypass rate limits, multiple people can scrape **different date ranges** in parallel.  
Example:

- Person A:

  ```bash
  python LexisNexis.py --start-date 01-01-2025 --end-date 31-03-2025
  ```

- Person B:

  ```bash
  python LexisNexis.py --start-date 01-04-2025 --end-date 30-06-2025
  ```

Each run only touches its own date range; `progress.csv` and `downloads/` will reflect the combined coverage when results are merged.

