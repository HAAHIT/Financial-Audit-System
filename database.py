"""
Database connection, schema creation, and migrations.
"""

import sqlite3
from config import DB_NAME, DEFAULT_AUDIT_STATUS


def get_connection(db_path=None):
    """Return a SQLite connection. Uses DB_NAME from config if no path given."""
    path = db_path or DB_NAME
    return sqlite3.connect(path, check_same_thread=False)


def initialize_schema(conn):
    """Create all tables and run migrations for existing databases."""
    cursor = conn.cursor()

    # ── Core Ledger Tables ──────────────────────────────────
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS bank_ledger (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            docdate     TEXT,
            docno       TEXT,
            contra_ledger_name TEXT,
            group_name  TEXT,
            debit_amount  REAL DEFAULT 0,
            credit_amount REAL DEFAULT 0,
            branch_id   TEXT,
            narration   TEXT,
            voucher_type TEXT,
            audit_status TEXT DEFAULT '{DEFAULT_AUDIT_STATUS}'
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS purchase_ledger (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            inv_no        TEXT,
            inv_date      TEXT,
            party_name    TEXT,
            item_name     TEXT,
            rec_qty       REAL DEFAULT 0,
            billing_quantity REAL DEFAULT 0,
            material_value REAL DEFAULT 0,
            tax_amt       REAL DEFAULT 0,
            excise_amt    REAL DEFAULT 0,
            charges_amt   REAL DEFAULT 0,
            rebate_amt    REAL DEFAULT 0,
            net_amt       REAL DEFAULT 0,
            audit_status  TEXT DEFAULT '{DEFAULT_AUDIT_STATUS}'
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS sales_ledger (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            inv_no          TEXT,
            docdate         TEXT,
            branch          TEXT,
            party_name      TEXT,
            state           TEXT,
            item_group      TEXT,
            item_name       TEXT,
            packing_type    TEXT,
            billing_quantity REAL DEFAULT 0,
            billing_pkgs    REAL DEFAULT 0,
            net_rate        REAL DEFAULT 0,
            material_value  REAL DEFAULT 0,
            tax_per         REAL DEFAULT 0,
            tax_name        TEXT,
            audit_status    TEXT DEFAULT '{DEFAULT_AUDIT_STATUS}'
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS gst_portal (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            docdate           TEXT,
            portal_tax_amount REAL DEFAULT 0,
            audit_status      TEXT DEFAULT '{DEFAULT_AUDIT_STATUS}'
        )
    """)

    # ── Audit Support Tables ────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_flags (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name  TEXT NOT NULL,
            record_id   INTEGER,
            flag_type   TEXT,
            category    TEXT DEFAULT 'Pending',
            notes       TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS party_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            party_name  TEXT,
            year        TEXT,
            total_debit  REAL DEFAULT 0,
            total_credit REAL DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transaction_links (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_uid TEXT,
            bank_docno      TEXT,
            purchase_inv_no TEXT,
            sales_inv_no    TEXT
        )
    """)

    # ── Migrations for legacy schema (no AUTOINCREMENT id) ──
    _safe_add_column(cursor, "bank_ledger", "audit_status", f"TEXT DEFAULT '{DEFAULT_AUDIT_STATUS}'")
    _safe_add_column(cursor, "bank_ledger", "narration", "TEXT")
    _safe_add_column(cursor, "bank_ledger", "voucher_type", "TEXT")
    _safe_add_column(cursor, "purchase_ledger", "audit_status", f"TEXT DEFAULT '{DEFAULT_AUDIT_STATUS}'")
    _safe_add_column(cursor, "purchase_ledger", "rebate_amt", "REAL DEFAULT 0")
    _safe_add_column(cursor, "purchase_ledger", "billing_quantity", "REAL DEFAULT 0")
    _safe_add_column(cursor, "purchase_ledger", "excise_amt", "REAL DEFAULT 0")
    _safe_add_column(cursor, "sales_ledger", "audit_status", f"TEXT DEFAULT '{DEFAULT_AUDIT_STATUS}'")
    _safe_add_column(cursor, "sales_ledger", "branch", "TEXT")
    _safe_add_column(cursor, "sales_ledger", "state", "TEXT")
    _safe_add_column(cursor, "sales_ledger", "item_group", "TEXT")
    _safe_add_column(cursor, "sales_ledger", "packing_type", "TEXT")
    _safe_add_column(cursor, "sales_ledger", "billing_pkgs", "REAL DEFAULT 0")
    _safe_add_column(cursor, "sales_ledger", "tax_per", "REAL DEFAULT 0")
    _safe_add_column(cursor, "sales_ledger", "tax_name", "TEXT")

    conn.commit()


def _safe_add_column(cursor, table, column, col_type):
    """Add a column if it doesn't already exist (migration-safe)."""
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    except Exception:
        pass  # Column already exists
