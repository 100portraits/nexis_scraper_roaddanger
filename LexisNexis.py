# LexisNexis Selenium utilities

import argparse
import csv
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from time import monotonic, sleep
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


LEXIS_URL = "https://lib.uva.nl/discovery/fulldisplay/alma990037746580205131/31UKB_UAM1_INST:UVA"
SEARCH_QUERY = (
    "(verkeersongeval or aanrijding or ongeluk or crash or botsing or verkeersongeluk)"
)
PROGRESS_CSV = Path("progress.csv")
DOWNLOAD_ROOT = Path(__file__).parent / "downloads"


@dataclass
class LexisContext:
    driver: WebDriver
    base_url: str = LEXIS_URL


def build_filtered_search_url(base_search_url: str, query: str) -> str:
    """
    Take a known working Lexis search URL (with filters already applied)
    and replace only the search terms, keeping filters (language, date, etc.) intact.
    """
    parsed = urlparse(base_search_url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    params["pdsearchterms"] = query
    new_query = urlencode(params, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def navigate_to_filtered_search(ctx: LexisContext, base_search_url: str, query: str) -> None:
    """
    Build a filtered search URL from a template and navigate to it.

    base_search_url should be a URL copied from Lexis with the desired filters
    already applied (e.g. Dutch + from 1 Jan 2025), so we can just swap the
    search terms.
    """
    url = build_filtered_search_url(base_search_url, query)
    ctx.driver.get(url)


def create_lexis_context() -> LexisContext:
    """Create a Selenium Chrome session for LexisNexis work."""
    DOWNLOAD_ROOT.mkdir(exist_ok=True)

    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    # Keep the Chrome window open after the cell finishes
    chrome_options.add_experimental_option("detach", True)

    # Set default download directory for Chrome to our downloads folder
    chrome_prefs = {
        "download.default_directory": str(DOWNLOAD_ROOT.resolve()),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    chrome_options.add_experimental_option("prefs", chrome_prefs)

    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return LexisContext(driver=driver)


def open_lexis_page(ctx: LexisContext) -> None:
    """Open the main LexisNexis page, run the base search, and land on results."""
    driver = ctx.driver
    driver.get(ctx.base_url)

    wait = WebDriverWait(driver, 20)
    # The text is inside a span within the button, so target the button that contains that span.
    available_online = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//button[.//span[normalize-space()='Available Online' or normalize-space()='Available online']]",
            )
        )
    )

    original_windows = driver.window_handles
    available_online.click()

    # Wait for a new tab/window to open and switch to it
    wait.until(lambda d: len(d.window_handles) > len(original_windows))
    new_windows = [h for h in driver.window_handles if h not in original_windows]
    if new_windows:
        driver.switch_to.window(new_windows[0])

    # In the new tab, wait for the LexisNexis main search box to be visible
    search_box = wait.until(
        EC.visibility_of_element_located(
            (By.CSS_SELECTOR, "lng-searchbox lng-expanding-textarea[aria-label='Search for']")
        )
    )

    # Enter the search query
    search_box.click()
    search_box.send_keys(SEARCH_QUERY)

    # Click the Search button
    search_button = wait.until(
        EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "lng-searchbox lng-search-button button[aria-label='Search']")
        )
    )
    search_button.click()


def scrape_lexis_page(ctx: LexisContext):
    """Placeholder for scraping logic from the current LexisNexis page."""
    # TODO: add real scraping code here
    return None


def download_lexis_document(ctx: LexisContext):
    """Placeholder for document download logic on LexisNexis."""
    # TODO: add real download interactions here
    return None


def clear_timeline_filter_if_any(ctx: LexisContext) -> None:
    """Remove an active timeline filter (if present) before applying a new one."""
    driver = ctx.driver
    wait = WebDriverWait(driver, 10)

    try:
        active_timeline = wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//ul[contains(@class,'filters-used')]//button[contains(@title, 'Tijdlijn:')]",
                )
            )
        )
        # Make sure it is in view and not covered, then click via JS to avoid interception.
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", active_timeline
        )
        driver.execute_script("arguments[0].click();", active_timeline)
        sleep(3)
    except TimeoutException:
        # No active timeline filter; nothing to clear.
        return


def filter_language_dutch(ctx: LexisContext) -> None:
    """Apply 'Dutch' language filter on the current results page."""
    driver = ctx.driver
    wait = WebDriverWait(driver, 20)

    # Expand the language accordion if it's collapsed
    lang_trigger = wait.until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "button[data-filtertype='language']")
        )
    )
    if "expanded" not in lang_trigger.get_attribute("class"):
        lang_trigger.click()

    # Click the label for the Dutch checkbox (more reliable than input)
    dutch_label = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//ul[@data-id='language']//label[.//span[normalize-space()='Dutch']]",
            )
        )
    )
    dutch_label.click()

    # Give the page a moment to apply the language filter
    sleep(3)


def filter_single_day(ctx: LexisContext, day: date) -> None:
    """Apply a date filter for a single day on the current results page."""
    driver = ctx.driver
    wait = WebDriverWait(driver, 20)

    # Clear any existing timeline filter chip first
    clear_timeline_filter_if_any(ctx)

    # Expand the timeline accordion if it's collapsed
    tl_trigger = wait.until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "button[data-filtertype='datestr-news']")
        )
    )
    if "collapsed" in tl_trigger.get_attribute("class"):
        tl_trigger.click()

    # Set both min and max date inputs to the same day (single-day range)
    # Lexis UI expects DD/MM/YYYY format, e.g. "01/01/2025"
    day_str = day.strftime("%d/%m/%Y")
    min_input = wait.until(
        EC.visibility_of_element_located(
            (By.CSS_SELECTOR, "div.supplemental.timeline input.min-val")
        )
    )
    max_input = wait.until(
        EC.visibility_of_element_located(
            (By.CSS_SELECTOR, "div.supplemental.timeline input.max-val")
        )
    )

    for el in (min_input, max_input):
        # Robust clear: select-all + delete, since plain .clear() may not work with masked inputs
        el.click()
        el.send_keys(Keys.CONTROL, "a")
        el.send_keys(Keys.DELETE)
        el.send_keys(day_str)

    # Click the OK button to apply the date range
    ok_button = wait.until(
        EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "div.supplemental.timeline button.save")
        )
    )
    ok_button.click()

    # Give the results a moment to refresh
    sleep(3)


DOWNLOAD_LIMIT = 250


def update_progress_for_day(
    day: date,
    completed: bool,
    num_docs: int,
    num_downloaded: int,
    time_taken: float,
) -> None:
    """Update or append a row for the given day in progress.csv, if it exists."""
    if not PROGRESS_CSV.exists():
        return

    rows: list[dict[str, str]] = []
    fieldnames = ["date", "completed", "num_docs", "num_downloaded", "time_taken"]

    with PROGRESS_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames:
            fieldnames = list(reader.fieldnames)
        for row in reader:
            rows.append(row)

    day_key = day.strftime("%d-%m-%Y")
    updated = False
    for row in rows:
        if row.get("date") == day_key:
            row["completed"] = str(bool(completed))
            row["num_docs"] = str(num_docs)
            row["num_downloaded"] = str(num_downloaded)
            row["time_taken"] = f"{time_taken:.2f}"
            updated = True
            break

    if not updated:
        rows.append(
            {
                "date": day_key,
                "completed": str(bool(completed)),
                "num_docs": str(num_docs),
                "num_downloaded": str(num_downloaded),
                "time_taken": f"{time_taken:.2f}",
            }
        )

    with PROGRESS_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def download_all_documents_for_current_results(ctx: LexisContext) -> tuple[int, int]:
    """
    For the current results page, batch-download the first content type's documents
    in chunks of at most DOWNLOAD_LIMIT.
    Prints a single boolean indicating whether the total count exceeds the limit.
    """
    driver = ctx.driver
    wait = WebDriverWait(driver, 20)

    first_tab = wait.until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "ul.content-switcher li[data-actualresultscount]")
        )
    )
    count_raw = first_tab.get_attribute("data-actualresultscount") or "0"
    try:
        count_int = int(count_raw.replace(".", "").replace("+", "").strip())
    except ValueError:
        count_int = 0

    if count_int == 0:
        return 0, 0

    total_downloaded = 0
    start_idx = 1
    while start_idx <= count_int:
        end_idx = min(start_idx + DOWNLOAD_LIMIT - 1, count_int)

        # Open the download modal for this batch
        download_btn = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button[data-action='downloadopt'][aria-label='Downloaden']")
            )
        )
        download_btn.click()

        set_download_modal_settings(ctx, start_idx, end_idx)

        total_downloaded += end_idx - start_idx + 1
        start_idx = end_idx + 1

    return count_int, total_downloaded


def set_download_modal_settings(ctx: LexisContext, start_idx: int, end_idx: int) -> None:
    """
    Configure the download dialog for the range start_idx-end_idx full documents in DOCX format,
    saved as separate files, and adjust formatting options.
    """
    driver = ctx.driver
    wait = WebDriverWait(driver, 20)

    # Verify the download dialog is open
    wait.until(
        EC.visibility_of_element_located(
            (By.CSS_SELECTOR, "aside.gvs-dialog.delivery[role='dialog'] form#dialog-content")
        )
    )

    # 1. Volledige documenten
    docs_radio = wait.until(
        EC.element_to_be_clickable((By.ID, "DocumentsOnly"))
    )
    if not docs_radio.is_selected():
        docs_radio.click()

    # 2. Range input: start_idx-end_idx (single batch range)
    range_input = wait.until(
        EC.visibility_of_element_located(
            (
                By.CSS_SELECTOR,
                "fieldset.DeliveryItemType .nested.range input#SelectedRange:not(.ignore)",
            )
        )
    )
    range_str = f"{start_idx}-{end_idx}"
    range_input.click()
    range_input.send_keys(Keys.CONTROL, "a")
    range_input.send_keys(Keys.DELETE)
    range_input.send_keys(range_str)

    # 3. Bestandstype: MS Word (docx)
    docx_radio = wait.until(EC.element_to_be_clickable((By.ID, "Docx")))
    if not docx_radio.is_selected():
        docx_radio.click()

    # 4. Bij meerdere documenten: opslaan als afzonderlijke bestanden
    separate_radio = wait.until(
        EC.element_to_be_clickable((By.ID, "SeparateFiles"))
    )
    if not separate_radio.is_selected():
        separate_radio.click()

    # --- Switch to 'Opmaakopties' tab ---
    formatting_tab = wait.until(
        EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "a.gvs-tab-button-link.FormattingOptions")
        )
    )
    formatting_tab.click()

    # Wait for the formatting tab panel to be shown
    wait.until(
        EC.visibility_of_element_located(
            (By.CSS_SELECTOR, "div.gvs-tab-panel.FormattingOptions section.supplemental")
        )
    )

    # --- Uncheck IncludeOptions checkboxes ---
    def _uncheck_if_checked(element_id: str) -> None:
        try:
            checkbox = driver.find_element(By.ID, element_id)
            if checkbox.is_selected():
                checkbox.click()
        except Exception:
            # If any specific checkbox is missing, just skip it.
            return

    for cid in [
        "IncludeCoverPage",
        "DisplayFirstLastNameEnabled",
        "IncludeCoverPageDetails",
        "PageNumberSelected",
        "EmbeddedReferences",
        "EmbeddedLegalCitationInItalicTypeEnabled",
    ]:
        _uncheck_if_checked(cid)

    # --- Uncheck all checked styling options under 'Opmaak' ---
    try:
        styling_fieldset = driver.find_element(By.CSS_SELECTOR, "fieldset.styling")
        styling_checkboxes = styling_fieldset.find_elements(
            By.CSS_SELECTOR, "input[type='checkbox']"
        )
        for cb in styling_checkboxes:
            if cb.is_selected():
                cb.click()
    except Exception:
        # If styling fieldset not present, ignore
        pass

    # Wait briefly, then click the Download button in the dialog footer
    sleep(2)
    download_submit = wait.until(
        EC.element_to_be_clickable(
            (
                By.CSS_SELECTOR,
                "footer.dialog-footer button.button.primary[data-action='download']",
            )
        )
    )
    download_submit.click()

    # --- Wait for download processing to complete before continuing the loop ---
    # 1) Wait for the delivery popin (spinner) to appear, indicating a download is in progress.
    try:
        WebDriverWait(driver, 30).until(
            EC.visibility_of_element_located((By.ID, "delivery-popin"))
        )
    except TimeoutException:
        # If it never appears, continue; some small downloads may finish too quickly.
        pass

    # 2) Wait for a "Downloaden is gereed" status message in the delivery jobs list.
    try:
        jobs_wait = WebDriverWait(driver, 120)
        jobs_wait.until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    "ul#delivery-jobs span.status-message.success",
                )
            )
        )

        # 3) Then wait until there are no active jobs left (the list empties / notification clears).
        jobs_wait.until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "ul#delivery-jobs li")) == 0
        )
    except TimeoutException:
        # If it times out, just move on; this prevents the loop from hanging forever.
        pass


def iterate_results_for_range(ctx: LexisContext, start: date, end: date) -> None:
    """Loop from start to end (inclusive), filtering one day at a time."""
    current = start

    while current <= end:
        # Track downloads created during this day so we can move them to a per-day folder
        before_files = {
            p for p in DOWNLOAD_ROOT.glob("*") if p.is_file()
        }

        day_start = monotonic()
        filter_single_day(ctx, current)
        num_docs, num_downloaded = download_all_documents_for_current_results(ctx)
        elapsed = monotonic() - day_start

        after_files = {
            p for p in DOWNLOAD_ROOT.glob("*") if p.is_file()
        }
        new_files = after_files - before_files
        if new_files:
            day_folder = DOWNLOAD_ROOT / current.strftime("%d-%m-%Y")
            day_folder.mkdir(exist_ok=True)
            for f in new_files:
                target = day_folder / f.name
                try:
                    f.rename(target)
                except OSError:
                    # If move fails for any reason, skip that file.
                    pass

        update_progress_for_day(
            current,
            completed=True,
            num_docs=num_docs,
            num_downloaded=num_downloaded,
            time_taken=elapsed,
        )
        current += date.resolution  # 1 day


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape LexisNexis results over a date range."
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default="01-01-2025",
        help="Start date (inclusive) in DD-MM-YYYY format. Default: 01-01-2025",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default="31-12-2025",
        help="End date (inclusive) in DD-MM-YYYY format. Default: 31-12-2025",
    )
    return parser.parse_args()


def main() -> None:
    """
    Pipeline:
    1. Open LexisNexis via UvA and run the base search.
    2. Filter to Dutch language only.
    3. For each day in the chosen range, filter to that single day and download all docs.
    """
    args = parse_args()
    try:
        start_date = datetime.strptime(args.start_date, "%d-%m-%Y").date()
        end_date = datetime.strptime(args.end_date, "%d-%m-%Y").date()
    except ValueError:
        raise SystemExit("start-date and end-date must be in DD-MM-YYYY format")

    if end_date < start_date:
        raise SystemExit("end-date must be on or after start-date")

    ctx = create_lexis_context()
    open_lexis_page(ctx)
    filter_language_dutch(ctx)
    iterate_results_for_range(ctx, start_date, end_date)


if __name__ == "__main__":
    main()