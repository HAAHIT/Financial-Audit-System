"""
One-time migration: fix date formats in existing database.
Converts DD-MM-YYYY dates to YYYY-MM-DD for proper SQL sorting and grouping.
"""

import sqlite3
import pandas as pd
import sys

DB_NAME = "financial_data.db"


def migrate_dates():
    conn = sqlite3.connect(DB_NAME)

    # Bank ledger — docdate
    print("Migrating bank_ledger.docdate ...")
    bank = pd.read_sql("SELECT rowid, docdate FROM bank_ledger", conn)
    if not bank.empty:
        original = bank["docdate"].iloc[0]
        bank["docdate_fixed"] = pd.to_datetime(
            bank["docdate"], dayfirst=True, errors="coerce"
        ).dt.strftime("%Y-%m-%d")
        # Only update rows that changed
        changed = bank[bank["docdate"] != bank["docdate_fixed"]]
        print(f"  {len(changed)} rows need date fix (sample: '{original}' → '{bank['docdate_fixed'].iloc[0]}')")
        for _, row in changed.iterrows():
            conn.execute(
                "UPDATE bank_ledger SET docdate = ? WHERE rowid = ?",
                (row["docdate_fixed"], row["rowid"]),
            )
        conn.commit()
        print(f"  ✅ bank_ledger migrated.")

    # Purchase ledger — inv_date
    print("Migrating purchase_ledger.inv_date ...")
    purch = pd.read_sql("SELECT rowid, inv_date FROM purchase_ledger", conn)
    if not purch.empty:
        original = purch["inv_date"].iloc[0]
        purch["inv_date_fixed"] = pd.to_datetime(
            purch["inv_date"], dayfirst=True, errors="coerce"
        ).dt.strftime("%Y-%m-%d")
        changed = purch[purch["inv_date"] != purch["inv_date_fixed"]]
        print(f"  {len(changed)} rows need date fix (sample: '{original}' → '{purch['inv_date_fixed'].iloc[0]}')")
        for _, row in changed.iterrows():
            conn.execute(
                "UPDATE purchase_ledger SET inv_date = ? WHERE rowid = ?",
                (row["inv_date_fixed"], row["rowid"]),
            )
        conn.commit()
        print(f"  ✅ purchase_ledger migrated.")

    # Sales ledger — docdate
    print("Migrating sales_ledger.docdate ...")
    sales = pd.read_sql("SELECT rowid, docdate FROM sales_ledger", conn)
    if not sales.empty:
        original = sales["docdate"].iloc[0]
        sales["docdate_fixed"] = pd.to_datetime(
            sales["docdate"], dayfirst=True, errors="coerce"
        ).dt.strftime("%Y-%m-%d")
        changed = sales[sales["docdate"] != sales["docdate_fixed"]]
        print(f"  {len(changed)} rows need date fix (sample: '{original}' → '{sales['docdate_fixed'].iloc[0]}')")
        for _, row in changed.iterrows():
            conn.execute(
                "UPDATE sales_ledger SET docdate = ? WHERE rowid = ?",
                (row["docdate_fixed"], row["rowid"]),
            )
        conn.commit()
        print(f"  ✅ sales_ledger migrated.")

    # Verify
    print("\n=== Verification ===")
    sample = conn.execute("SELECT docdate FROM bank_ledger LIMIT 3").fetchall()
    print(f"  Bank sample dates: {[r[0] for r in sample]}")
    sample = conn.execute("SELECT inv_date FROM purchase_ledger LIMIT 3").fetchall()
    print(f"  Purchase sample dates: {[r[0] for r in sample]}")
    sample = conn.execute("SELECT docdate FROM sales_ledger LIMIT 3").fetchall()
    print(f"  Sales sample dates: {[r[0] for r in sample]}")

    conn.close()
    print("\n✅ Migration complete! All dates are now YYYY-MM-DD.")


if __name__ == "__main__":
    migrate_dates()
