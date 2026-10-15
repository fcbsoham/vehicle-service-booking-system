"""
DriveCare Data Mining - ETL Pipeline

Extracts existing records from PostgreSQL, cleans the data in memory,
and saves analytical CSV files.

This script does not insert, update, or delete database records.
"""

import sys
from pathlib import Path
import sys

import pandas as pd

# Add the project root to Python's import path.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import app
from models.user import User
from models.vehicle import Vehicle
from models.booking import Booking


# Output directory for analytical datasets.
OUTPUT_DIR = PROJECT_ROOT / "data_mining" / "output"


def extract_data():
    """Extract users, vehicles, and bookings from PostgreSQL."""

    with app.app_context():
        users = User.query.all()
        vehicles = Vehicle.query.all()
        bookings = Booking.query.all()

        # Convert SQLAlchemy objects to ordinary Python dictionaries.
        users_data = [
            {
                "user_id": user.user_id,
                "full_name": user.full_name,
                "email": user.email,
                "role": user.role,
                "created_at": user.created_at,
            }
            for user in users
        ]

        vehicles_data = [
            {
                "vehicle_id": vehicle.vehicle_id,
                "user_id": vehicle.user_id,
                "brand": vehicle.brand,
                "model": vehicle.model,
                "year": vehicle.year,
                "registration_number": vehicle.registration_number,
                "fuel_type": vehicle.fuel_type,
                "created_at": vehicle.created_at,
            }
            for vehicle in vehicles
        ]

        bookings_data = [
            {
                "booking_id": booking.booking_id,
                "user_id": booking.user_id,
                "vehicle_id": booking.vehicle_id,
                "service_type": booking.service_type,
                "booking_date": booking.booking_date,
                "description": booking.description,
                "status": booking.status,
                "created_at": booking.created_at,
            }
            for booking in bookings
        ]

    # Return independent DataFrames after leaving the database context.
    return (
        pd.DataFrame(users_data),
        pd.DataFrame(vehicles_data),
        pd.DataFrame(bookings_data),
    )


def clean_text_columns(df, columns):
    """Trim surrounding whitespace and normalize empty strings."""

    for column in columns:
        if column in df.columns:
            df[column] = df[column].astype("string").str.strip()
            df[column] = df[column].replace("", pd.NA)

    return df


def transform_data(users, vehicles, bookings):
    """Clean extracted data and prepare a joined booking dataset."""

    # Clean text columns without changing the source database.
    users = clean_text_columns(
        users,
        ["full_name", "email", "role"],
    )

    vehicles = clean_text_columns(
        vehicles,
        ["brand", "model", "registration_number", "fuel_type"],
    )

    bookings = clean_text_columns(
        bookings,
        ["service_type", "status", "description"],
    )

    # Normalize email addresses and categorical text.
    if "email" in users.columns:
        users["email"] = users["email"].str.lower()

    if "role" in users.columns:
        users["role"] = users["role"].str.lower()

    if "service_type" in bookings.columns:
        bookings["service_type"] = bookings["service_type"].str.title()

    if "status" in bookings.columns:
        bookings["status"] = bookings["status"].str.strip().str.title()

    if "fuel_type" in vehicles.columns:
        vehicles["fuel_type"] = vehicles["fuel_type"].str.title()

    # Convert date fields into pandas datetime values.
    for df, date_columns in [
        (users, ["created_at"]),
        (vehicles, ["created_at"]),
        (bookings, ["booking_date", "created_at"]),
    ]:
        for column in date_columns:
            if column in df.columns:
                df[column] = pd.to_datetime(
                    df[column],
                    errors="coerce",
                )

    # Convert vehicle year to numeric where possible.
    if "year" in vehicles.columns:
        vehicles["year"] = pd.to_numeric(
            vehicles["year"],
            errors="coerce",
        )

    # Remove duplicate rows in the extracted analytical copies.
    users = users.drop_duplicates(subset=["user_id"])
    vehicles = vehicles.drop_duplicates(subset=["vehicle_id"])
    bookings = bookings.drop_duplicates(subset=["booking_id"])

    # Exclude rows with missing primary keys from analytical copies.
    users = users.dropna(subset=["user_id"])
    vehicles = vehicles.dropna(subset=["vehicle_id"])
    bookings = bookings.dropna(subset=["booking_id"])

    # Build a booking-level analytical dataset.
    # Left joins preserve bookings even if a related record is missing.
    booking_analysis = bookings.merge(
        users[
            ["user_id", "full_name", "role"]
        ],
        on="user_id",
        how="left",
        validate="many_to_one",
    )

    booking_analysis = booking_analysis.merge(
        vehicles[
            ["vehicle_id", "brand", "model", "year", "fuel_type"]
        ],
        on="vehicle_id",
        how="left",
        validate="many_to_one",
    )

    # Flag missing relationships rather than silently discarding records.
    booking_analysis["missing_customer"] = (
        booking_analysis["full_name"].isna()
    )

    booking_analysis["missing_vehicle"] = (
        booking_analysis["brand"].isna()
        | booking_analysis["model"].isna()
    )

    return users, vehicles, bookings, booking_analysis


def save_datasets(users, vehicles, bookings, booking_analysis):
    """Save the transformed datasets as CSV files."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    datasets = {
        "cleaned_users.csv": users,
        "cleaned_vehicles.csv": vehicles,
        "cleaned_bookings.csv": bookings,
        "booking_analysis.csv": booking_analysis,
    }

    for filename, df in datasets.items():
        output_path = OUTPUT_DIR / filename

        # UTF-8 CSV output; source database is not modified.
        df.to_csv(output_path, index=False, encoding="utf-8")

        print(f"Saved: {output_path}")
        print(f"Rows: {len(df):,} | Columns: {len(df.columns)}")


def main():
    """Run the complete ETL workflow."""

    print("\n" + "=" * 60)
    print("DRIVECARE DATA MINING - ETL PIPELINE")
    print("=" * 60)

    print("\n[1/3] Extracting records from PostgreSQL...")

    users, vehicles, bookings = extract_data()

    print(f"Users extracted: {len(users):,}")
    print(f"Vehicles extracted: {len(vehicles):,}")
    print(f"Bookings extracted: {len(bookings):,}")

    print("\n[2/3] Cleaning and transforming analytical copies...")

    users, vehicles, bookings, booking_analysis = transform_data(
        users,
        vehicles,
        bookings,
    )

    print(f"Users after cleaning: {len(users):,}")
    print(f"Vehicles after cleaning: {len(vehicles):,}")
    print(f"Bookings after cleaning: {len(bookings):,}")
    print(f"Joined booking records: {len(booking_analysis):,}")

    if not booking_analysis.empty:
        missing_customers = int(
            booking_analysis["missing_customer"].sum()
        )
        missing_vehicles = int(
            booking_analysis["missing_vehicle"].sum()
        )

        print(f"Bookings with missing customer details: {missing_customers}")
        print(f"Bookings with missing vehicle details: {missing_vehicles}")

        print("\nBooking status distribution:")

        print(
            booking_analysis["status"]
            .fillna("Unknown")
            .value_counts()
            .to_string()
        )

    print("\n[3/3] Saving analytical datasets...")

    save_datasets(
        users,
        vehicles,
        bookings,
        booking_analysis,
    )

    print("\nETL pipeline completed successfully.")
    print("No database records were inserted, updated, or deleted.")
    print("=" * 60)


if __name__ == "__main__":
    main()