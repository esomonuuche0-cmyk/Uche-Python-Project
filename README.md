# Delta Harvest Distributors: Automated Sales & Inventory Data Pipeline

An incremental Python pipeline that ingests daily warehouse CSV exports, cleans and standardizes them, and builds a master dataset ready for a Power BI dashboard that refreshes each morning.

---

## 1. Background

**Delta Harvest Distributors Ltd** is an FMCG distributor based in Asaba, Delta State. It supplies packaged foods, beverages, and household items from **3 regional warehouses** to roughly **150 retail outlets** (supermarkets, mini-marts, and open-market retailers) across Delta, Edo, and Anambra states.

### The problem

Operations data lives in disconnected Excel/CSV files:

- Each warehouse exports a daily sales/inventory CSV from its POS system.
- Supplier deliveries are logged separately in an Excel workbook by the procurement officer.
- Every Monday an analyst manually copies everything into one master workbook, fixes inconsistent product names and formats, and rebuilds the Power BI report. This takes **1 to 2 full days**.
- Management receives the report on Wednesday, so the data is already **3 to 4 days stale**.
- Manual copy-paste has caused duplicated entries, mismatched SKU codes across warehouses, and inconsistent regional labels (for example `Asaba`, `asaba `, and `ASB`).

### The goal

| Management ask | How this project addresses it |
|---|---|
| Cut the reporting cycle from days to minutes | Pipeline runs in seconds and can be scheduled daily |
| Eliminate manual errors | Cleaning rules are coded once and applied identically to every file |
| Dashboard that refreshes each morning | Pipeline writes a single, consistent `master_data.csv` that Power BI reads on a scheduled refresh |
| Visibility into sales, stock levels, and stockout risk by warehouse and product | Standardized warehouse, SKU, product, and category fields make these breakdowns reliable |

---

## 2. How it works

```
data/raw/*.csv  ->  detect new files  ->  clean & standardize  ->  data/cleaned/cleaned_data_<date>.csv
                                                                        |
                                                                        v
                                                          data/combined/master_data.csv  ->  Power BI
```

1. **Detect new files.** The script lists every CSV in `data/raw/` and compares file names against `processed_files.txt`. Only unseen files are processed. If there are none, it logs the fact and stops.
2. **Clean each file** (see below).
3. **Combine** all files cleaned in the run into one table.
4. **Save** the result as a dated file in `data/cleaned/`.
5. **Record** the processed file names so they are skipped on the next run.
6. **Log** every step to the console and to a daily log file.

### Cleaning rules

| Step | Rule | Why it matters |
|---|---|---|
| Column names | Lowercased, trimmed, spaces replaced with underscores | Warehouses' exports line up when combined |
| Missing values | Rows containing any null are dropped; the count removed is logged | Prevents incomplete records reaching the dashboard, with an audit trail |
| Text casing | `warehouse_region`, `product_name`, `category` converted to Title Case | Removes case-based label variants |
| SKU codes | Uppercased, then reformatted to `XXX-XXX` (first 3 + last 3 characters) | Fixes mismatched SKU formats across warehouses |
| Dates | Parsed with `dayfirst=True` and mixed-format support; unparseable values become `NaT` | Gives one consistent date type for time-series reporting |
| Error handling | Each file is processed in its own `try/except`; failures are logged and the run continues | One bad file doesn't stop the pipeline |

---

## 3. Project structure

```
project/
├── pipeline.py                  # the pipeline script
├── processed_files.txt          # names of files already processed (auto-created)
└── data/
    ├── raw/                     # drop warehouse CSV exports here
    ├── cleaned/                 # cleaned_data_YYYY-MM-DD.csv (one per run)
    ├── combined/                # master_data.csv (cumulative dataset for Power BI)
    └── logs/                    # pipeline_YYYY-MM-DD.log
```

All folders are created automatically on first run.

---

## 4. Getting started

**Requirements:** Python 3.9+ and `pandas`.

```bash
pip install pandas
```

**Run it:**

1. Place the warehouse CSV exports in `data/raw/`.
2. Run:
   ```bash
   python pipeline.py
   ```
3. Check `data/cleaned/` for the output and `data/logs/` for the run log.

**Expected input columns** (case and spacing are normalized automatically):
`warehouse_region`, `sku_code`, `product_name`, `category`, `date`, plus any sales and inventory measures.

---

## 5. Connecting to Power BI

1. In Power BI Desktop, choose **Get Data > Text/CSV** and select `data/combined/master_data.csv`.
2. Build the visuals: sales performance, stock levels, and stockout risk by warehouse and product.
3. Publish to the Power BI Service and configure a **scheduled refresh** (for example 6:00 AM) using an on-premises data gateway, or place the master file in OneDrive/SharePoint so the service can read it directly.
4. Schedule the pipeline to run **before** the Power BI refresh (see below).

### Scheduling the pipeline

- **Windows:** Task Scheduler, running `python pipeline.py` daily at 5:30 AM.
- **Linux/macOS:** cron, for example `30 5 * * * cd /path/to/project && python pipeline.py`.

---

## 6. Known limitations and fixes needed

These are documented honestly so the pipeline can be hardened before production use.

| # | Issue | Impact | Recommended fix |
|---|---|---|---|
| 1 | **Master file is never built.** `MASTER_FILE` is defined and the final log line references `master_data`, which does not exist | Script raises a `NameError` at the end; Power BI has no master file | Append `new_data` to `master_data.csv` (snippet below) |
| 2 | **Failed files are still marked as processed** | A file that errors is never retried | Track only successfully cleaned files |
| 3 | **`pd.concat` fails if every file errors** | Crash when `cleaned_data` is empty | Check the list is non-empty before concatenating |
| 4 | **Whitespace in values is not stripped** | `"asaba "` becomes `"Asaba "`, still different from `"Asaba"` | Apply `.str.strip()` before `.str.title()` |
| 5 | **Region abbreviations are not mapped** | `ASB` stays distinct from `Asaba` | Add a mapping dictionary (for example `{"Asb": "Asaba"}`) |
| 6 | **No duplicate removal** | Duplicated entries from repeated exports persist | Call `drop_duplicates()` on a key such as warehouse, SKU, and date |
| 7 | **Rows with unparseable dates become `NaT`** | Silent gaps in time-based reports | Log or quarantine rows where `date` is null |
| 8 | **`exit()` is notebook-style** | Unreliable in some script environments | Use `sys.exit()` |
| 9 | **SKU fix assumes at least 6 characters** | Short or malformed codes produce wrong output | Validate length and flag exceptions |
| 10 | **Supplier delivery data is not included** | No supplier performance view yet | Add a second ingestion path for the procurement workbook |

### Fix for issue 1: building the master file

```python
if MASTER_FILE.exists():
    master_data = pd.concat([pd.read_csv(MASTER_FILE), new_data], ignore_index=True)
else:
    master_data = new_data

master_data.to_csv(MASTER_FILE, index=False)
log(f"Total master records: {len(master_data)}")
```

### Fixes for issues 4 and 5: stripping whitespace and mapping regions

```python
REGION_MAP = {"Asb": "Asaba"}  # extend with other known abbreviations

data["warehouse_region"] = (
    data["warehouse_region"].str.strip().str.title().replace(REGION_MAP)
)
```

---

## 7. Roadmap

- [ ] Fix the known issues in section 6
- [ ] Add a stockout-risk field (for example days of cover = stock on hand / average daily sales)
- [ ] Ingest supplier delivery records and join them to inventory data
- [ ] Add data-quality checks and a summary report per run (rows in, rows dropped, rows with bad dates)
- [ ] Move to a database (such as SQLite or PostgreSQL) as the master store if data volume grows
- [ ] Email or Slack alert when a run fails or a warehouse file is missing

---

## 8. Expected outcome

| | Before | After (target) |
|---|---|---|
| Time to prepare data | 1 to 2 days of manual work | Seconds to minutes, automated |
| Data age at delivery | 3 to 4 days | Same day, refreshed each morning |
| Cleaning consistency | Dependent on the analyst | Identical rules every run |
| Auditability | None | Timestamped logs of every run and every dropped row |
