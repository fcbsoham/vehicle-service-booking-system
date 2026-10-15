"""
DriveCare Data Mining - Association Rule Mining

Algorithm:
    Apriori

Metrics:
    Support, Confidence, Lift

Transaction definition:
    One customer and the distinct non-cancelled services
    they have booked.

This script reads CSV files only and does not modify PostgreSQL.
"""

from pathlib import Path

import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder


PROJECT_ROOT = Path(__file__).resolve().parent.parent

INPUT_DIR = PROJECT_ROOT / "data_mining" / "output"
RESULTS_DIR = PROJECT_ROOT / "data_mining" / "association_results"

MIN_SUPPORT = 0.03
MIN_CONFIDENCE = 0.30
MIN_LIFT = 1.0


def load_booking_data():
    """Load cleaned users and bookings."""

    users_path = INPUT_DIR / "cleaned_users.csv"
    bookings_path = INPUT_DIR / "cleaned_bookings.csv"

    if not users_path.exists():
        raise FileNotFoundError(
            "cleaned_users.csv not found. "
            "Run etl_pipeline.py first."
        )

    if not bookings_path.exists():
        raise FileNotFoundError(
            "cleaned_bookings.csv not found. "
            "Run etl_pipeline.py first."
        )

    users = pd.read_csv(users_path)
    bookings = pd.read_csv(bookings_path)

    return users, bookings


def prepare_transactions(users, bookings):
    """
    Create one service transaction per customer.

    Customers without eligible bookings are excluded from the
    transaction matrix, but are counted in the diagnostic output.
    """

    # Retain customer records with an ID.
    users = users.dropna(subset=["user_id"]).copy()

    # Normalize status and service labels for consistent processing.
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

    # Exclude cancelled bookings from the primary analysis.
    eligible = bookings[
        (bookings["status"] != "cancelled")
        & (bookings["service_type"] != "")
    ].copy()

    # Deduplicate customer-service pairs.
    # Repeated bookings for the same service do not increase
    # the number of items in a customer's transaction.
    eligible = eligible.drop_duplicates(
        subset=["user_id", "service_type"]
    )

    transactions = (
        eligible.groupby("user_id")["service_type"]
        .apply(list)
        .tolist()
    )

    total_customers = users["user_id"].nunique()
    customers_with_transactions = len(transactions)

    diagnostics = {
        "total_customers": total_customers,
        "customers_with_transactions": customers_with_transactions,
        "customers_without_eligible_bookings": (
            total_customers - customers_with_transactions
        ),
        "eligible_bookings_before_deduplication": len(
            bookings[
                (bookings["status"] != "cancelled")
                & (bookings["service_type"] != "")
            ]
        ),
        "distinct_customer_service_pairs": len(eligible),
        "distinct_services": eligible["service_type"].nunique(),
    }

    return transactions, diagnostics


def run_apriori(transactions):
    """Generate frequent itemsets and association rules."""

    if not transactions:
        return pd.DataFrame(), pd.DataFrame()

    # A transaction must contain at least two distinct services
    # to contribute to multi-service association rules.
    transactions_with_multiple_services = [
        transaction
        for transaction in transactions
        if len(transaction) >= 2
    ]

    if not transactions_with_multiple_services:
        print(
            "\nNo customer has multiple distinct eligible services. "
            "Multi-service association rules cannot be generated."
        )

        return pd.DataFrame(), pd.DataFrame()

    # Encode transactions as a one-hot Boolean matrix.
    encoder = TransactionEncoder()

    encoded_array = encoder.fit(
        transactions
    ).transform(transactions)

    basket = pd.DataFrame(
        encoded_array,
        columns=encoder.columns_,
    )

    # Generate frequent itemsets.
    frequent_itemsets = apriori(
        basket,
        min_support=MIN_SUPPORT,
        use_colnames=True,
    )

    # Single-item sets are useful for support analysis but cannot
    # produce a meaningful multi-item association rule.
    if frequent_itemsets.empty:
        return frequent_itemsets, pd.DataFrame()

    multi_itemsets = frequent_itemsets[
        frequent_itemsets["itemsets"].apply(
            lambda itemset: len(itemset) >= 2
        )
    ]

    if multi_itemsets.empty:
        return frequent_itemsets, pd.DataFrame()

    # Build rules from frequent itemsets.
    rules = association_rules(
        frequent_itemsets,
        metric="confidence",
        min_threshold=MIN_CONFIDENCE,
    )

    if not rules.empty:
        rules = rules[rules["lift"] >= MIN_LIFT].copy()

        rules["antecedents"] = rules["antecedents"].apply(
            lambda items: ", ".join(sorted(items))
        )

        rules["consequents"] = rules["consequents"].apply(
            lambda items: ", ".join(sorted(items))
        )

        rules = rules.sort_values(
            ["lift", "confidence", "support"],
            ascending=False,
        )

    return frequent_itemsets, rules


def main():
    """Run the complete association rule mining workflow."""

    print("\n" + "=" * 65)
    print("DRIVECARE - ASSOCIATION RULE MINING")
    print("=" * 65)

    print("\nLoading cleaned data...")

    users, bookings = load_booking_data()

    print(f"Users loaded: {len(users):,}")
    print(f"Bookings loaded: {len(bookings):,}")

    print("\nPreparing customer-level transactions...")

    transactions, diagnostics = prepare_transactions(
        users,
        bookings,
    )

    for label, value in diagnostics.items():
        print(f"{label.replace('_', ' ').title()}: {value:,}")

    if not transactions:
        print(
            "\nNo eligible customer transactions were found. "
            "Association analysis cannot continue."
        )
        return

    print("\nApriori configuration:")
    print(f"Minimum support: {MIN_SUPPORT:.2f}")
    print(f"Minimum confidence: {MIN_CONFIDENCE:.2f}")
    print(f"Minimum lift: {MIN_LIFT:.2f}")

    frequent_itemsets, rules = run_apriori(transactions)

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Save frequent itemsets in a readable format.
    if not frequent_itemsets.empty:
        itemsets_to_save = frequent_itemsets.copy()

        itemsets_to_save["itemsets"] = (
            itemsets_to_save["itemsets"].apply(
                lambda items: ", ".join(sorted(items))
            )
        )

        itemsets_to_save = itemsets_to_save.sort_values(
            "support",
            ascending=False,
        )

        itemsets_path = (
            RESULTS_DIR / "frequent_itemsets.csv"
        )

        itemsets_to_save.to_csv(
            itemsets_path,
            index=False,
            encoding="utf-8",
        )

        print(f"\nSaved: {itemsets_path}")
        print(
            f"Frequent itemsets found: "
            f"{len(itemsets_to_save):,}"
        )

        print("\nTop frequent itemsets:")
        print(itemsets_to_save.head(15).to_string(index=False))

    else:
        print("\nNo frequent itemsets met the support threshold.")

    if not rules.empty:
        rules_path = RESULTS_DIR / "association_rules.csv"

        rules.to_csv(
            rules_path,
            index=False,
            encoding="utf-8",
        )

        print(f"\nSaved: {rules_path}")
        print(f"Association rules found: {len(rules):,}")

        display_columns = [
            "antecedents",
            "consequents",
            "support",
            "confidence",
            "lift",
        ]

        print("\nTop association rules:")
        print(
            rules[display_columns]
            .head(15)
            .round(4)
            .to_string(index=False)
        )

    else:
        print(
            "\nNo association rules met the configured "
            "support, confidence, and lift thresholds."
        )

        print(
            "This is a valid result. We can examine the transaction "
            "distribution and thresholds before changing parameters."
        )

    print("\nAssociation rule mining completed.")
    print(f"Results directory: {RESULTS_DIR}")
    print("No PostgreSQL records were modified.")
    print("=" * 65)


if __name__ == "__main__":
    main()