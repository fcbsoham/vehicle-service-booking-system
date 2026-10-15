"""Admin-only Data Mining Analytics dashboard."""

from pathlib import Path

import pandas as pd

from flask import Blueprint, abort, render_template, send_from_directory
from flask_login import current_user, login_required


data_mining_bp = Blueprint(
    "data_mining",
    __name__,
    url_prefix="/admin/data-mining",
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_MINING_DIR = PROJECT_ROOT / "data_mining"


def read_csv_safely(path, **kwargs):
    """Read an analytical CSV if it exists; otherwise return an empty DataFrame."""

    if not path.exists():
        return pd.DataFrame()

    try:
        return pd.read_csv(path, **kwargs)
    except (OSError, pd.errors.ParserError, UnicodeDecodeError):
        return pd.DataFrame()


def get_records(df, limit=10):
    """Convert a DataFrame into template-friendly records."""

    if df.empty:
        return []

    return df.head(limit).where(pd.notna(df), None).to_dict(
        orient="records"
    )


@data_mining_bp.route("/")
@login_required
def analytics_dashboard():
    """Display existing Data Mining results to administrators only."""

    if current_user.role != "admin":
        abort(403)

    # Operational counts are read-only database queries.
    from extensions import db
    from models.user import User
    from models.vehicle import Vehicle
    from models.booking import Booking

    total_users = User.query.count()
    total_vehicles = Vehicle.query.count()
    total_bookings = Booking.query.count()

    status_counts = (
        db.session.query(
            Booking.status,
            db.func.count(Booking.booking_id),
        )
        .group_by(Booking.status)
        .all()
    )

    # OLAP results
    olap_dir = DATA_MINING_DIR / "olap_results"

    monthly = read_csv_safely(
        olap_dir / "rollup_monthly_bookings.csv"
    )

    pivot = read_csv_safely(
        olap_dir / "pivot_service_status.csv"
    )

    # Association rule mining results
    association_dir = (
        DATA_MINING_DIR / "association_results"
    )

    association_rules = read_csv_safely(
        association_dir / "association_rules.csv"
    )

    if not association_rules.empty:
        sort_columns = [
            column
            for column in ["lift", "confidence", "support"]
            if column in association_rules.columns
        ]

        if sort_columns:
            association_rules = association_rules.sort_values(
                sort_columns,
                ascending=[False] * len(sort_columns),
            )

    # Classification results
    classification_dir = (
        DATA_MINING_DIR / "classification_results"
    )

    model_comparison = read_csv_safely(
        classification_dir / "model_comparison.csv"
    )

    # Clustering results
    clustering_dir = (
        DATA_MINING_DIR / "clustering_results"
    )

    kmeans_summary = read_csv_safely(
        clustering_dir / "kmeans_cluster_summary.csv"
    )

    hierarchical_summary = read_csv_safely(
        clustering_dir / "hierarchical_cluster_summary.csv"
    )

    clustering_metrics = read_csv_safely(
        clustering_dir / "clustering_metrics.csv"
    )

    # Outlier detection results
    outlier_dir = DATA_MINING_DIR / "outlier_results"

    outliers = read_csv_safely(
        outlier_dir / "flagged_customers.csv"
    )

    # Images are served from the project's static directory.
    # Copying generated plots there is a separate step.
    classification_images = {
        "decision_tree": (
            "decision_tree_confusion_matrix.png"
        ),
        "naive_bayes": (
            "gaussian_naive_bayes_confusion_matrix.png"
        ),
        "knn": (
            "k_nearest_neighbors_confusion_matrix.png"
        ),
    }

    return render_template(
        "data_mining_dashboard.html",
        total_users=total_users,
        total_vehicles=total_vehicles,
        total_bookings=total_bookings,
        status_counts=status_counts,
        monthly_records=get_records(monthly, limit=24),
        pivot_columns=pivot.columns.tolist() if not pivot.empty else [],
        pivot_records=get_records(pivot, limit=50),
        association_columns=(
            association_rules.columns.tolist()
            if not association_rules.empty
            else []
        ),
        association_records=get_records(
            association_rules,
            limit=10,
        ),
        model_columns=(
            model_comparison.columns.tolist()
            if not model_comparison.empty
            else []
        ),
        model_records=get_records(model_comparison, limit=10),
        kmeans_columns=(
            kmeans_summary.columns.tolist()
            if not kmeans_summary.empty
            else []
        ),
        kmeans_records=get_records(
            kmeans_summary,
            limit=10,
        ),
        hierarchical_columns=(
            hierarchical_summary.columns.tolist()
            if not hierarchical_summary.empty
            else []
        ),
        hierarchical_records=get_records(
            hierarchical_summary,
            limit=10,
        ),
        clustering_columns=(
            clustering_metrics.columns.tolist()
            if not clustering_metrics.empty
            else []
        ),
        clustering_records=get_records(
            clustering_metrics,
            limit=10,
        ),
        outlier_columns=(
            outliers.columns.tolist()
            if not outliers.empty
            else []
        ),
        outlier_records=get_records(outliers, limit=20),
        classification_images=classification_images,
    )

# Only serve explicitly approved analytics images.
ANALYTICS_IMAGES = {
    "decision_tree_confusion_matrix.png": (
        DATA_MINING_DIR / "classification_results"
    ),
    "gaussian_naive_bayes_confusion_matrix.png": (
        DATA_MINING_DIR / "classification_results"
    ),
    "k_nearest_neighbors_confusion_matrix.png": (
        DATA_MINING_DIR / "classification_results"
    ),
    "kmeans_clusters.png": (
        DATA_MINING_DIR / "clustering_results"
    ),
    "hierarchical_clusters.png": (
        DATA_MINING_DIR / "clustering_results"
    ),
    "customer_outliers.png": (
        DATA_MINING_DIR / "outlier_results"
    ),
}


@data_mining_bp.route("/images/<path:filename>")
@login_required
def analytics_image(filename):
    if current_user.role != "admin":
        abort(403)

    image_directory = ANALYTICS_IMAGES.get(filename)

    if image_directory is None:
        abort(404)

    if not (image_directory / filename).is_file():
        abort(404)

    return send_from_directory(
        str(image_directory),
        filename,
        mimetype="image/png",
        max_age=300,
    )