"""
Reconciliation: GST vs portal, bank vs system, billing math,
payment account verification, GST misclassification.
"""

import pandas as pd
from config import BILLING_TOLERANCE


def reconcile_gst(conn):
    """
    Compare GST payments in bank ledger vs GST portal data.
    Returns DataFrame with month, bank_gst_paid, portal_gst_filed, mismatch.
    """
    gst_bank = pd.read_sql(
        "SELECT strftime('%Y-%m', docdate) AS month, "
        "       SUM(debit_amount) AS bank_gst_paid "
        "FROM bank_ledger "
        "WHERE group_name LIKE '%GST%' OR contra_ledger_name LIKE '%GST%' "
        "GROUP BY month", conn
    )
    gst_portal = pd.read_sql(
        "SELECT strftime('%Y-%m', docdate) AS month, "
        "       SUM(portal_tax_amount) AS portal_gst_filed "
        "FROM gst_portal GROUP BY month", conn
    )
    recon = pd.merge(gst_bank, gst_portal, on="month", how="outer").fillna(0)
    recon["mismatch"] = recon["bank_gst_paid"] - recon["portal_gst_filed"]
    return recon


def check_billing_math(conn, tolerance=None):
    """
    Verify: material_value + tax_amt + charges_amt - rebate_amt ≈ net_amt.
    Returns rows where the difference exceeds tolerance.
    """
    tol = tolerance if tolerance is not None else BILLING_TOLERANCE
    df = pd.read_sql("SELECT * FROM purchase_ledger", conn)
    if df.empty:
        return df

    df["expected_net"] = (
        df["material_value"] + df["tax_amt"]
        + df["charges_amt"] - df["rebate_amt"]
    )
    df["discrepancy"] = abs(df["net_amt"] - df["expected_net"])
    mismatches = df[df["discrepancy"] > tol]
    return mismatches.reset_index(drop=True)


def reconcile_bank_vs_system(conn):
    """
    Cross-check transactions that exist in bank but not in purchase/sales
    (indicating direct bank transactions not captured in ERP).
    Returns bank entries that can't be mapped to any purchase or sales invoice.
    """
    bank = pd.read_sql("SELECT * FROM bank_ledger", conn)
    if bank.empty:
        return pd.DataFrame()

    purchase_parties = set(
        pd.read_sql("SELECT DISTINCT party_name FROM purchase_ledger", conn)
        .get("party_name", pd.Series())
        .str.upper()
    )
    sales_parties = set(
        pd.read_sql("SELECT DISTINCT party_name FROM sales_ledger", conn)
        .get("party_name", pd.Series())
        .str.upper()
    )
    known_parties = purchase_parties | sales_parties

    bank["_party_upper"] = bank["contra_ledger_name"].str.upper()
    unmatched = bank[~bank["_party_upper"].isin(known_parties)].drop(columns="_party_upper")
    return unmatched.reset_index(drop=True)


def check_payment_account_match(conn):
    """
    For purchase invoices, verify that the bank debit went to the same
    party as the invoice. Returns mismatches.
    """
    purchases = pd.read_sql(
        "SELECT inv_no, party_name, net_amt FROM purchase_ledger", conn
    )
    bank_debits = pd.read_sql(
        "SELECT docno, contra_ledger_name, debit_amount FROM bank_ledger "
        "WHERE debit_amount > 0", conn
    )
    if purchases.empty or bank_debits.empty:
        return pd.DataFrame()

    # Normalise for matching
    purchases["_party"] = purchases["party_name"].str.upper().str.strip()
    bank_debits["_party"] = bank_debits["contra_ledger_name"].str.upper().str.strip()

    # Try to match by similar amount (within 1%) on the same party
    # Flag cases where the amount matches but the party doesn't
    mismatches = []
    for _, inv in purchases.iterrows():
        similar = bank_debits[
            (bank_debits["debit_amount"].between(inv["net_amt"] * 0.99, inv["net_amt"] * 1.01))
            & (bank_debits["_party"] != inv["_party"])
        ]
        for _, bank_row in similar.iterrows():
            mismatches.append({
                "inv_no": inv["inv_no"],
                "invoice_party": inv["party_name"],
                "invoice_amount": inv["net_amt"],
                "bank_party": bank_row["contra_ledger_name"],
                "bank_amount": bank_row["debit_amount"],
            })

    return pd.DataFrame(mismatches)


def check_gst_misclassification(conn):
    """
    Detect payments classified under GST in bank ledger that might not
    actually be GST payments (unusually large or small amounts).
    """
    gst_payments = pd.read_sql(
        "SELECT * FROM bank_ledger "
        "WHERE group_name LIKE '%GST%' OR contra_ledger_name LIKE '%GST%'", conn
    )
    if gst_payments.empty:
        return pd.DataFrame()

    # Flag if amount is an outlier within GST payments
    if len(gst_payments) > 1 and gst_payments["debit_amount"].std() > 0:
        mean_val = gst_payments["debit_amount"].mean()
        std_val = gst_payments["debit_amount"].std()
        gst_payments["z_score"] = (gst_payments["debit_amount"] - mean_val) / std_val
        flagged = gst_payments[gst_payments["z_score"].abs() > 2.0]
        return flagged.reset_index(drop=True)

    return pd.DataFrame()
