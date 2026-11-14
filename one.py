import argparse
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

REQUIRED_COLUMNS = ("Date", "RoomType", "RoomsSold", "Rate")


class Choice(Enum):
    DAILY = "1"
    ROOM_TYPE = "2"
    EXIT = "3"


class DataError(Exception):
    pass


@dataclass(frozen=True)
class LoadResult:
    data: pd.DataFrame
    warnings: tuple[str, ...]


def money(value: float) -> str:
    value = float(value)
    return f"Rs. {value:.0f}" if value.is_integer() else f"Rs. {value:.2f}"


def validate(raw: pd.DataFrame) -> LoadResult:
    frame = raw.copy()
    frame["Row"] = range(1, len(frame) + 1)

    dates = pd.to_datetime(frame["Date"].str.strip(), format="%Y-%m-%d", errors="coerce")
    room_type = frame["RoomType"].str.strip()
    rooms = pd.to_numeric(frame["RoomsSold"].str.strip(), errors="coerce")
    rate = pd.to_numeric(frame["Rate"].str.strip(), errors="coerce")

    rules = (
        (dates.isna(), "Date must be in YYYY-MM-DD format"),
        (room_type.eq(""), "RoomType must not be empty"),
        (rooms.isna(), "RoomsSold must be a number"),
        (rooms.lt(0), "RoomsSold must be 0 or more"),
        (rate.isna(), "Rate must be a number"),
        (rate.lt(0), "Rate must be 0 or more"),
    )

    reason = pd.Series([None] * len(frame), index=frame.index, dtype=object)
    for condition, message in rules:
        reason = reason.mask(reason.isna() & condition, message)

    invalid = reason.notna()
    warnings = tuple(
        f"Warning: Row {row} skipped - {text}."
        for row, text in zip(frame.loc[invalid, "Row"], reason[invalid])
    )

    clean = pd.DataFrame(
        {
            "Date": dates.dt.strftime("%Y-%m-%d"),
            "RoomType": room_type,
            "RoomsSold": rooms,
            "Rate": rate,
        }
    )[~invalid].reset_index(drop=True)
    clean["Revenue"] = clean["RoomsSold"] * clean["Rate"]
    return LoadResult(clean, warnings)


def load_sales(path: Path) -> LoadResult:
    if not path.is_file():
        raise FileNotFoundError(path)
    try:
        raw = pd.read_csv(path, dtype=str, keep_default_na=False, skipinitialspace=True)
    except pd.errors.EmptyDataError as exc:
        raise DataError("File is empty") from exc
    except pd.errors.ParserError as exc:
        raise DataError(f"File could not be parsed ({exc})") from exc

    raw.columns = raw.columns.str.strip()
    missing = [c for c in REQUIRED_COLUMNS if c not in raw.columns]
    if missing:
        raise DataError(f"Missing required column(s): {', '.join(missing)}")

    result = validate(raw[list(REQUIRED_COLUMNS)].fillna(""))
    if result.data.empty:
        for line in result.warnings:
            print(line)
        raise DataError("No valid records to analyse")
    return result


def save_figure(fig: plt.Figure, directory: Path, name: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / name
    fig.tight_layout()
    fig.savefig(target, dpi=150)
    plt.close(fig)
    return target


def plot_daily(daily: pd.Series, best_day: str, directory: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = ["tab:green" if day == best_day else "tab:blue" for day in daily.index]
    bars = ax.bar(daily.index, daily.to_numpy(), color=colors)
    ax.bar_label(bars, labels=[money(v) for v in daily], padding=3)
    ax.set_title("Daily Revenue")
    ax.set_xlabel("Date")
    ax.set_ylabel("Revenue (Rs.)")
    ax.margins(y=0.12)
    fig.autofmt_xdate()
    return save_figure(fig, directory, "daily_revenue.png")


def plot_share(by_type: pd.Series, directory: Path) -> Path:
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(by_type.to_numpy(), labels=by_type.index, autopct="%1.2f%%", startangle=90)
    ax.set_title("Revenue Share by Room Type")
    ax.axis("equal")
    return save_figure(fig, directory, "room_type_share.png")


def report_daily(data: pd.DataFrame, directory: Path, draw: bool) -> None:
    daily = data.groupby("Date")["Revenue"].sum().sort_index()
    best_day = daily.idxmax()
    for day, value in daily.items():
        print(f"{day} : {money(value)}")
    print(f"Total revenue: {money(daily.sum())}")
    print(f"Best day: {best_day} ({money(daily[best_day])})")
    if draw:
        print(f"Chart saved: {plot_daily(daily, best_day, directory)}")


def report_room_types(data: pd.DataFrame, directory: Path, draw: bool) -> None:
    by_type = data.groupby("RoomType")["Revenue"].sum().sort_values(ascending=False, kind="stable")
    total = by_type.sum()
    shares = by_type / total * 100 if total else by_type * 0
    for name, value in by_type.items():
        print(f"{name} : {money(value)} ({shares[name]:.2f}%)")
    print(f"Total revenue: {money(total)}")
    if draw and total:
        print(f"Chart saved: {plot_share(by_type, directory)}")


def prompt_choice() -> Choice:
    print("\n1. Daily revenue\n2. Revenue by room type\n3. Exit")
    try:
        return Choice(input("Select an option: ").strip())
    except ValueError:
        print("Invalid option. Please enter 1, 2 or 3.")
        return prompt_choice()
    except EOFError:
        return Choice.EXIT


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hotel Revenue Analyzer")
    parser.add_argument("file", nargs="?", default="hotel_sales.csv", type=Path)
    parser.add_argument("--menu", choices=("daily", "room"))
    parser.add_argument("--output-dir", default=Path("charts"), type=Path)
    parser.add_argument("--no-charts", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = load_sales(args.file)
    except FileNotFoundError:
        print(f"Error: File '{args.file}' not found.")
        return 1
    except DataError as exc:
        print(f"Error: {exc}.")
        return 1

    for line in result.warnings:
        print(line)
    print(f"Valid records analysed: {len(result.data)}")

    draw = not args.no_charts
    actions = {
        Choice.DAILY: report_daily,
        Choice.ROOM_TYPE: report_room_types,
    }

    if args.menu:
        choice = Choice.DAILY if args.menu == "daily" else Choice.ROOM_TYPE
        actions[choice](result.data, args.output_dir, draw)
        return 0

    while (choice := prompt_choice()) is not Choice.EXIT:
        actions[choice](result.data, args.output_dir, draw)
    return 0


if __name__ == "__main__":
    sys.exit(main())
