"""
Data ingestion: CSV parsing, cleaning, deduplication, and loading.
"""

import hashlib
import pandas as pd


# ============================================================
# CLEANING HELPERS
# ============================================================

def clean_columns(df):
    """Strip whitespace and uppercase all column names."""
    df = df.copy()
    df.columns = df.columns.str.strip().str.upper()
    return df


def standardize_dates(df, date_cols):
    """Normalize date columns to YYYY-MM-DD format."""
    df = df.copy()
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], dayfirst=True, errors="coerce").dt.strftime("%Y-%m-%d")
    return df


def coerce_numeric(df, cols):
    """Convert columns to numeric, replacing non-parseable values with 0."""
    df = df.copy()
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", "", regex=False),
                errors="coerce",
            ).fillna(0)
    return df


# ============================================================
# CSV READING (ERP-aware)
# ============================================================

def read_erp_csv(file, is_gst=False):
    """
    Read an ERP-exported CSV that often has junk header rows.
    Scans the first 15 rows for a recognisable header.
    """
    if is_gst:
        return pd.read_csv(file)

    df_temp = pd.read_csv(file, header=None, nrows=15)
    header_idx = 0
    known_headers = {
        "DOCNO", "INV_NO", "PARTY_NAME", "CONTRA_LEDGER_NAME",
        "BRANCH_ID", "ITEM_NAME", "SR. NO",
    }
    for i, row in df_temp.iterrows():
        row_vals = set(row.astype(str).str.strip().str.upper())
        if row_vals & known_headers:
            header_idx = i
            break

    file.seek(0)
    return pd.read_csv(file, skiprows=header_idx)


# ============================================================
# ROW HASHING & DEDUPLICATION
# ============================================================

def _row_hash(row):
    """Create a deterministic hash of a row for dedup."""
    vals = "|".join(str(v) for v in row.values)
    return hashlib.md5(vals.encode()).hexdigest()


def dedup_dataframe(df):
    """Remove duplicate rows based on content hash."""
    df = df.copy()
    df["_hash"] = df.apply(_row_hash, axis=1)
    df = df.drop_duplicates(subset="_hash").drop(columns="_hash")
    return df


def dedup_against_db(df, table_name, conn):
    """
    Remove rows from df that already exist in the database table.
    Uses a content hash comparison on matching columns only.
    """
    try:
        existing = pd.read_sql(f"SELECT * FROM {table_name}", conn)
        if existing.empty:
            return df

        # Only compare columns that exist in both incoming df and existing table
        incoming_cols = list(df.columns)
        # Drop system columns that aren't in the incoming data
        compare_cols = [c for c in incoming_cols if c in existing.columns]
        if not compare_cols:
            return df

        existing_clean = existing[compare_cols]
        existing_hashes = set(existing_clean.apply(_row_hash, axis=1))

        # Hash incoming rows using only the comparable columns
        df = df.copy()
        df["_hash"] = df[compare_cols].apply(_row_hash, axis=1)
        df = df[~df["_hash"].isin(existing_hashes)].drop(columns="_hash")
        return df
    except Exception:
        return df


# ============================================================
# TABLE-SPECIFIC LOADERS
# ============================================================

def load_bank_csv(file, conn):
    """Parse and load a bank CSV into bank_ledger."""
    df = clean_columns(read_erp_csv(file))
    df = standardize_dates(df, ["DOCDATE"])
    df = coerce_numeric(df, ["DEBIT_AMOUNT", "CREDIT_AMOUNT"])

    col_map = {
        "DOCDATE": "docdate",
        "DOCNO": "docno",
        "CONTRA_LEDGER_NAME": "contra_ledger_name",
        "GROUP_NAME": "group_name",
        "DEBIT_AMOUNT": "debit_amount",
        "CREDIT_AMOUNT": "credit_amount",
        "BRANCH_ID": "branch_id",
        "NARRATION": "narration",
        "VOUCHER_TYPE": "voucher_type",
    }
    available = {k: v for k, v in col_map.items() if k in df.columns}
    df = df.rename(columns=available)[list(available.values())]

    df = dedup_dataframe(df)
    df = dedup_against_db(df, "bank_ledger", conn)

    if not df.empty:
        df.to_sql("bank_ledger", conn, if_exists="append", index=False)
    return len(df)


def load_purchase_csv(file, conn):
    """Parse and load a purchase CSV into purchase_ledger."""
    df = clean_columns(read_erp_csv(file))
    df = standardize_dates(df, ["INV_DATE"])
    num_cols = ["REC_QTY", "BILLING_QUANTITY", "MATERIAL_VALUE", "TAX_AMT",
                "EXCISE_AMT", "CHARGES_AMT", "REBATE_AMT", "NET_AMT"]
    for c in num_cols:
        if c not in df.columns:
            df[c] = 0.0
    df = coerce_numeric(df, num_cols)

    col_map = {
        "INV_NO": "inv_no", "INV_DATE": "inv_date", "PARTY_NAME": "party_name",
        "ITEM_NAME": "item_name", "REC_QTY": "rec_qty",
        "BILLING_QUANTITY": "billing_quantity",
        "MATERIAL_VALUE": "material_value", "TAX_AMT": "tax_amt",
        "EXCISE_AMT": "excise_amt", "CHARGES_AMT": "charges_amt",
        "REBATE_AMT": "rebate_amt", "NET_AMT": "net_amt",
    }
    available = {k: v for k, v in col_map.items() if k in df.columns}
    df = df.rename(columns=available)[list(available.values())]

    df = dedup_dataframe(df)
    df = dedup_against_db(df, "purchase_ledger", conn)

    if not df.empty:
        df.to_sql("purchase_ledger", conn, if_exists="append", index=False)
    return len(df)


def load_sales_csv(file, conn):
    """Parse and load a sales CSV into sales_ledger."""
    df = clean_columns(read_erp_csv(file))
    df = standardize_dates(df, ["DOCDATE"])
    num_cols = ["BILLING_QUANTITY", "BILLING_PKGS", "NET_RATE",
                "MATERIAL_VALUE", "TAX_PER"]
    for c in num_cols:
        if c not in df.columns:
            df[c] = 0.0
    df = coerce_numeric(df, num_cols)

    col_map = {
        "INV_NO": "inv_no", "DOCDATE": "docdate", "BRANCH": "branch",
        "PARTY_NAME": "party_name", "STATE": "state",
        "ITEM_GROUP": "item_group", "ITEM_NAME": "item_name",
        "PACKING_TYPE": "packing_type",
        "BILLING_QUANTITY": "billing_quantity", "BILLING_PKGS": "billing_pkgs",
        "NET_RATE": "net_rate", "MATERIAL_VALUE": "material_value",
        "TAX_PER": "tax_per", "TAX_NAME": "tax_name",
    }
    available = {k: v for k, v in col_map.items() if k in df.columns}
    df = df.rename(columns=available)[list(available.values())]

    df = dedup_dataframe(df)
    df = dedup_against_db(df, "sales_ledger", conn)

    if not df.empty:
        df.to_sql("sales_ledger", conn, if_exists="append", index=False)
    return len(df)


def load_gst_csv(file, conn):
    """Parse and load a GST portal CSV into gst_portal."""
    df = clean_columns(read_erp_csv(file, is_gst=True))
    df = standardize_dates(df, ["DATE", "DOCDATE"])

    date_col = next((c for c in ["DOCDATE", "DATE"] if c in df.columns), None)
    tax_col = next((c for c in ["TAX_AMOUNT", "AMOUNT", "PORTAL_TAX_AMOUNT"] if c in df.columns), None)

    if not date_col or not tax_col:
        return 0

    df = df.rename(columns={date_col: "docdate", tax_col: "portal_tax_amount"})
    df = coerce_numeric(df, ["portal_tax_amount"])
    df = df[["docdate", "portal_tax_amount"]]

    df = dedup_dataframe(df)
    df = dedup_against_db(df, "gst_portal", conn)

    if not df.empty:
        df.to_sql("gst_portal", conn, if_exists="append", index=False)
    return len(df)
