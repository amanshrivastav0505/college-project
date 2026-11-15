# Hotel Revenue Analyzer

**PS No. 70** | Language: Python 3 | Concepts: Pandas, CSV, Visualization

A command-line program that reads hotel room sales from a CSV file, validates every row, calculates revenue (`Revenue = RoomsSold x Rate`), and reports:

- daily revenue, total revenue and the best day
- revenue share of each room type
- charts for both reports (saved as PNG images)

Rows with negative or non-numeric values are skipped, and a warning is shown for each one.

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Project Structure](#project-structure)
3. [Requirements and Installation](#requirements-and-installation)
4. [Input File Format](#input-file-format)
5. [How to Run](#how-to-run)
6. [Validation Rules](#validation-rules)
7. [Code Explanation](#code-explanation)
8. [Test Cases](#test-cases)
9. [Bare Minimum Requirements Checklist](#bare-minimum-requirements-checklist)
10. [Advanced Concepts Used](#advanced-concepts-used)
11. [Design Notes](#design-notes)

---

## Problem Statement

Read `hotel_sales.csv` with Pandas. Revenue = RoomsSold x Rate. Show daily revenue, the best day and the revenue share of each room type, with charts. Skip rows with negative or non-numeric values.

Sample data (`hotel_sales.csv`):

```csv
Date,RoomType,RoomsSold,Rate
2026-10-01,Standard,10,2000
2026-10-01,Deluxe,5,3500
2026-10-02,Standard,12,2000
2026-10-02,Deluxe,6,3500
2026-10-03,Standard,8,2000
2026-10-03,Deluxe,4,3500
```

---

## Project Structure

```
.
├── hotel_revenue.py      # the complete solution (single .py file)
├── hotel_sales.csv       # sample data (Test Cases 1 and 4)
├── one_row.csv           # one data row (Test Case 2)
├── invalid_rows.csv      # sample data plus invalid rows (Test Case 3a)
├── charts/               # generated automatically when the program runs
│   ├── daily_revenue.png
│   └── room_type_share.png
└── README.md
```

---

## Requirements and Installation

- Python 3.10 or newer (the code uses the `list[str] | None` type syntax and the walrus operator)
- pandas
- matplotlib

Install the libraries:

```bash
pip install pandas matplotlib
```

---

## Input File Format

The CSV file must contain these four columns (column order does not matter, extra columns are ignored):

| Column      | Meaning                          | Rule                              |
|-------------|----------------------------------|-----------------------------------|
| `Date`      | Date of the sale                 | Format `YYYY-MM-DD`               |
| `RoomType`  | Category of the room             | Must not be empty                 |
| `RoomsSold` | Number of rooms sold that day    | Number, 0 or more                 |
| `Rate`      | Price per room in rupees         | Number, 0 or more                 |

---

## How to Run

**Interactive menu** (default file is `hotel_sales.csv`):

```bash
python hotel_revenue.py
python hotel_revenue.py hotel_sales.csv
```

```
1. Daily revenue
2. Revenue by room type
3. Exit
Select an option:
```

**Direct report without the menu:**

```bash
python hotel_revenue.py hotel_sales.csv --menu daily
python hotel_revenue.py hotel_sales.csv --menu room
```

**Command-line options:**

| Option               | Description                                              |
|----------------------|----------------------------------------------------------|
| `file`               | Path of the CSV file (default: `hotel_sales.csv`)        |
| `--menu daily`       | Show the daily revenue report and exit                   |
| `--menu room`        | Show the revenue by room type report and exit            |
| `--output-dir DIR`   | Folder where charts are saved (default: `charts`)        |
| `--no-charts`        | Do not create chart images                               |

**Exit codes:** `0` on success, `1` if the file is missing, empty, unreadable, has missing columns, or has no valid rows.

---

## Validation Rules

Each data row is numbered starting from 1 (the first row after the header is Row 1). The first rule a row fails decides its warning message, and the row is excluded from all calculations.

| Order | Check                         | Warning text                                          |
|-------|-------------------------------|-------------------------------------------------------|
| 1     | Date is not `YYYY-MM-DD`      | `Warning: Row N skipped - Date must be in YYYY-MM-DD format.` |
| 2     | RoomType is empty             | `Warning: Row N skipped - RoomType must not be empty.` |
| 3     | RoomsSold is not a number     | `Warning: Row N skipped - RoomsSold must be a number.` |
| 4     | RoomsSold is negative         | `Warning: Row N skipped - RoomsSold must be 0 or more.` |
| 5     | Rate is not a number          | `Warning: Row N skipped - Rate must be a number.`     |
| 6     | Rate is negative              | `Warning: Row N skipped - Rate must be 0 or more.`    |

After loading, the program prints `Valid records analysed: <count>`.

---

## Code Explanation

### Imports and constants

| Item               | Purpose                                                                              |
|--------------------|--------------------------------------------------------------------------------------|
| `argparse`         | Reads command-line arguments (`file`, `--menu`, `--output-dir`, `--no-charts`)       |
| `sys`              | Used for `sys.exit(main())` so the exit code reaches the console                     |
| `dataclass`        | Creates the small `LoadResult` container class                                       |
| `Enum`             | Creates the `Choice` menu options                                                    |
| `Path`             | Handles file and folder paths in a portable way                                      |
| `matplotlib.use("Agg")` | Selects a non-interactive backend so charts are saved to files and the program works without a display |
| `pandas`           | Reads the CSV, validates the data and performs the grouping                          |
| `REQUIRED_COLUMNS` | Tuple of the four column names the CSV must contain                                  |

### Classes

**`Choice(Enum)`**
Defines the menu options as named constants: `DAILY = "1"`, `ROOM_TYPE = "2"`, `EXIT = "3"`. Calling `Choice("1")` converts the typed text to the matching option and raises `ValueError` for anything else, which gives free input validation.

**`DataError(Exception)`**
A custom exception for problems with the file contents (empty file, missing columns, no valid rows). It keeps data problems separate from the "file not found" case so each one gets its own error message.

**`LoadResult` (frozen dataclass)**
An immutable container with two fields:
- `data`: a DataFrame holding only the valid rows, with the `Revenue` column added
- `warnings`: a tuple of warning messages, one per skipped row

### Functions

**`money(value)`**
Formats a number as rupees. Whole numbers are shown without decimals (`Rs. 37500`), other values with two decimals (`Rs. 1250.50`). It uses `float.is_integer()` to decide.

**`validate(raw)`**
Cleans and checks the raw text data.
1. Adds a `Row` number to each record.
2. Converts `Date` with `pd.to_datetime(..., format="%Y-%m-%d", errors="coerce")`, and `RoomsSold` and `Rate` with `pd.to_numeric(..., errors="coerce")`. Anything that cannot be converted becomes `NaN`.
3. Builds a list of `(condition, message)` rules. Each condition is a boolean Series covering all rows at once (vectorised, no row-by-row loop).
4. Fills a `reason` Series using `Series.mask`. A row only receives a reason if it does not have one yet, so the first failed rule wins.
5. Creates the warning strings for every row that has a reason.
6. Builds a clean DataFrame from the valid rows only and adds the column `Revenue = RoomsSold * Rate`.
7. Returns a `LoadResult`.

**`load_sales(path)`**
Reads and checks the file.
1. Raises `FileNotFoundError` if the file does not exist.
2. Reads the CSV with `dtype=str` and `keep_default_na=False`, so every value arrives as plain text and the program, not Pandas, decides what is valid.
3. Converts `EmptyDataError` and `ParserError` into `DataError`.
4. Strips spaces from column names and raises `DataError` if a required column is missing.
5. Calls `validate`. If no valid row remains, it prints the warnings and raises `DataError("No valid records to analyse")`.

**`save_figure(fig, directory, name)`**
Creates the output folder if needed, applies `tight_layout`, saves the figure at 150 dpi, closes the figure to free memory, and returns the saved path.

**`plot_daily(daily, best_day, directory)`**
Draws a bar chart of revenue per day. The best day's bar is green and the others are blue. Each bar is labelled with its amount. Saved as `daily_revenue.png`.

**`plot_share(by_type, directory)`**
Draws a pie chart of revenue per room type with percentage labels. Saved as `room_type_share.png`.

**`report_daily(data, directory, draw)`**
Groups the data by `Date`, sums `Revenue`, and sorts by date. It prints each day, the total revenue, and the best day (found with `idxmax()`). If `draw` is true, it also saves the bar chart.

**`report_room_types(data, directory, draw)`**
Groups the data by `RoomType`, sums `Revenue`, and sorts from highest to lowest. Each share is `revenue / total * 100`. If the total is zero, shares are set to 0 to avoid division by zero, and the pie chart is skipped. It prints each type with its percentage and the total revenue.

**`prompt_choice()`**
Prints the menu and reads the user's choice. A valid choice returns a `Choice`. An invalid choice shows an error and asks again. If input ends (Ctrl+D or piped input finishing), it returns `Choice.EXIT` so the program closes cleanly.

**`parse_args(argv)`**
Defines and parses the command-line options using `argparse`. Accepts an optional list so the function can also be tested without a real command line.

**`main(argv=None)`**
Controls the whole program.
1. Parses arguments and loads the file. On `FileNotFoundError` it prints `Error: File '<name>' not found.`, and on `DataError` it prints `Error: <message>.`. Both return exit code 1.
2. Prints the warnings, then `Valid records analysed: <count>`.
3. Builds a dictionary that maps each `Choice` to its report function.
4. If `--menu` was given, runs that one report and returns 0.
5. Otherwise runs the interactive loop `while (choice := prompt_choice()) is not Choice.EXIT`.

---

## Test Cases

All four cases were run and produced the expected output.

### Test Case 1: Normal Input

File: `hotel_sales.csv` (sample above) | Menu: Daily revenue

```bash
python hotel_revenue.py hotel_sales.csv --menu daily
```

```
Valid records analysed: 6
2026-10-01 : Rs. 37500
2026-10-02 : Rs. 45000
2026-10-03 : Rs. 30000
Total revenue: Rs. 112500
Best day: 2026-10-02 (Rs. 45000)
Chart saved: charts/daily_revenue.png
```

### Test Case 2: Boundary / Minimum Input

File: `one_row.csv`, containing one data row `2026-10-01,Standard,1,2000`

```bash
python hotel_revenue.py one_row.csv --menu daily
```

```
Valid records analysed: 1
2026-10-01 : Rs. 2000
Total revenue: Rs. 2000
Best day: 2026-10-01 (Rs. 2000)
Chart saved: charts/daily_revenue.png
```

### Test Case 3: Invalid Input

**(a)** `invalid_rows.csv` is the sample file with an extra row `2026-10-04,Deluxe,-3,3500` as Row 7. It also includes a Row 8 `2026-10-04,Standard,abc,2000` to show the non-numeric check. Delete Row 8 to get exactly the single-warning output of the problem statement.

```bash
python hotel_revenue.py invalid_rows.csv --menu daily
```

```
Warning: Row 7 skipped - RoomsSold must be 0 or more.
Warning: Row 8 skipped - RoomsSold must be a number.
Valid records analysed: 6
2026-10-01 : Rs. 37500
2026-10-02 : Rs. 45000
2026-10-03 : Rs. 30000
Total revenue: Rs. 112500
Best day: 2026-10-02 (Rs. 45000)
Chart saved: charts/daily_revenue.png
```

**(b)** File `sales_old.csv` does not exist.

```bash
python hotel_revenue.py sales_old.csv --menu daily
```

```
Error: File 'sales_old.csv' not found.
```

### Test Case 4: Different Valid Scenario

File: `hotel_sales.csv` | Menu: Revenue by room type

```bash
python hotel_revenue.py hotel_sales.csv --menu room
```

```
Valid records analysed: 6
Standard : Rs. 60000 (53.33%)
Deluxe : Rs. 52500 (46.67%)
Total revenue: Rs. 112500
Chart saved: charts/room_type_share.png
```

### Summary

| Test case | Input                         | Expected result                        | Status |
|-----------|-------------------------------|----------------------------------------|--------|
| 1         | `hotel_sales.csv`, daily      | 37500 / 45000 / 30000, total 112500, best day 2026-10-02 | Pass |
| 2         | `one_row.csv`, daily          | Total 2000, best day 2026-10-01        | Pass   |
| 3a        | `invalid_rows.csv`            | Row 7 warning, 6 valid records         | Pass   |
| 3b        | `sales_old.csv` (missing)     | `Error: File 'sales_old.csv' not found.` | Pass |
| 4         | `hotel_sales.csv`, room type  | Standard 53.33%, Deluxe 46.67%         | Pass   |

---

## Bare Minimum Requirements Checklist

| # | Requirement                                                     | Where it is done                              |
|---|-----------------------------------------------------------------|-----------------------------------------------|
| 1 | Solution in Python 3, one `.py` file, run from the console      | `hotel_revenue.py`                            |
| 2 | Load the CSV with Pandas and report how many valid rows were read | `load_sales`, and `Valid records analysed` in `main` |
| 3 | Create a Revenue column (RoomsSold x Rate)                      | End of `validate`                             |
| 4 | Skip negative or non-numeric rows and show a warning            | `validate` rules and warning messages         |
| 5 | Test with all four test cases                                   | [Test Cases](#test-cases)                     |

---

## Advanced Concepts Used

- **Vectorised validation:** boolean Series rules and `Series.mask` instead of loops
- **Safe type conversion:** `pd.to_numeric` and `pd.to_datetime` with `errors="coerce"`
- **Enum-based menu:** with a dispatch dictionary replacing long `if/elif` chains
- **Frozen dataclass:** an immutable result object
- **Custom exception:** `DataError` for clean error handling
- **Type hints:** including the modern `X | None` syntax
- **Walrus operator `:=`:** assigns and tests the menu choice in the loop condition
- **argparse:** both a command-line mode and an interactive mode
- **Headless plotting:** `matplotlib` with the `Agg` backend
- **Pandas `groupby`, `idxmax`, `sort_values`:** for aggregation

---

## Design Notes

- Every CSV value is read as text first, so invalid entries such as `abc` are caught and reported instead of silently becoming `NaN` or crashing.
- Revenue is computed only after validation, so skipped rows can never affect any total.
- If two days have the same highest revenue, the earliest date is reported as the best day.
- Amounts that are not whole numbers are shown with two decimals.

---

##Author

Aman kumar
