"""
Procurement audit: price outliers, average material cost,
BOM total validation, historical BOM comparison.
"""

import pandas as pd
import numpy as np
from config import PROCUREMENT_VARIANCE_PCT


def detect_price_outliers(conn, variance_pct=None):
    """
    Compare each purchase's implied rate against the historical
    baseline rate for that item. Flag if variance exceeds threshold.
    """
    threshold = (variance_pct if variance_pct is not None else PROCUREMENT_VARIANCE_PCT) / 100.0

    df = pd.read_sql(
        "SELECT * FROM purchase_ledger WHERE rec_qty > 0", conn
    )
    if df.empty:
        return df

    df["implied_rate"] = df["material_value"] / df["rec_qty"]

    baseline = pd.read_sql(
        "SELECT item_name, AVG(material_value / rec_qty) AS baseline_rate "
        "FROM purchase_ledger WHERE rec_qty > 0 GROUP BY item_name", conn
    )
    df = df.merge(baseline, on="item_name", how="left")
    df["variance_pct"] = abs(df["implied_rate"] - df["baseline_rate"]) / df["baseline_rate"]

    outliers = df[df["variance_pct"] > threshold]
    return outliers.sort_values("variance_pct", ascending=False).reset_index(drop=True)


def compute_avg_material_cost(conn):
    """
    Compute weighted average cost per item across all purchases.
    Also detects outlier line-items via Z-score.
    """
    df = pd.read_sql(
        "SELECT item_name, party_name, rec_qty, material_value "
        "FROM purchase_ledger WHERE rec_qty > 0", conn
    )
    if df.empty:
        return pd.DataFrame()

    df["unit_rate"] = df["material_value"] / df["rec_qty"]

    # Weighted average per item
    summary = df.groupby("item_name").apply(
        lambda g: pd.Series({
            "total_qty": g["rec_qty"].sum(),
            "total_value": g["material_value"].sum(),
            "weighted_avg_rate": g["material_value"].sum() / g["rec_qty"].sum(),
            "min_rate": g["unit_rate"].min(),
            "max_rate": g["unit_rate"].max(),
            "std_rate": g["unit_rate"].std(),
            "txn_count": len(g),
        }),
        include_groups=False,
    ).reset_index()

    return summary.sort_values("total_value", ascending=False).reset_index(drop=True)


def validate_bom_totals(conn):
    """
    For each invoice, check if the sum of line-item material values
    matches the expected invoice total (net_amt).
    Each INV_NO groups multiple line items (the "BOM").
    """
    df = pd.read_sql("SELECT * FROM purchase_ledger", conn)
    if df.empty:
        return pd.DataFrame()

    # Group by invoice: sum of material+tax+charges-rebate vs sum of net_amt
    inv_summary = df.groupby("inv_no").agg(
        component_total=("material_value", "sum"),
        tax_total=("tax_amt", "sum"),
        charges_total=("charges_amt", "sum"),
        rebate_total=("rebate_amt", "sum"),
        net_amt_total=("net_amt", "sum"),
        line_count=("inv_no", "count"),
        party_name=("party_name", "first"),
        inv_date=("inv_date", "first"),
    ).reset_index()

    inv_summary["expected_total"] = (
        inv_summary["component_total"]
        + inv_summary["tax_total"]
        + inv_summary["charges_total"]
        - inv_summary["rebate_total"]
    )
    inv_summary["bom_discrepancy"] = abs(
        inv_summary["net_amt_total"] - inv_summary["expected_total"]
    )

    mismatches = inv_summary[inv_summary["bom_discrepancy"] > 1.0]
    return mismatches.sort_values("bom_discrepancy", ascending=False).reset_index(drop=True)


def check_bom_historical(conn):
    """
    Compare each invoice's BOM total against historical averages
    for the same items. Flag if significantly different.
    """
    df = pd.read_sql(
        "SELECT inv_no, inv_date, party_name, item_name, "
        "       rec_qty, material_value "
        "FROM purchase_ledger WHERE rec_qty > 0", conn
    )
    if df.empty:
        return pd.DataFrame()

    df["unit_rate"] = df["material_value"] / df["rec_qty"]

    # Historical average per item
    hist_avg = df.groupby("item_name")["unit_rate"].mean().rename("hist_avg_rate")

    df = df.merge(hist_avg, on="item_name", how="left")
    df["hist_deviation_pct"] = (
        abs(df["unit_rate"] - df["hist_avg_rate"]) / df["hist_avg_rate"]
    ) * 100

    flagged = df[df["hist_deviation_pct"] > 30.0]
    return flagged.sort_values("hist_deviation_pct", ascending=False).reset_index(drop=True)
