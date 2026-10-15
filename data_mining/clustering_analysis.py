"""
DriveCare Data Mining - Customer Clustering Analysis

Algorithms:
    1. K-Means Clustering
    2. Hierarchical Agglomerative Clustering

Input:
    data_mining/output/cleaned_users.csv
    data_mining/output/cleaned_bookings.csv

Output:
    data_mining/clustering_results/

This module reads analytical CSV files only.
It does not modify PostgreSQL records.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler


# --------------------------------------------------
# PATHS AND CONFIGURATION
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

INPUT_DIR = PROJECT_ROOT / "data_mining" / "output"

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data_mining"
    / "clustering_results"
)

RANDOM_STATE = 42
N_CLUSTERS = 3


# --------------------------------------------------
# STEP 1: LOAD ANALYTICAL DATA
# --------------------------------------------------

def load_data():
    """Load cleaned users and bookings from CSV files."""

    users_file = INPUT_DIR / "cleaned_users.csv"
    bookings_file = INPUT_DIR / "cleaned_bookings.csv"

    if not users_file.exists():
        raise FileNotFoundError(
            f"Users dataset not found: {users_file}. "
            "Run etl_pipeline.py first."
        )

    if not bookings_file.exists():
        raise FileNotFoundError(
            f"Bookings dataset not found: {bookings_file}. "
            "Run etl_pipeline.py first."
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
            "The users dataset does not contain the required columns."
        )

    if not required_booking_columns.issubset(bookings.columns):
        raise ValueError(
            "The bookings dataset does not contain the required columns."
        )

    return users, bookings


# --------------------------------------------------
# STEP 2: BUILD CUSTOMER BEHAVIOUR FEATURES
# --------------------------------------------------

def build_customer_features(users, bookings):
    """
    Create one analytical record per customer.

    Customers without bookings are retained.
    """

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

    # Count total, completed, pending and cancelled bookings.
    booking_summary = (
        bookings.groupby("user_id")
        .agg(
            total_bookings=("user_id", "size"),
            completed_bookings=(
                "status",
                lambda values: (values == "completed").sum(),
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

    # Count the distinct service types used by each customer.
    service_summary = (
        bookings.loc[bookings["service_type"].ne("")]
        .groupby("user_id")["service_type"]
        .nunique()
        .rename("distinct_services")
        .reset_index()
    )

    # Keep every customer, including those without bookings.
    customer_features = (
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
        "pending_bookings",
        "cancelled_bookings",
        "distinct_services",
    ]

    customer_features[numeric_features] = (
        customer_features[numeric_features]
        .fillna(0)
        .astype(int)
    )

    return customer_features


# --------------------------------------------------
# STEP 3: APPLY CLUSTERING ALGORITHMS
# --------------------------------------------------

def perform_clustering(customer_features):
    """
    Apply K-Means and hierarchical clustering.

    Returns customer assignments, cluster summaries,
    and model evaluation metrics.
    """

    df = customer_features.copy()

    features = [
        "total_bookings",
        "completed_bookings",
        "pending_bookings",
        "cancelled_bookings",
        "distinct_services",
    ]

    X = df[features].fillna(0)

    if len(df) < 3:
        raise ValueError(
            "At least three customers are required "
            "for a three-cluster comparison."
        )

    if X.nunique().max() == 1 and X.nunique().sum() == 1:
        raise ValueError(
            "All customer features are identical. "
            "Meaningful clustering is not possible."
        )

    # Standardization prevents larger-valued features from
    # dominating the distance calculations.
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # K-Means clustering.
    kmeans = KMeans(
        n_clusters=N_CLUSTERS,
        random_state=RANDOM_STATE,
        n_init=10,
    )

    df["kmeans_cluster"] = kmeans.fit_predict(X_scaled)

    # Hierarchical agglomerative clustering.
    hierarchical = AgglomerativeClustering(
        n_clusters=N_CLUSTERS,
        linkage="ward",
    )

    df["hierarchical_cluster"] = (
        hierarchical.fit_predict(X_scaled)
    )

    # Evaluate cluster separation when valid.
    metrics = []

    for algorithm, column in [
        ("K-Means", "kmeans_cluster"),
        ("Hierarchical", "hierarchical_cluster"),
    ]:
        labels = df[column]
        number_of_clusters = labels.nunique()

        if 1 < number_of_clusters < len(df):
            score = silhouette_score(
                X_scaled,
                labels,
            )
        else:
            score = float("nan")

        metrics.append({
            "algorithm": algorithm,
            "customers": len(df),
            "clusters": number_of_clusters,
            "silhouette_score": score,
        })

    return df, pd.DataFrame(metrics), X_scaled, features


# --------------------------------------------------
# STEP 4: GENERATE CLUSTER SUMMARIES
# --------------------------------------------------

def generate_cluster_summary(df, cluster_column):
    """Summarize customer behaviour for each cluster."""

    summary = (
        df.groupby(cluster_column)
        .agg(
            customer_count=("user_id", "count"),
            average_bookings=("total_bookings", "mean"),
            average_completed=("completed_bookings", "mean"),
            average_pending=("pending_bookings", "mean"),
            average_cancelled=("cancelled_bookings", "mean"),
            average_distinct_services=("distinct_services", "mean"),
        )
        .round(2)
        .reset_index()
    )

    return summary


# --------------------------------------------------
# STEP 5: CREATE VISUALIZATIONS
# --------------------------------------------------

def save_cluster_plot(df, algorithm_column, output_path):
    """
    Plot customer groups using total bookings and completed bookings.

    This is a two-dimensional view of clusters calculated
    from all five standardized features.
    """

    fig, ax = plt.subplots(figsize=(9, 6))

    scatter = ax.scatter(
        df["total_bookings"],
        df["completed_bookings"],
        c=df[algorithm_column],
        alpha=0.75,
    )

    ax.set_title(
        f"Customer Segmentation - "
        f"{algorithm_column.replace('_', ' ').title()}"
    )

    ax.set_xlabel("Total Bookings")
    ax.set_ylabel("Completed Bookings")

    legend = ax.legend(
        *scatter.legend_elements(),
        title="Cluster",
    )

    ax.add_artist(legend)

    ax.grid(
        True,
        linestyle="--",
        alpha=0.3,
    )

    fig.tight_layout()

    fig.savefig(
        output_path,
        dpi=150,
        bbox_inches="tight",
    )

    plt.close(fig)


# --------------------------------------------------
# STEP 6: RUN THE COMPLETE ANALYSIS
# --------------------------------------------------

def main():
    print("\n" + "=" * 65)
    print("DRIVECARE - CUSTOMER CLUSTERING ANALYSIS")
    print("=" * 65)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    users, bookings = load_data()

    print(f"\nCustomers loaded: {len(users):,}")
    print(f"Bookings loaded: {len(bookings):,}")

    customer_features = build_customer_features(
        users,
        bookings,
    )

    print(
        f"Customer records prepared: "
        f"{len(customer_features):,}"
    )

    print("\nCustomer feature preview:")

    print(
        customer_features[
            [
                "user_id",
                "total_bookings",
                "completed_bookings",
                "pending_bookings",
                "cancelled_bookings",
                "distinct_services",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    (
        clustered_customers,
        metrics,
        X_scaled,
        features,
    ) = perform_clustering(customer_features)

    # Save assignments.
    assignments_path = (
        OUTPUT_DIR / "customer_cluster_assignments.csv"
    )

    clustered_customers.to_csv(
        assignments_path,
        index=False,
        encoding="utf-8",
    )

    # Save separate cluster summaries.
    kmeans_summary = generate_cluster_summary(
        clustered_customers,
        "kmeans_cluster",
    )

    hierarchical_summary = generate_cluster_summary(
        clustered_customers,
        "hierarchical_cluster",
    )

    kmeans_summary.to_csv(
        OUTPUT_DIR / "kmeans_cluster_summary.csv",
        index=False,
        encoding="utf-8",
    )

    hierarchical_summary.to_csv(
        OUTPUT_DIR / "hierarchical_cluster_summary.csv",
        index=False,
        encoding="utf-8",
    )

    # Save evaluation metrics.
    metrics.to_csv(
        OUTPUT_DIR / "clustering_metrics.csv",
        index=False,
        encoding="utf-8",
    )

    # Save visualizations.
    save_cluster_plot(
        clustered_customers,
        "kmeans_cluster",
        OUTPUT_DIR / "kmeans_clusters.png",
    )

    save_cluster_plot(
        clustered_customers,
        "hierarchical_cluster",
        OUTPUT_DIR / "hierarchical_clusters.png",
    )

    print("\n" + "=" * 65)
    print("CLUSTERING EVALUATION")
    print("=" * 65)

    print(
        metrics.round(4).to_string(index=False)
    )

    print("\nK-Means cluster summary:")

    print(
        kmeans_summary.to_string(index=False)
    )

    print("\nHierarchical cluster summary:")

    print(
        hierarchical_summary.to_string(index=False)
    )

    print("\nOutput directory:")
    print(OUTPUT_DIR)

    print("\nGenerated files:")
    for file_path in sorted(OUTPUT_DIR.iterdir()):
        print(f"- {file_path.name}")

    print("\nClustering analysis completed.")
    print("PostgreSQL records were not modified.")
    print("=" * 65)


if __name__ == "__main__":
    main()