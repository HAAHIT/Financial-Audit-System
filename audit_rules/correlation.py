"""
Time-series correlation engine: build monthly metrics from all tables,
compute pairwise Pearson correlations.
"""

import pandas as pd
import numpy as np
from scipy import stats
from config import CORRELATION_MIN_MONTHS


def build_time_series(conn):
    """
    Aggregate monthly metrics from bank, purchase, and sales tables.
    Returns DataFrame: month, metric, value
    """
    frames = []

    # Bank: debit by group
    mo_bank = pd.read_sql(
        "SELECT group_name, strftime('%Y-%m', docdate) AS month, "
        "       SUM(debit_amount) AS val "
        "FROM bank_ledger WHERE debit_amount > 0 "
        "GROUP BY group_name, month", conn
    )
    if not mo_bank.empty:
        mo_bank["metric"] = "Bank Debit: " + mo_bank["group_name"]
        frames.append(mo_bank[["month", "metric", "val"]])

    # Purchase: avg unit rate by item
    mo_purch = pd.read_sql(
        "SELECT item_name, strftime('%Y-%m', inv_date) AS month, "
        "       AVG(material_value / rec_qty) AS val "
        "FROM purchase_ledger WHERE rec_qty > 0 "
        "GROUP BY item_name, month", conn
    )
    if not mo_purch.empty:
        mo_purch["metric"] = "Purchase Rate: " + mo_purch["item_name"]
        frames.append(mo_purch[["month", "metric", "val"]])

    # Sales: volume by item
    mo_sales = pd.read_sql(
        "SELECT item_name, strftime('%Y-%m', docdate) AS month, "
        "       SUM(billing_quantity) AS val "
        "FROM sales_ledger "
        "GROUP BY item_name, month", conn
    )
    if not mo_sales.empty:
        mo_sales["metric"] = "Sales Vol: " + mo_sales["item_name"]
        frames.append(mo_sales[["month", "metric", "val"]])

    if not frames:
        return pd.DataFrame(columns=["month", "metric", "val"])

    return pd.concat(frames, ignore_index=True)


def correlate(series_a, series_b):
    """
    Compute Pearson correlation and p-value between two aligned Series.
    Returns (correlation, p_value) or (None, None) if insufficient data.
    """
    combined = pd.concat([series_a, series_b], axis=1).dropna()
    if len(combined) < 2:
        return None, None

    r, p = stats.pearsonr(combined.iloc[:, 0], combined.iloc[:, 1])
    return round(r, 4), round(p, 4)


def correlate_two_metrics(conn, metric_a, metric_b, min_months=None):
    """
    Given two metric names (from build_time_series), compute their correlation.
    """
    min_m = min_months if min_months is not None else CORRELATION_MIN_MONTHS
    all_ts = build_time_series(conn)
    if all_ts.empty:
        return None, None, pd.DataFrame()

    df_a = all_ts[all_ts["metric"] == metric_a][["month", "val"]].rename(
        columns={"val": metric_a}
    )
    df_b = all_ts[all_ts["metric"] == metric_b][["month", "val"]].rename(
        columns={"val": metric_b}
    )
    merged = pd.merge(df_a, df_b, on="month").dropna()

    if len(merged) < min_m:
        return None, None, merged

    r, p = correlate(merged[metric_a], merged[metric_b])
    return r, p, merged


def find_all_correlations(conn, min_months=None):
    """
    Build a correlation matrix of all available monthly metrics.
    Returns a DataFrame of pairwise correlations.
    """
    min_m = min_months if min_months is not None else CORRELATION_MIN_MONTHS
    all_ts = build_time_series(conn)
    if all_ts.empty:
        return pd.DataFrame()

    # Pivot to wide format: months as rows, metrics as columns
    pivot = all_ts.pivot_table(index="month", columns="metric", values="val")

    # Only keep metrics with enough data points
    valid_cols = [c for c in pivot.columns if pivot[c].dropna().shape[0] >= min_m]
    if len(valid_cols) < 2:
        return pd.DataFrame()

    corr_matrix = pivot[valid_cols].corr()
    return corr_matrix
