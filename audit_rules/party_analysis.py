"""
Party analysis: 360-view reconciliation, YoY delta, new party detection,
inter-party anomalies, always-low-price buyer, party momentum.
"""

import pandas as pd
from config import LOW_PRICE_CONSISTENCY_PCT


def get_party_360(conn):
    """
    Full party reconciliation: total billed vs total paid,
    pending balance, year-over-year delta, and last-year ledger balance.
    """
    purchases = pd.read_sql(
        "SELECT party_name, SUM(net_amt) AS total_billed "
        "FROM purchase_ledger GROUP BY party_name", conn
    )
    payments = pd.read_sql(
        "SELECT contra_ledger_name AS party_name, SUM(debit_amount) AS total_paid "
        "FROM bank_ledger GROUP BY contra_ledger_name", conn
    )
    recon = pd.merge(purchases, payments, on="party_name", how="outer").fillna(0)
    recon["pending_balance"] = recon["total_billed"] - recon["total_paid"]

    # YoY delta
    yearly = pd.read_sql(
        "SELECT contra_ledger_name AS party_name, "
        "       substr(docdate, 1, 4) AS year, "
        "       SUM(debit_amount) AS yearly_paid "
        "FROM bank_ledger GROUP BY party_name, year", conn
    )
    if not yearly.empty:
        pivot = yearly.pivot(index="party_name", columns="year", values="yearly_paid").fillna(0)
        years = sorted(pivot.columns.tolist())
        if len(years) >= 2:
            pivot["yoy_delta"] = pivot[years[-1]] - pivot[years[-2]]
            pivot["last_year_balance"] = pivot[years[-2]]
            recon = pd.merge(recon, pivot[["yoy_delta", "last_year_balance"]],
                             left_on="party_name", right_index=True, how="left").fillna(0)

    return recon.sort_values("pending_balance", ascending=False).reset_index(drop=True)


def detect_new_parties(conn):
    """Flag parties with only 1 transaction ever."""
    df = pd.read_sql("SELECT * FROM bank_ledger", conn)
    if df.empty:
        return pd.DataFrame()

    counts = df["contra_ledger_name"].value_counts()
    single_entry = counts[counts == 1].index
    flagged = df[df["contra_ledger_name"].isin(single_entry)]
    return flagged.reset_index(drop=True)


def detect_new_party_in_new_group(conn):
    """
    Double-flag: a party that is both new (single transaction)
    AND appears in a group that has no other parties.
    """
    df = pd.read_sql("SELECT * FROM bank_ledger", conn)
    if df.empty:
        return pd.DataFrame()

    party_counts = df["contra_ledger_name"].value_counts()
    new_parties = set(party_counts[party_counts == 1].index)

    group_party_counts = df.groupby("group_name")["contra_ledger_name"].nunique()
    single_party_groups = set(group_party_counts[group_party_counts == 1].index)

    flagged = df[
        (df["contra_ledger_name"].isin(new_parties))
        & (df["group_name"].isin(single_party_groups))
    ]
    return flagged.reset_index(drop=True)


def detect_interparty_anomalies(conn):
    """
    Detect overbilling/underbilling by comparing each party's
    average purchase rate against the global average per item.
    """
    global_avg = pd.read_sql(
        "SELECT item_name, AVG(material_value / rec_qty) AS global_avg_rate "
        "FROM purchase_ledger WHERE rec_qty > 0 GROUP BY item_name", conn
    )
    party_avg = pd.read_sql(
        "SELECT party_name, item_name, "
        "       AVG(material_value / rec_qty) AS party_avg_rate, "
        "       COUNT(*) AS txn_count "
        "FROM purchase_ledger WHERE rec_qty > 0 GROUP BY party_name, item_name", conn
    )
    if global_avg.empty or party_avg.empty:
        return pd.DataFrame()

    merged = pd.merge(party_avg, global_avg, on="item_name")
    merged["deviation_pct"] = (
        (merged["party_avg_rate"] - merged["global_avg_rate"]) / merged["global_avg_rate"]
    ) * 100

    # Flag both overbilling (>20%) and underbilling (<-20%)
    anomalies = merged[merged["deviation_pct"].abs() > 20.0]
    return anomalies.sort_values("deviation_pct", key=abs, ascending=False).reset_index(drop=True)


def detect_always_low_buyer(conn, threshold_pct=None):
    """
    Find parties that consistently buy at a price lower than
    the global average (in sales context).
    """
    threshold = threshold_pct if threshold_pct is not None else LOW_PRICE_CONSISTENCY_PCT

    global_rates = pd.read_sql(
        "SELECT item_name, AVG(net_rate) AS global_avg_rate "
        "FROM sales_ledger WHERE net_rate > 0 GROUP BY item_name", conn
    )
    party_rates = pd.read_sql(
        "SELECT party_name, item_name, "
        "       AVG(net_rate) AS party_avg_rate, "
        "       COUNT(*) AS txn_count "
        "FROM sales_ledger WHERE net_rate > 0 GROUP BY party_name, item_name", conn
    )
    if global_rates.empty or party_rates.empty:
        return pd.DataFrame()

    merged = pd.merge(party_rates, global_rates, on="item_name")
    merged["discount_pct"] = (
        (merged["global_avg_rate"] - merged["party_avg_rate"]) / merged["global_avg_rate"]
    ) * 100

    # Only flag parties with multiple transactions AND consistent low price
    low_buyers = merged[
        (merged["discount_pct"] > threshold) & (merged["txn_count"] >= 3)
    ]
    return low_buyers.sort_values("discount_pct", ascending=False).reset_index(drop=True)


def compute_party_momentum(conn):
    """
    Compute quarterly payment momentum per party.
    Positive momentum = increasing payments quarter over quarter.
    """
    query = """
        SELECT contra_ledger_name AS party_name,
               substr(docdate, 1, 4) || '-Q' ||
               CASE
                   WHEN CAST(substr(docdate, 6, 2) AS INTEGER) <= 3 THEN '1'
                   WHEN CAST(substr(docdate, 6, 2) AS INTEGER) <= 6 THEN '2'
                   WHEN CAST(substr(docdate, 6, 2) AS INTEGER) <= 9 THEN '3'
                   ELSE '4'
               END AS quarter,
               SUM(debit_amount) AS total_paid
        FROM bank_ledger
        WHERE debit_amount > 0
        GROUP BY party_name, quarter
        ORDER BY party_name, quarter
    """
    df = pd.read_sql(query, conn)
    if df.empty:
        return pd.DataFrame()

    df["prev_quarter"] = df.groupby("party_name")["total_paid"].shift(1)
    df["momentum_pct"] = (
        (df["total_paid"] - df["prev_quarter"]) / df["prev_quarter"]
    ) * 100
    df = df.dropna(subset=["momentum_pct"])

    # Summarise: average momentum per party
    summary = df.groupby("party_name").agg(
        avg_momentum=("momentum_pct", "mean"),
        quarters_tracked=("momentum_pct", "count"),
    ).reset_index()

    return summary.sort_values("avg_momentum", ascending=False).reset_index(drop=True)
