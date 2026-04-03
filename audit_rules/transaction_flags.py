"""
Transaction flagging: CRUD for audit flags, auto-classification
of transactions into the credit/debit taxonomy.
"""

import pandas as pd
from config import AUDIT_STATUSES, CREDIT_CATEGORIES, DEBIT_CATEGORIES


# ============================================================
# FLAG CRUD
# ============================================================

def add_flag(conn, table_name, record_id, flag_type, category="Pending", notes=""):
    """Insert a new audit flag."""
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO audit_flags (table_name, record_id, flag_type, category, notes) "
        "VALUES (?, ?, ?, ?, ?)",
        (table_name, record_id, flag_type, category, notes),
    )
    conn.commit()
    return cursor.lastrowid


def update_flag_category(conn, flag_id, category):
    """Update the category of an existing flag."""
    if category not in AUDIT_STATUSES:
        raise ValueError(f"Invalid category '{category}'. Must be one of {AUDIT_STATUSES}")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE audit_flags SET category = ? WHERE id = ?",
        (category, flag_id),
    )
    conn.commit()
    return cursor.rowcount > 0


def get_flags(conn, table_name=None, flag_type=None, category=None):
    """Query flags with optional filters."""
    query = "SELECT * FROM audit_flags WHERE 1=1"
    params = []

    if table_name:
        query += " AND table_name = ?"
        params.append(table_name)
    if flag_type:
        query += " AND flag_type = ?"
        params.append(flag_type)
    if category:
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY created_at DESC"
    return pd.read_sql(query, conn, params=params)


def delete_flag(conn, flag_id):
    """Delete a flag by ID."""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM audit_flags WHERE id = ?", (flag_id,))
    conn.commit()
    return cursor.rowcount > 0


# ============================================================
# AUTO-CLASSIFICATION
# ============================================================

def classify_transaction(group_name, contra_ledger_name, debit_amount, credit_amount):
    """
    Classify a bank transaction based on the taxonomy defined in config.
    Returns: (direction, category_key, category_description)
    """
    group_upper = (group_name or "").upper()
    ledger_upper = (contra_ledger_name or "").upper()
    searchable = group_upper + " " + ledger_upper

    if credit_amount > 0 and debit_amount == 0:
        direction = "CREDIT"
        for cat_key, cat_info in CREDIT_CATEGORIES.items():
            for kw in cat_info["keywords"]:
                if kw in searchable:
                    return direction, cat_key, cat_info["description"]
        return direction, "OTHER_CREDIT", "Unclassified credit"

    elif debit_amount > 0:
        direction = "DEBIT"
        for cat_key, cat_info in DEBIT_CATEGORIES.items():
            for kw in cat_info["keywords"]:
                if kw in searchable:
                    return direction, cat_key, cat_info["description"]
        return direction, "OTHER_DEBIT", "Unclassified debit"

    return "UNKNOWN", "UNKNOWN", "Zero-value transaction"


def classify_all_transactions(conn):
    """
    Classify every bank ledger transaction and return a DataFrame
    with the classification appended.
    """
    df = pd.read_sql("SELECT * FROM bank_ledger", conn)
    if df.empty:
        return df

    classifications = df.apply(
        lambda row: classify_transaction(
            row.get("group_name", ""),
            row.get("contra_ledger_name", ""),
            row.get("debit_amount", 0),
            row.get("credit_amount", 0),
        ),
        axis=1,
        result_type="expand",
    )
    classifications.columns = ["direction", "category_key", "category_desc"]
    return pd.concat([df, classifications], axis=1)
