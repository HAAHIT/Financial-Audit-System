"""
Shared test fixtures for the Financial Audit System test suite.
Provides in-memory SQLite databases pre-loaded with realistic sample data.
"""

import sys
import os
import pytest
import pandas as pd

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_connection, initialize_schema


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def in_memory_db():
    """Fresh in-memory SQLite database with schema initialised."""
    conn = get_connection(":memory:")
    initialize_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def sample_bank_df():
    """20 realistic bank ledger rows spanning multiple branches, groups, dates."""
    return pd.DataFrame({
        "docdate": [
            "2025-01-05", "2025-01-05", "2025-01-06", "2025-01-07", "2025-01-08",
            "2025-01-10", "2025-01-12", "2025-01-15", "2025-01-18", "2025-01-20",
            "2025-02-01", "2025-02-05", "2025-02-10", "2025-02-15", "2025-02-20",
            "2025-03-01", "2025-03-05", "2025-03-10", "2025-03-15", "2025-03-20",
        ],
        "docno": [f"DOC-{i:04d}" for i in range(1, 21)],
        "contra_ledger_name": [
            "RASHMI TRADERS", "MOEPL GANGAKHED", "ABC OILS LTD", "RASHMI TRADERS",
            "NEW VENDOR XYZ", "GST PAYMENT", "SALARY ACCOUNT", "RASHMI TRADERS",
            "ABC OILS LTD", "TRANSPORT CO", "RASHMI TRADERS", "MOEPL GANGAKHED",
            "TESTING LAB", "GST PAYMENT", "SALARY ACCOUNT", "RASHMI TRADERS",
            "NEW SINGLE PARTY", "ABC OILS LTD", "SALARY ACCOUNT", "BROKERAGE FIRM",
        ],
        "group_name": [
            "SUNDRY DEBTORS FOR DOC", "INTER BRANCH ACCOUNTS", "SUNDRY CREDITORS",
            "SUNDRY DEBTORS FOR DOC", "SUNDRY CREDITORS", "GST PAYMENTS",
            "SALARY", "SUNDRY DEBTORS FOR DOC", "SUNDRY CREDITORS",
            "TRANSPORT CHARGES", "SUNDRY DEBTORS FOR DOC", "INTER BRANCH ACCOUNTS",
            "TESTING CHARGES", "GST PAYMENTS", "SALARY",
            "SUNDRY DEBTORS FOR DOC", "NEW GROUP ALPHA", "SUNDRY CREDITORS",
            "SALARY", "BROKERAGE",
        ],
        "debit_amount": [
            0, 5948345, 250000, 0, 180000, 45000, 200000, 0,
            300000, 85000, 0, 6100000, 25000, 48000, 200000,
            0, 75000, 280000, 260000, 42000,
        ],
        "credit_amount": [
            1011363, 0, 0, 850000, 0, 0, 0, 920000,
            0, 0, 1100000, 0, 0, 0, 0,
            780000, 0, 0, 0, 0,
        ],
        "branch_id": [
            "15", "15", "15", "15", "15", "15", "15", "15", "15", "15",
            "20", "20", "20", "20", "20", "20", "20", "20", "20", "20",
        ],
    })


@pytest.fixture
def sample_purchase_df():
    """10 purchase ledger rows with varying items, rates, and quantities."""
    return pd.DataFrame({
        "inv_no": [f"PSTD24-{i:05d}" for i in range(1, 11)],
        "inv_date": [
            "2025-01-04", "2025-01-04", "2025-01-10", "2025-01-15", "2025-01-20",
            "2025-02-01", "2025-02-10", "2025-02-15", "2025-03-01", "2025-03-10",
        ],
        "party_name": [
            "ANANTAA ENTERPRISES", "MEHTA PAINTS", "ANANTAA ENTERPRISES",
            "GLOBAL SEEDS", "ANANTAA ENTERPRISES", "MEHTA PAINTS",
            "NEW SUPPLIER CO", "GLOBAL SEEDS", "ANANTAA ENTERPRISES",
            "OVERPRICED VENDOR",
        ],
        "item_name": [
            "STEAM COAL", "STORES AND SPARES", "STEAM COAL",
            "SOYA SEED", "STEAM COAL", "STORES AND SPARES",
            "STEAM COAL", "SOYA SEED", "STEAM COAL", "STEAM COAL",
        ],
        "rec_qty": [31.02, 1, 28.5, 100, 30, 2, 25, 120, 32, 10],
        "material_value": [
            254068, 3050, 233000, 500000, 245000, 6200,
            204000, 600000, 262000, 150000,
        ],
        "tax_amt": [12703, 549, 11650, 25000, 12250, 1116, 10200, 30000, 13100, 7500],
        "excise_amt": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "charges_amt": [12153, 0, 11000, 5000, 11500, 0, 9800, 6000, 12500, 5000],
        "rebate_amt": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "net_amt": [278924, 3599, 255650, 530000, 268750, 7316, 224000, 636000, 287600, 162500],
    })


@pytest.fixture
def sample_sales_df():
    """15 sales ledger rows with discount scenarios and multiple items."""
    return pd.DataFrame({
        "inv_no": [f"SBDG24-{i:05d}" for i in range(1, 16)],
        "docdate": [
            "2025-01-05", "2025-01-05", "2025-01-10", "2025-01-15", "2025-01-20",
            "2025-02-01", "2025-02-05", "2025-02-10", "2025-02-15", "2025-02-20",
            "2025-03-01", "2025-03-05", "2025-03-10", "2025-03-15", "2025-03-20",
        ],
        "party_name": [
            "PREMIUM CHICKS FEEDS", "PREMIUM CHICKS FEEDS", "AGRO TRADERS",
            "PREMIUM CHICKS FEEDS", "DISCOUNT BUYER",
            "AGRO TRADERS", "PREMIUM CHICKS FEEDS", "DISCOUNT BUYER",
            "AGRO TRADERS", "PREMIUM CHICKS FEEDS",
            "DISCOUNT BUYER", "AGRO TRADERS", "DISCOUNT BUYER",
            "PREMIUM CHICKS FEEDS", "DISCOUNT BUYER",
        ],
        "branch": ["GANGAKHED"] * 15,
        "item_name": [
            "YELLOW SOYA DOC", "YELLOW SOYA DOC", "YELLOW SOYA DOC",
            "REFINED SOYA OIL", "YELLOW SOYA DOC",
            "YELLOW SOYA DOC", "REFINED SOYA OIL", "YELLOW SOYA DOC",
            "REFINED SOYA OIL", "YELLOW SOYA DOC",
            "YELLOW SOYA DOC", "REFINED SOYA OIL", "REFINED SOYA OIL",
            "YELLOW SOYA DOC", "YELLOW SOYA DOC",
        ],
        "billing_quantity": [
            3.7, 30, 25, 5, 20,
            28, 8, 22, 6, 35,
            18, 7, 4, 32, 15,
        ],
        "net_rate": [
            35600, 34600, 35000, 95000, 30000,
            34800, 94000, 29500, 93000, 35200,
            29000, 94500, 80000, 34900, 28500,
        ],
        "material_value": [
            131720, 1038000, 875000, 475000, 600000,
            974400, 752000, 649000, 558000, 1232000,
            522000, 661500, 320000, 1116800, 427500,
        ],
        "tax_per": [5] * 15,
        "tax_name": ["IGST 5%"] * 15,
    })


@pytest.fixture
def loaded_db(in_memory_db, sample_bank_df, sample_purchase_df, sample_sales_df):
    """In-memory DB pre-loaded with all sample data."""
    sample_bank_df.to_sql("bank_ledger", in_memory_db, if_exists="append", index=False)
    sample_purchase_df.to_sql("purchase_ledger", in_memory_db, if_exists="append", index=False)
    sample_sales_df.to_sql("sales_ledger", in_memory_db, if_exists="append", index=False)

    # Add some GST portal data
    gst_data = pd.DataFrame({
        "docdate": ["2025-01-15", "2025-02-15", "2025-03-15"],
        "portal_tax_amount": [44000, 47000, 50000],
    })
    gst_data.to_sql("gst_portal", in_memory_db, if_exists="append", index=False)

    return in_memory_db
