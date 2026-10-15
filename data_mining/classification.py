"""
DriveCare Data Mining - Classification

Models:
    1. Decision Tree
    2. Gaussian Naive Bayes
    3. k-Nearest Neighbors

Target:
    Completed vs Not Completed

Important:
    This is a demonstration of historical-status classification,
    not a validated prediction of future booking completion.

Reads analytical CSV files only.
Does not modify PostgreSQL records.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier


PROJECT_ROOT = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    PROJECT_ROOT
    / "data_mining"
    / "output"
    / "cleaned_bookings.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data_mining"
    / "classification_results"
)

RANDOM_STATE = 42
TEST_SIZE = 0.25


def load_data():
    """Load and validate the cleaned booking dataset."""

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            "cleaned_bookings.csv not found. "
            "Run etl_pipeline.py first."
        )

    data = pd.read_csv(INPUT_FILE)

    required_columns = [
        "booking_id",
        "user_id",
        "vehicle_id",
        "service_type",
        "booking_date",
        "status",
        "created_at",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in data.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Required columns missing: {missing_columns}"
        )

    return data


def prepare_features(data):
    """
    Prepare model features and the binary target.

    Direct identifiers, free-text descriptions, and status are
    excluded from model inputs.
    """

    df = data.copy()

    df["status"] = (
        df["status"]
        .astype(str)
        .str.strip()
        .str.casefold()
    )

    # Map the historical booking status to a binary target.
    df["target"] = (
        df["status"] == "completed"
    ).astype(int)

    # Parse dates for feature extraction.
    df["booking_date"] = pd.to_datetime(
        df["booking_date"],
        errors="coerce",
    )

    df["created_at"] = pd.to_datetime(
        df["created_at"],
        errors="coerce",
    )

    df["booking_year"] = df["booking_date"].dt.year
    df["booking_month"] = df["booking_date"].dt.month
    df["booking_day_of_week"] = (
        df["booking_date"].dt.dayofweek
    )

    df["created_year"] = df["created_at"].dt.year
    df["created_month"] = df["created_at"].dt.month

    # Calculate lead time between creation and scheduled date.
    df["booking_lead_days"] = (
        df["booking_date"] - df["created_at"].dt.normalize()
    ).dt.total_seconds() / 86400

    # Retain features available without using the target status.
    feature_columns = [
        "service_type",
        "booking_year",
        "booking_month",
        "booking_day_of_week",
        "created_year",
        "created_month",
        "booking_lead_days",
    ]

    X = df[feature_columns].copy()
    y = df["target"].copy()

    # Convert infinite values to missing values for safe imputation.
    X = X.replace([float("inf"), float("-inf")], pd.NA)

    return X, y


def build_preprocessor():
    """Build preprocessing pipelines for categorical and numeric fields."""

    categorical_features = ["service_type"]

    numeric_features = [
        "booking_year",
        "booking_month",
        "booking_day_of_week",
        "created_year",
        "created_month",
        "booking_lead_days",
    ]

    categorical_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(strategy="most_frequent"),
            ),
            (
                "onehot",
                OneHotEncoder(handle_unknown="ignore"),
            ),
        ]
    )

    numeric_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(strategy="median"),
            ),
            (
                "scaler",
                StandardScaler(),
            ),
        ]
    )

    return ColumnTransformer(
        transformers=[
            (
                "categorical",
                categorical_pipeline,
                categorical_features,
            ),
            (
                "numeric",
                numeric_pipeline,
                numeric_features,
            ),
        ]
    )


def evaluate_model(name, model, X_train, X_test, y_train, y_test):
    """Fit a model and calculate classification metrics."""

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    metrics = {
        "model": name,
        "accuracy": accuracy_score(y_test, predictions),
        "precision": precision_score(
            y_test,
            predictions,
            zero_division=0,
        ),
        "recall": recall_score(
            y_test,
            predictions,
            zero_division=0,
        ),
        "f1_score": f1_score(
            y_test,
            predictions,
            zero_division=0,
        ),
    }

    matrix = confusion_matrix(
        y_test,
        predictions,
        labels=[0, 1],
    )

    print(f"\n{'-' * 60}")
    print(name)
    print("-" * 60)

    print(f"Accuracy : {metrics['accuracy']:.4f}")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"Recall   : {metrics['recall']:.4f}")
    print(f"F1-score : {metrics['f1_score']:.4f}")

    print("\nClassification report:")
    print(
        classification_report(
            y_test,
            predictions,
            labels=[0, 1],
            target_names=["Not Completed", "Completed"],
            zero_division=0,
        )
    )

    print("Confusion matrix:")
    print(matrix)

    return metrics, matrix


def main():
    """Train and compare the three classification models."""

    print("\n" + "=" * 65)
    print("DRIVECARE - CLASSIFICATION AND MODEL EVALUATION")
    print("=" * 65)

    data = load_data()

    print(f"\nBookings loaded: {len(data):,}")

    print("\nOriginal status distribution:")
    print(data["status"].value_counts().to_string())

    X, y = prepare_features(data)

    print("\nBinary target distribution:")
    print(
        y.map({
            0: "Not Completed",
            1: "Completed",
        }).value_counts().to_string()
    )

    # Verify that stratification is possible.
    if y.nunique() < 2 or y.value_counts().min() < 2:
        raise ValueError(
            "Insufficient examples in one of the target classes."
        )

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    print(f"\nTraining records: {len(X_train):,}")
    print(f"Testing records: {len(X_test):,}")

    preprocessor = build_preprocessor()

    models = {
        "Decision Tree": DecisionTreeClassifier(
            max_depth=5,
            min_samples_leaf=5,
            random_state=RANDOM_STATE,
            class_weight="balanced",
        ),
        "Gaussian Naive Bayes": GaussianNB(),
        "K-Nearest Neighbors": KNeighborsClassifier(
            n_neighbors=5,
            weights="distance",
        ),
    }

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    results = []

    for name, classifier in models.items():
        # Each model gets its own independent preprocessing pipeline.
        pipeline = Pipeline(
            steps=[
                ("preprocessor", build_preprocessor()),
                ("classifier", classifier),
            ]
        )

        metrics, matrix = evaluate_model(
            name,
            pipeline,
            X_train,
            X_test,
            y_train,
            y_test,
        )

        results.append(metrics)

        display = ConfusionMatrixDisplay(
            confusion_matrix=matrix,
            display_labels=["Not Completed", "Completed"],
        )

        fig, ax = plt.subplots(figsize=(6, 5))

        display.plot(
            ax=ax,
            values_format="d",
            colorbar=False,
        )

        ax.set_title(f"{name} - Confusion Matrix")

        fig.tight_layout()

        filename = (
            name.lower()
            .replace(" ", "_")
            .replace("-", "_")
            + "_confusion_matrix.png"
        )

        fig.savefig(
            OUTPUT_DIR / filename,
            dpi=150,
            bbox_inches="tight",
        )

        plt.close(fig)

        print(
            f"Confusion matrix image saved: "
            f"{OUTPUT_DIR / filename}"
        )

    # Compare models using their evaluation metrics.
    results_df = pd.DataFrame(results)

    results_df = results_df.sort_values(
        "f1_score",
        ascending=False,
    )

    results_path = OUTPUT_DIR / "model_comparison.csv"

    results_df.to_csv(
        results_path,
        index=False,
        encoding="utf-8",
    )

    print("\n" + "=" * 65)
    print("MODEL COMPARISON")
    print("=" * 65)

    print(results_df.round(4).to_string(index=False))

    print(f"\nSaved model comparison: {results_path}")

    print("\nClassification experiment completed.")
    print(
        "These metrics evaluate historical-status classification "
        "and do not establish future booking-completion accuracy."
    )
    print("No PostgreSQL records were modified.")
    print("=" * 65)


if __name__ == "__main__":
    main()