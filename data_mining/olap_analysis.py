"""
DriveCare Data Mining - OLAP Analysis

Implements:
1. Roll-up
2. Drill-down
3. Slice
4. Dice
5. Pivot

Uses the CSV-based star-schema warehouse.
Does not modify PostgreSQL records.
"""

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent

WAREHOUSE_DIR = (
    PROJECT_ROOT / "data_mining" / "warehouse"
)

OUTPUT_DIR = (
    PROJECT_ROOT / "data_mining" / "olap_results"
)


def load_warehouse():
    """Load the fact table and its required dimensions."""

    required_files = [
        "fact_bookings.csv",
        "dim_date.csv",
        "dim_service.csv",
        "dim_status.csv",
    ]

    for filename in required_files:
        if not (WAREHOUSE_DIR / filename).exists():
            raise FileNotFoundError(
                f"{filename} not found. "
                "Run warehouse.py first."
            )

    fact = pd.read_csv(
        WAREHOUSE_DIR / "fact_bookings.csv"
    )

    dates = pd.read_csv(
        WAREHOUSE_DIR / "dim_date.csv"
    )

    services = pd.read_csv(
        WAREHOUSE_DIR / "dim_service.csv"
    )

    statuses = pd.read_csv(
        WAREHOUSE_DIR / "dim_status.csv"
    )

    # Convert the date dimension's date column.
    dates["full_date"] = pd.to_datetime(
        dates["full_date"],
        errors="coerce",
    )

    # Join the fact table to its dimensions.
    data = fact.merge(
        dates,
        on="date_key",
        how="left",
        validate="many_to_one",
    )

    data = data.merge(
        services,
        on="service_key",
        how="left",
        validate="many_to_one",
    )

    data = data.merge(
        statuses,
        on="status_key",
        how="left",
        validate="many_to_one",
        suffixes=("", "_dimension"),
    )

    if len(data) != len(fact):
        raise ValueError(
            "Joining the dimensions changed the fact row count."
        )

    return data


def roll_up(data):
    """
    Roll-up: summarize booking counts by year and month.
    """

    result = (
        data.groupby(
            ["year", "month", "month_name"],
            dropna=False,
        )
        .agg(
            total_bookings=("booking_count", "sum"),
            distinct_customers=("customer_key", "nunique"),
        )
        .reset_index()
        .sort_values(["year", "month"])
    )

    return result


def drill_down(data):
    """
    Drill-down: progressively summarize by year,
    quarter, month, and day.
    """

    year_summary = (
        data.groupby("year")
        .agg(
            total_bookings=("booking_count", "sum")
        )
        .reset_index()
        .sort_values("year")
    )

    quarter_summary = (
        data.groupby(["year", "quarter"])
        .agg(
            total_bookings=("booking_count", "sum")
        )
        .reset_index()
        .sort_values(["year", "quarter"])
    )

    month_summary = (
        data.groupby(["year", "quarter", "month", "month_name"])
        .agg(
            total_bookings=("booking_count", "sum")
        )
        .reset_index()
        .sort_values(["year", "quarter", "month"])
    )

    day_summary = (
        data.groupby(["full_date"])
        .agg(
            total_bookings=("booking_count", "sum")
        )
        .reset_index()
        .sort_values("full_date")
    )

    return (
        year_summary,
        quarter_summary,
        month_summary,
        day_summary,
    )


def slice_analysis(data, selected_status="Completed"):
    """
    Slice: select one booking status.
    """

    result = data[
        data["status"].str.casefold()
        == selected_status.casefold()
    ].copy()

    return result


def dice_analysis(
    data,
    selected_statuses=None,
    selected_services=None,
    start_date=None,
    end_date=None,
):
    """
    Dice: filter on multiple dimensions simultaneously.

    All supplied filters are combined using AND logic.
    """

    result = data.copy()

    if selected_statuses:
        normalized_statuses = {
            value.casefold()
            for value in selected_statuses
        }

        result = result[
            result["status"].str.casefold().isin(
                normalized_statuses
            )
        ]

    if selected_services:
        normalized_services = {
            value.casefold()
            for value in selected_services
        }

        result = result[
            result["service_type"].str.casefold().isin(
                normalized_services
            )
        ]

    if start_date:
        result = result[
            result["full_date"]
            >= pd.Timestamp(start_date)
        ]

    if end_date:
        result = result[
            result["full_date"]
            <= pd.Timestamp(end_date)
        ]

    return result.copy()


def pivot_analysis(data):
    """
    Pivot: compare booking statuses across service types.
    """

    result = pd.pivot_table(
        data,
        index="service_type",
        columns="status",
        values="booking_count",
        aggfunc="sum",
        fill_value=0,
    )

    result["Total"] = result.sum(axis=1)

    result.loc["Grand Total"] = result.sum(axis=0)

    return result


def save_result(df, filename):
    """Save an analytical result to a CSV file."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = OUTPUT_DIR / filename

    df.to_csv(
        output_path,
        index=True,
        encoding="utf-8",
    )

    print(f"Saved: {output_path}")


def main():
    """Run all five OLAP operations."""

    print("\n" + "=" * 65)
    print("DRIVECARE DATA MINING - OLAP ANALYSIS")
    print("=" * 65)

    data = load_warehouse()

    print(f"\nWarehouse fact rows analyzed: {len(data):,}")

    # 1. Roll-up
    print("\n1. ROLL-UP: Bookings by year and month")

    rollup = roll_up(data)

    print(rollup.to_string(index=False))

    save_result(
        rollup,
        "rollup_monthly_bookings.csv",
    )

    # 2. Drill-down
    print("\n2. DRILL-DOWN: Yearly summary")

    year_summary, quarter_summary, month_summary, day_summary = (
        drill_down(data)
    )

    print(year_summary.to_string(index=False))

    print("\nQuarterly summary:")
    print(quarter_summary.to_string(index=False))

    save_result(
        year_summary,
        "drilldown_yearly.csv",
    )

    save_result(
        quarter_summary,
        "drilldown_quarterly.csv",
    )

    save_result(
        month_summary,
        "drilldown_monthly.csv",
    )

    save_result(
        day_summary,
        "drilldown_daily.csv",
    )

    # 3. Slice
    print("\n3. SLICE: Completed bookings")

    sliced = slice_analysis(
        data,
        selected_status="Completed",
    )

    print(f"Completed bookings: {len(sliced):,}")

    save_result(
        sliced,
        "slice_completed_bookings.csv",
    )

    # 4. Dice
    print("\n4. DICE: Multiple-condition analysis")

    diced = dice_analysis(
        data,
        selected_statuses=["Completed", "Confirmed"],
    )

    print(
        "Bookings with Completed or Confirmed status: "
        f"{len(diced):,}"
    )

    save_result(
        diced,
        "dice_completed_confirmed.csv",
    )

    # 5. Pivot
    print("\n5. PIVOT: Service type by booking status")

    pivot = pivot_analysis(data)

    print(pivot.to_string())

    save_result(
        pivot,
        "pivot_service_status.csv",
    )

    print("\nAll five OLAP operations completed.")
    print(f"Results directory: {OUTPUT_DIR}")
    print("=" * 65)


if __name__ == "__main__":
    main()