"""
Cash flow analysis: daily profitability, net cash flow, percentile
calculations, branch summaries, category summaries.
"""

import pandas as pd
import numpy as np


def compute_daily_profitability(conn, daily_tax=0, daily_depreciation=0):
    """
    Compute daily net cash flow and profitability (after tax & depreciation).
    Returns DataFrame: docdate, credit, debit, net_cash_flow, daily_profitability
    """
    df = pd.read_sql(
        "SELECT docdate, "
        "       SUM(credit_amount) AS credit, "
        "       SUM(debit_amount) AS debit "
        "FROM bank_ledger "
        "GROUP BY docdate ORDER BY docdate", conn
    )
    if df.empty:
        return df

    df["net_cash_flow"] = df["credit"] - df["debit"]
    df["daily_profitability"] = df["net_cash_flow"] - daily_tax - daily_depreciation
    return df


def compute_net_cashflow(conn, start_date=None, end_date=None):
    """
    Compute cumulative net cash flow over a date range.
    """
    query = (
        "SELECT docdate, "
        "       SUM(credit_amount) AS credit, "
        "       SUM(debit_amount) AS debit "
        "FROM bank_ledger "
    )
    params = []
    wheres = []
    if start_date:
        wheres.append("docdate >= ?")
        params.append(start_date)
    if end_date:
        wheres.append("docdate <= ?")
        params.append(end_date)

    if wheres:
        query += " WHERE " + " AND ".join(wheres)
    query += " GROUP BY docdate ORDER BY docdate"

    df = pd.read_sql(query, conn, params=params)
    if df.empty:
        return df

    df["net_cash_flow"] = df["credit"] - df["debit"]
    df["cumulative_net"] = df["net_cash_flow"].cumsum()
    return df


def compute_percentiles(conn, percentile_list=None, start_date=None, end_date=None):
    """
    Compute transaction-size percentiles for the given timeframe.
    Returns dict: {'debit_percentiles': {...}, 'credit_percentiles': {...}}
    """
    if percentile_list is None:
        percentile_list = [10, 25, 50, 75, 90, 95, 99]

    query = "SELECT debit_amount, credit_amount FROM bank_ledger"
    params = []
    wheres = []
    if start_date:
        wheres.append("docdate >= ?")
        params.append(start_date)
    if end_date:
        wheres.append("docdate <= ?")
        params.append(end_date)
    if wheres:
        query += " WHERE " + " AND ".join(wheres)

    df = pd.read_sql(query, conn, params=params)
    if df.empty:
        return {"debit_percentiles": {}, "credit_percentiles": {}}

    debits = df["debit_amount"][df["debit_amount"] > 0]
    credits = df["credit_amount"][df["credit_amount"] > 0]

    debit_pctls = {}
    credit_pctls = {}
    for p in percentile_list:
        debit_pctls[f"P{p}"] = float(np.percentile(debits, p)) if len(debits) > 0 else 0
        credit_pctls[f"P{p}"] = float(np.percentile(credits, p)) if len(credits) > 0 else 0

    return {"debit_percentiles": debit_pctls, "credit_percentiles": credit_pctls}


def compute_branch_summary(conn):
    """
    Branch-wise total inward (credit) and outward (debit),
    with category-level breakdown.
    """
    df = pd.read_sql(
        "SELECT branch_id, group_name, "
        "       SUM(credit_amount) AS total_inward, "
        "       SUM(debit_amount) AS total_outward "
        "FROM bank_ledger "
        "GROUP BY branch_id, group_name "
        "ORDER BY branch_id, group_name", conn
    )
    return df


def compute_branch_totals(conn):
    """Branch-level aggregation without category breakdown."""
    df = pd.read_sql(
        "SELECT branch_id, "
        "       SUM(credit_amount) AS total_inward, "
        "       SUM(debit_amount) AS total_outward "
        "FROM bank_ledger "
        "GROUP BY branch_id "
        "ORDER BY branch_id", conn
    )
    if not df.empty:
        df["net_flow"] = df["total_inward"] - df["total_outward"]
    return df


def compute_category_summary(conn):
    """
    Category-wise total inward and outward (across all branches).
    """
    df = pd.read_sql(
        "SELECT group_name, "
        "       SUM(credit_amount) AS total_inward, "
        "       SUM(debit_amount) AS total_outward "
        "FROM bank_ledger "
        "GROUP BY group_name "
        "ORDER BY group_name", conn
    )
    if not df.empty:
        df["net_flow"] = df["total_inward"] - df["total_outward"]
    return df
