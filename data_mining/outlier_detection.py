"""
DriveCare Data Mining - Customer Outlier Detection

Algorithm:
    Isolation Forest

Input:
    data_mining/output/cleaned_users.csv
    data_mining/output/cleaned_bookings.csv

Output:
    data_mining/outlier_results/

The analysis reads CSV files only and does not modify
PostgreSQL records.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

INPUT_DIR = PROJECT_ROOT / "data_mining" / "output"

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data_mining"
    / "outlier_results"
)

CONTAMINATION = 0.05
RANDOM_STATE = 42


# --------------------------------------------------
# STEP 1: LOAD DATA
# --------------------------------------------------

def load_data():
    """Load cleaned users and bookings."""

    users_file = INPUT_DIR / "cleaned_users.csv"
    bookings_file = INPUT_DIR / "cleaned_bookings.csv"

    if not users_file.exists() or not bookings_file.exists():
        raise FileNotFoundError(
            "Required cleaned CSV files are missing. "
            "Run data_mining/etl_pipeline.py first."
        )

    users = pd.read_csv(users_file)
    bookings = pd.read_csv(bookings_file)

    required_user_columns = {
        "user_id",
        "full_name",
    }

    required_booking_columns = {
        "user_id",
        "service_type",
        "status",
    }

    if not required_user_columns.issubset(users.columns):
        raise ValueError(
            "The users dataset is missing required columns."
        )

    if not required_booking_columns.issubset(bookings.columns):
        raise ValueError(
            "The bookings dataset is missing required columns."
        )

    return users, bookings


# --------------------------------------------------
# STEP 2: AGGREGATE CUSTOMER BEHAVIOUR
# --------------------------------------------------

def build_customer_features(users, bookings):
    """Build one feature record per customer."""

    users = users.copy()
    bookings = bookings.copy()

    bookings["status"] = (
        bookings["status"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.casefold()
    )

    bookings["service_type"] = (
        bookings["service_type"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    booking_summary = (
        bookings.groupby("user_id")
        .agg(
            total_bookings=("user_id", "size"),
            completed_bookings=(
                "status",
                lambda values: (values == "completed").sum(),
            ),
            confirmed_bookings=(
                "status",
                lambda values: (values == "confirmed").sum(),
            ),
            pending_bookings=(
                "status",
                lambda values: (values == "pending").sum(),
            ),
            cancelled_bookings=(
                "status",
                lambda values: (values == "cancelled").sum(),
            ),
        )
        .reset_index()
    )

    service_summary = (
        bookings.loc[bookings["service_type"].ne("")]
        .groupby("user_id")["service_type"]
        .nunique()
        .rename("distinct_services")
        .reset_index()
    )

    customer_data = (
        users[["user_id", "full_name"]]
        .drop_duplicates(subset=["user_id"])
        .merge(
            booking_summary,
            on="user_id",
            how="left",
        )
        .merge(
            service_summary,
            on="user_id",
            how="left",
        )
    )

    numeric_features = [
        "total_bookings",
        "completed_bookings",
        "confirmed_bookings",
        "pending_bookings",
        "cancelled_bookings",
        "distinct_services",
    ]

    customer_data[numeric_features] = (
        customer_data[numeric_features]
        .fillna(0)
        .astype(int)
    )

    return customer_data, numeric_features


# --------------------------------------------------
# STEP 3: DETECT OUTLIERS
# --------------------------------------------------

def detect_outliers(customer_data, numeric_features):
    """
    Fit Isolation Forest to standardized customer features.

    Isolation Forest returns:
        1  = inlier
       -1  = outlier
    """

    df = customer_data.copy()

    X = df[numeric_features].fillna(0)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = IsolationForest(
        n_estimators=200,
        contamination=CONTAMINATION,
        random_state=RANDOM_STATE,
    )

    predictions = model.fit_predict(X_scaled)

    df["outlier_flag"] = predictions
    df["is_outlier"] = df["outlier_flag"].eq(-1)

    # Higher anomaly scores indicate observations more typical
    # of the inlier population. Lower scores indicate anomalies.
    df["anomaly_score"] = model.decision_function(X_scaled)

    return df


# --------------------------------------------------
# STEP 4: CREATE AN OUTLIER REPORT
# --------------------------------------------------

def save_results(df, numeric_features):
    """Save full assignments, flagged customers and a chart."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    assignments_path = (
        OUTPUT_DIR / "customer_outlier_analysis.csv"
    )

    df.to_csv(
        assignments_path,
        index=False,
        encoding="utf-8",
    )

    outliers = (
        df.loc[df["is_outlier"]]
        .sort_values("anomaly_score")
        .copy()
    )

    outliers_path = (
        OUTPUT_DIR / "flagged_customers.csv"
    )

    outliers.to_csv(
        outliers_path,
        index=False,
        encoding="utf-8",
    )

    # Plot booking frequency against cancellations.
    fig, ax = plt.subplots(figsize=(9, 6))

    normal_customers = df.loc[~df["is_outlier"]]
    flagged_customers = df.loc[df["is_outlier"]]

    ax.scatter(
        normal_customers["total_bookings"],
        normal_customers["cancelled_bookings"],
        label="Typical pattern",
        alpha=0.7,
    )

    ax.scatter(
        flagged_customers["total_bookings"],
        flagged_customers["cancelled_bookings"],
        label="Flagged as outlier",
        marker="x",
        s=90,
    )

    ax.set_title("Customer Booking Outlier Detection")
    ax.set_xlabel("Total Bookings")
    ax.set_ylabel("Cancelled Bookings")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.3)

    fig.tight_layout()

    chart_path = OUTPUT_DIR / "customer_outliers.png"

    fig.savefig(
        chart_path,
        dpi=150,
        bbox_inches="tight",
    )

    plt.close(fig)

    return outliers, assignments_path, outliers_path, chart_path


# --------------------------------------------------
# STEP 5: RUN THE ANALYSIS
# --------------------------------------------------

def main():
    print("\n" + "=" * 65)
    print("DRIVECARE - CUSTOMER OUTLIER DETECTION")
    print("=" * 65)

    users, bookings = load_data()

    print(f"\nCustomers loaded: {len(users):,}")
    print(f"Bookings loaded: {len(bookings):,}")

    customer_data, numeric_features = (
        build_customer_features(users, bookings)
    )

    print(
        f"Customer records prepared: "
        f"{len(customer_data):,}"
    )

    results = detect_outliers(
        customer_data,
        numeric_features,
    )

    outliers, assignments_path, outliers_path, chart_path = (
        save_results(results, numeric_features)
    )

    total_customers = len(results)
    outlier_count = int(results["is_outlier"].sum())
    normal_count = total_customers - outlier_count

    print("\n" + "=" * 65)
    print("OUTLIER DETECTION SUMMARY")
    print("=" * 65)

    print(f"Total customers: {total_customers}")
    print(f"Typical-pattern customers: {normal_count}")
    print(f"Flagged outliers: {outlier_count}")

    if total_customers:
        print(
            f"Flagged percentage: "
            f"{outlier_count / total_customers * 100:.2f}%"
        )

    print("\nFlagged customer details:")

    if outliers.empty:
        print("No customers were flagged.")
    else:
        columns_to_display = [
            "user_id",
            "full_name",
            "total_bookings",
            "completed_bookings",
            "confirmed_bookings",
            "pending_bookings",
            "cancelled_bookings",
            "distinct_services",
            "anomaly_score",
        ]

        print(
            outliers[columns_to_display]
            .round(4)
            .to_string(index=False)
        )

    print("\nSaved files:")
    print(assignments_path)
    print(outliers_path)
    print(chart_path)

    print("\nOutlier detection completed.")
    print(
        "A flagged outlier is an unusual pattern, "
        "not proof of fraud or misconduct."
    )
    print("PostgreSQL records were not modified.")
    print("=" * 65)


if __name__ == "__main__":
    main()