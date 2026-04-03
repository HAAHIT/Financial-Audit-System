"""
Anomaly detection: expense spikes, salary spikes, Z-score outliers,
sudden increase/decrease detection.
"""

import pandas as pd
import numpy as np
from config import SPIKE_THRESHOLD_PCT, SALARY_SPIKE_PCT, ZSCORE_THRESHOLD


def detect_expense_spikes(conn, threshold_pct=None):
    """
    Find groups whose month-over-month spending spiked above threshold.
    Returns DataFrame with columns:
      group_name, month, total_spent, prev_month_spent, spike_pct
    """
    threshold = threshold_pct if threshold_pct is not None else SPIKE_THRESHOLD_PCT
    query = """
        SELECT group_name,
               strftime('%Y-%m', docdate) AS month,
               SUM(debit_amount) AS total_spent
        FROM bank_ledger
        WHERE debit_amount > 0
          AND group_name NOT LIKE '%SUNDRY%'
          AND group_name NOT LIKE '%INTER BRANCH%'
        GROUP BY group_name, month
        ORDER BY group_name, month
    """
    df = pd.read_sql(query, conn)
    if df.empty:
        return df

    df["prev_month_spent"] = df.groupby("group_name")["total_spent"].shift(1)
    df["spike_pct"] = (
        (df["total_spent"] - df["prev_month_spent"]) / df["prev_month_spent"]
    ) * 100

    spikes = df[df["spike_pct"] > threshold].dropna(subset=["spike_pct"])
    return spikes.sort_values("spike_pct", ascending=False).reset_index(drop=True)


def detect_salary_spikes(conn, threshold_pct=None):
    """
    Detect sudden increases in salary-related payments MoM.
    """
    threshold = threshold_pct if threshold_pct is not None else SALARY_SPIKE_PCT
    query = """
        SELECT strftime('%Y-%m', docdate) AS month,
               SUM(debit_amount) AS total_salary
        FROM bank_ledger
        WHERE debit_amount > 0
          AND (group_name LIKE '%SALARY%'
               OR group_name LIKE '%WAGES%'
               OR group_name LIKE '%PAYROLL%')
        GROUP BY month
        ORDER BY month
    """
    df = pd.read_sql(query, conn)
    if df.empty:
        return df

    df["prev_month"] = df["total_salary"].shift(1)
    df["spike_pct"] = ((df["total_salary"] - df["prev_month"]) / df["prev_month"]) * 100

    spikes = df[df["spike_pct"] > threshold].dropna(subset=["spike_pct"])
    return spikes.sort_values("spike_pct", ascending=False).reset_index(drop=True)


def compute_zscore_outliers(series, threshold=None):
    """
    Return a boolean mask where True = outlier (|z| > threshold).
    """
    thresh = threshold if threshold is not None else ZSCORE_THRESHOLD
    if series.empty or series.std() == 0:
        return pd.Series([False] * len(series), index=series.index)

    z = (series - series.mean()) / series.std()
    return z.abs() > thresh


def detect_sudden_changes(conn, direction="both", threshold_pct=None):
    """
    Flag any sudden increase or decrease in any expense group MoM.
    direction: 'increase', 'decrease', or 'both'
    """
    threshold = threshold_pct if threshold_pct is not None else SPIKE_THRESHOLD_PCT
    query = """
        SELECT group_name,
               strftime('%Y-%m', docdate) AS month,
               SUM(debit_amount) AS total_spent
        FROM bank_ledger
        WHERE debit_amount > 0
        GROUP BY group_name, month
        ORDER BY group_name, month
    """
    df = pd.read_sql(query, conn)
    if df.empty:
        return df

    df["prev_month_spent"] = df.groupby("group_name")["total_spent"].shift(1)
    df["change_pct"] = (
        (df["total_spent"] - df["prev_month_spent"]) / df["prev_month_spent"]
    ) * 100

    df = df.dropna(subset=["change_pct"])

    if direction == "increase":
        result = df[df["change_pct"] > threshold]
    elif direction == "decrease":
        result = df[df["change_pct"] < -threshold]
    else:
        result = df[df["change_pct"].abs() > threshold]

    return result.sort_values("change_pct", key=abs, ascending=False).reset_index(drop=True)
