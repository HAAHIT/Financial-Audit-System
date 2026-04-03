"""
Sales analysis: discount outliers, consistently-low-price buyer detection.
"""

import pandas as pd
from config import DISCOUNT_ALARM_PCT, LOW_PRICE_CONSISTENCY_PCT


def detect_discount_outliers(conn, threshold_pct=None):
    """
    Find buyers whose average rate per item is significantly below
    the global average, suggesting unusual discounts.
    """
    threshold = threshold_pct if threshold_pct is not None else DISCOUNT_ALARM_PCT

    global_rates = pd.read_sql(
        "SELECT item_name, AVG(net_rate) AS global_avg_rate "
        "FROM sales_ledger WHERE net_rate > 0 GROUP BY item_name", conn
    )
    party_rates = pd.read_sql(
        "SELECT party_name, item_name, "
        "       AVG(net_rate) AS party_avg_rate, "
        "       SUM(billing_quantity) AS total_vol, "
        "       COUNT(*) AS txn_count "
        "FROM sales_ledger WHERE net_rate > 0 GROUP BY party_name, item_name", conn
    )
    if global_rates.empty or party_rates.empty:
        return pd.DataFrame()

    merged = pd.merge(party_rates, global_rates, on="item_name")
    merged["discount_pct"] = (
        (merged["global_avg_rate"] - merged["party_avg_rate"])
        / merged["global_avg_rate"]
    ) * 100

    flagged = merged[merged["discount_pct"] > threshold]
    return flagged.sort_values("discount_pct", ascending=False).reset_index(drop=True)


def detect_always_low_price_party(conn, threshold_pct=None):
    """
    Flag parties that have ALWAYS bought below the global average
    across ALL their transactions — not just occasionally.
    """
    threshold = threshold_pct if threshold_pct is not None else LOW_PRICE_CONSISTENCY_PCT

    global_rates = pd.read_sql(
        "SELECT item_name, AVG(net_rate) AS global_avg_rate "
        "FROM sales_ledger WHERE net_rate > 0 GROUP BY item_name", conn
    )
    detail = pd.read_sql(
        "SELECT party_name, item_name, net_rate "
        "FROM sales_ledger WHERE net_rate > 0", conn
    )
    if global_rates.empty or detail.empty:
        return pd.DataFrame()

    merged = pd.merge(detail, global_rates, on="item_name")
    merged["below_avg"] = merged["net_rate"] < (
        merged["global_avg_rate"] * (1 - threshold / 100)
    )

    party_summary = merged.groupby("party_name").agg(
        total_txns=("below_avg", "count"),
        below_avg_txns=("below_avg", "sum"),
    ).reset_index()

    party_summary["below_avg_ratio"] = (
        party_summary["below_avg_txns"] / party_summary["total_txns"]
    )

    # Flag if >80% of transactions are below avg AND they have ≥3 transactions
    consistently_low = party_summary[
        (party_summary["below_avg_ratio"] > 0.80)
        & (party_summary["total_txns"] >= 3)
    ]
    return consistently_low.sort_values("below_avg_ratio", ascending=False).reset_index(drop=True)
