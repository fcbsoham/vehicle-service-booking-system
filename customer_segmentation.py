import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from app import app
from extensions import db
from models.user import User
from models.booking import Booking


def get_customer_data():
    """Retrieve customer booking behavior from PostgreSQL."""

    with app.app_context():
        users = User.query.all()
        bookings = Booking.query.all()

        # Create one record for every customer, including those with no bookings.
        customer_records = []

        for user in users:
            user_bookings = [
                booking for booking in bookings
                if booking.user_id == user.user_id
            ]

            customer_records.append({
                "user_id": user.user_id,
                "customer_name": user.full_name,
                "total_bookings": len(user_bookings),
                "completed_bookings": sum(
                    booking.status == "Completed"
                    for booking in user_bookings
                ),
                "pending_bookings": sum(
                    booking.status == "Pending"
                    for booking in user_bookings
                ),
                "distinct_services": len({
                    booking.service_type
                    for booking in user_bookings
                }),
            })

        return pd.DataFrame(customer_records)


def perform_customer_segmentation(n_clusters=3):
    """Apply K-Means clustering to customer booking behavior."""

    df = get_customer_data()

    if df.empty:
        raise ValueError("No customer records found in the database.")

    features = [
        "total_bookings",
        "completed_bookings",
        "pending_bookings",
        "distinct_services",
    ]

    X = df[features].fillna(0)

    # Scale features so that differences in their numerical ranges
    # do not dominate the clustering algorithm.
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # A single cluster is sufficient if there is only one customer.
    actual_clusters = min(n_clusters, len(df))

    model = KMeans(
        n_clusters=actual_clusters,
        random_state=42,
        n_init=10,
    )

    df["cluster"] = model.fit_predict(X_scaled)

    # Generate a summary of the customer groups.
    summary = (
        df.groupby("cluster")
        .agg(
            customer_count=("user_id", "count"),
            average_bookings=("total_bookings", "mean"),
            average_completed=("completed_bookings", "mean"),
            average_pending=("pending_bookings", "mean"),
            average_distinct_services=("distinct_services", "mean"),
        )
        .round(2)
        .reset_index()
    )

    return df, summary


if __name__ == "__main__":
    customer_df, cluster_summary = perform_customer_segmentation()

    print("\n========== CUSTOMER SEGMENTATION ==========")
    print(f"Customers analyzed: {len(customer_df)}")
    print(f"Clusters created: {customer_df['cluster'].nunique()}")

    print("\n--- Customer Assignments ---")
    print(customer_df.to_string(index=False))

    print("\n--- Cluster Summary ---")
    print(cluster_summary.to_string(index=False))
