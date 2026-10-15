"""
DriveCare Data Warehouse
Builds a star-schema warehouse from the cleaned ETL CSV files.

This implementation creates analytical CSV files only.
It does not modify PostgreSQL operational records.
"""

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = PROJECT_ROOT / "data_mining" / "output"
WAREHOUSE_DIR = PROJECT_ROOT / "data_mining" / "warehouse"


def load_source_data():
    """Load the cleaned datasets produced by the ETL pipeline."""

    required_files = [
        "cleaned_users.csv",
        "cleaned_vehicles.csv",
        "cleaned_bookings.csv",
    ]

    for filename in required_files:
        path = INPUT_DIR / filename

        if not path.exists():
            raise FileNotFoundError(
                f"{path} not found. Run etl_pipeline.py first."
            )

    users = pd.read_csv(INPUT_DIR / "cleaned_users.csv")
    vehicles = pd.read_csv(INPUT_DIR / "cleaned_vehicles.csv")
    bookings = pd.read_csv(INPUT_DIR / "cleaned_bookings.csv")

    return users, vehicles, bookings


def build_customer_dimension(users):
    """Create the customer dimension."""

    dim_customer = users[
        ["user_id", "full_name", "role"]
    ].copy()

    dim_customer = dim_customer.rename(
        columns={"user_id": "source_user_id"}
    )

    # Surrogate key for the dimension.
    dim_customer.insert(
        0,
        "customer_key",
        range(1, len(dim_customer) + 1),
    )

    return dim_customer


def build_vehicle_dimension(vehicles):
    """Create the vehicle dimension."""

    columns = [
        "vehicle_id",
        "brand",
        "model",
        "year",
        "fuel_type",
    ]

    dim_vehicle = vehicles[columns].copy()

    dim_vehicle = dim_vehicle.rename(
        columns={"vehicle_id": "source_vehicle_id"}
    )

    dim_vehicle.insert(
        0,
        "vehicle_key",
        range(1, len(dim_vehicle) + 1),
    )

    return dim_vehicle


def build_date_dimension(bookings):
    """Create a date dimension from booking dates."""

    dates = pd.to_datetime(
        bookings["booking_date"],
        errors="coerce",
    ).dropna()

    unique_dates = pd.Series(
        dates.dt.normalize().unique()
    ).sort_values().reset_index(drop=True)

    dim_date = pd.DataFrame({
        "full_date": pd.to_datetime(unique_dates)
    })

    dim_date["date_key"] = (
        dim_date["full_date"].dt.strftime("%Y%m%d").astype(int)
    )

    dim_date["year"] = dim_date["full_date"].dt.year
    dim_date["quarter"] = dim_date["full_date"].dt.quarter
    dim_date["month"] = dim_date["full_date"].dt.month
    dim_date["month_name"] = dim_date["full_date"].dt.month_name()
    dim_date["day"] = dim_date["full_date"].dt.day
    dim_date["weekday"] = dim_date["full_date"].dt.day_name()

    return dim_date[
        [
            "date_key",
            "full_date",
            "year",
            "quarter",
            "month",
            "month_name",
            "day",
            "weekday",
        ]
    ]


def build_service_dimension(bookings):
    """Create a service dimension."""

    services = (
        bookings["service_type"]
        .dropna()
        .astype(str)
        .drop_duplicates()
        .sort_values()
        .reset_index(drop=True)
    )

    dim_service = pd.DataFrame({
        "service_type": services
    })

    dim_service.insert(
        0,
        "service_key",
        range(1, len(dim_service) + 1),
    )

    return dim_service


def build_status_dimension(bookings):
    """Create a booking status dimension."""

    statuses = (
        bookings["status"]
        .dropna()
        .astype(str)
        .drop_duplicates()
        .sort_values()
        .reset_index(drop=True)
    )

    dim_status = pd.DataFrame({
        "status": statuses
    })

    dim_status.insert(
        0,
        "status_key",
        range(1, len(dim_status) + 1),
    )

    return dim_status


def build_fact_table(
    bookings,
    dim_customer,
    dim_vehicle,
    dim_date,
    dim_service,
    dim_status,
):
    """Create the central booking fact table."""

    fact = bookings[
        [
            "booking_id",
            "user_id",
            "vehicle_id",
            "booking_date",
            "service_type",
            "status",
        ]
    ].copy()

    fact["booking_date"] = pd.to_datetime(
        fact["booking_date"],
        errors="coerce",
    ).dt.normalize()

    # Map source IDs and categorical values to dimension keys.
    customer_map = dim_customer.set_index(
        "source_user_id"
    )["customer_key"]

    vehicle_map = dim_vehicle.set_index(
        "source_vehicle_id"
    )["vehicle_key"]

    date_map = dim_date.set_index(
        "full_date"
    )["date_key"]

    service_map = dim_service.set_index(
        "service_type"
    )["service_key"]

    status_map = dim_status.set_index(
        "status"
    )["status_key"]

    fact["customer_key"] = fact["user_id"].map(customer_map)
    fact["vehicle_key"] = fact["vehicle_id"].map(vehicle_map)
    fact["date_key"] = fact["booking_date"].map(date_map)
    fact["service_key"] = fact["service_type"].map(service_map)
    fact["status_key"] = fact["status"].map(status_map)

    # One fact row represents one booking.
    fact["booking_count"] = 1

    fact = fact[
        [
            "booking_id",
            "customer_key",
            "vehicle_key",
            "date_key",
            "service_key",
            "status_key",
            "booking_count",
        ]
    ]

    # Check whether dimension mapping succeeded.
    key_columns = [
        "customer_key",
        "vehicle_key",
        "date_key",
        "service_key",
        "status_key",
    ]

    missing_keys = fact[key_columns].isna().sum()

    if missing_keys.any():
        raise ValueError(
            "Some fact rows could not be mapped to dimensions:\n"
            + missing_keys[missing_keys > 0].to_string()
        )

    # Dimension keys must be integral.
    for column in key_columns:
        fact[column] = fact[column].astype(int)

    return fact


def main():
    """Build and save all star-schema tables."""

    print("\n" + "=" * 60)
    print("DRIVECARE DATA WAREHOUSE")
    print("=" * 60)

    print("\nLoading cleaned ETL datasets...")

    users, vehicles, bookings = load_source_data()

    print(f"Users: {len(users):,}")
    print(f"Vehicles: {len(vehicles):,}")
    print(f"Bookings: {len(bookings):,}")

    print("\nBuilding dimension tables...")

    dim_customer = build_customer_dimension(users)
    dim_vehicle = build_vehicle_dimension(vehicles)
    dim_date = build_date_dimension(bookings)
    dim_service = build_service_dimension(bookings)
    dim_status = build_status_dimension(bookings)

    print("\nBuilding fact table...")

    fact_bookings = build_fact_table(
        bookings,
        dim_customer,
        dim_vehicle,
        dim_date,
        dim_service,
        dim_status,
    )

    # Ensure every source booking appears exactly once.
    if len(fact_bookings) != len(bookings):
        raise ValueError(
            "Fact table row count differs from source booking count."
        )

    if fact_bookings["booking_id"].duplicated().any():
        raise ValueError("Duplicate booking IDs found in fact table.")

    WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)

    tables = {
        "dim_customer.csv": dim_customer,
        "dim_vehicle.csv": dim_vehicle,
        "dim_date.csv": dim_date,
        "dim_service.csv": dim_service,
        "dim_status.csv": dim_status,
        "fact_bookings.csv": fact_bookings,
    }

    print("\nSaving warehouse tables...")

    for filename, dataframe in tables.items():
        output_path = WAREHOUSE_DIR / filename

        dataframe.to_csv(
            output_path,
            index=False,
            encoding="utf-8",
        )

        print(
            f"{filename}: {len(dataframe):,} rows, "
            f"{len(dataframe.columns)} columns"
        )

    print("\nWarehouse validation passed.")
    print(f"Fact rows: {len(fact_bookings):,}")
    print("Each fact row represents one booking.")
    print("No PostgreSQL records were modified.")
    print(f"Output directory: {WAREHOUSE_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()