"""Tests for data ingestion: CSV parsing, date normalization, dedup, numeric coercion."""

import io
import pandas as pd
import pytest

from data_ingestion import (
    clean_columns,
    standardize_dates,
    coerce_numeric,
    read_erp_csv,
    dedup_dataframe,
    dedup_against_db,
)


class TestCleanColumns:
    def test_strips_whitespace(self):
        df = pd.DataFrame({" Name ": [1], "  AGE": [2], "CITY  ": [3]})
        result = clean_columns(df)
        assert list(result.columns) == ["NAME", "AGE", "CITY"]

    def test_uppercases_columns(self):
        df = pd.DataFrame({"name": [1], "Age": [2], "CITY": [3]})
        result = clean_columns(df)
        assert list(result.columns) == ["NAME", "AGE", "CITY"]

    def test_does_not_modify_original(self):
        df = pd.DataFrame({"name": [1]})
        clean_columns(df)
        assert df.columns[0] == "name"


class TestStandardizeDates:
    def test_dd_mm_yyyy_format(self):
        df = pd.DataFrame({"INV_DATE": ["04-01-2025"]})
        result = standardize_dates(df, ["INV_DATE"])
        assert result["INV_DATE"].iloc[0] == "2025-01-04"

    def test_yyyy_mm_dd_format(self):
        df = pd.DataFrame({"INV_DATE": ["2025-01-15"]})
        result = standardize_dates(df, ["INV_DATE"])
        assert result["INV_DATE"].iloc[0] == "2025-01-15"

    def test_slash_format(self):
        df = pd.DataFrame({"INV_DATE": ["04/01/2025"]})
        result = standardize_dates(df, ["INV_DATE"])
        # dayfirst=True → 04 is the day
        assert result["INV_DATE"].iloc[0] == "2025-01-04"

    def test_missing_column_ignored(self):
        df = pd.DataFrame({"OTHER": ["2025-01-01"]})
        result = standardize_dates(df, ["INV_DATE"])
        assert "INV_DATE" not in result.columns

    def test_invalid_date_becomes_nat(self):
        df = pd.DataFrame({"INV_DATE": ["NOT_A_DATE"]})
        result = standardize_dates(df, ["INV_DATE"])
        assert pd.isna(result["INV_DATE"].iloc[0]) or result["INV_DATE"].iloc[0] == "NaT"

    def test_does_not_modify_original(self):
        df = pd.DataFrame({"INV_DATE": ["04-01-2025"]})
        standardize_dates(df, ["INV_DATE"])
        assert df["INV_DATE"].iloc[0] == "04-01-2025"


class TestCoerceNumeric:
    def test_string_with_commas(self):
        df = pd.DataFrame({"AMOUNT": ["1,234.56"]})
        result = coerce_numeric(df, ["AMOUNT"])
        assert result["AMOUNT"].iloc[0] == pytest.approx(1234.56)

    def test_non_numeric_becomes_zero(self):
        df = pd.DataFrame({"AMOUNT": ["abc"]})
        result = coerce_numeric(df, ["AMOUNT"])
        assert result["AMOUNT"].iloc[0] == 0.0

    def test_missing_column_ignored(self):
        df = pd.DataFrame({"OTHER": [100]})
        result = coerce_numeric(df, ["AMOUNT"])
        assert "AMOUNT" not in result.columns

    def test_already_numeric(self):
        df = pd.DataFrame({"AMOUNT": [42.5]})
        result = coerce_numeric(df, ["AMOUNT"])
        assert result["AMOUNT"].iloc[0] == 42.5


class TestReadErpCsv:
    def test_skips_junk_header_rows(self):
        csv_content = (
            '"Details for something",,,,\n'
            ',,,,\n'
            'Sr. No,BRANCH_ID,CONTRA_LEDGER_NAME,DEBIT_AMOUNT,CREDIT_AMOUNT\n'
            '1,15,RASHMI TRADERS,0,1000\n'
        )
        result = read_erp_csv(io.StringIO(csv_content))
        result = clean_columns(result)
        assert "CONTRA_LEDGER_NAME" in result.columns
        assert len(result) == 1

    def test_standard_header(self):
        csv_content = "INV_NO,PARTY_NAME,NET_AMT\nINV001,ABC,1000\n"
        result = read_erp_csv(io.StringIO(csv_content))
        result = clean_columns(result)
        assert "INV_NO" in result.columns
        assert len(result) == 1


class TestDedup:
    def test_removes_duplicate_rows(self):
        df = pd.DataFrame({"A": [1, 1, 2], "B": ["x", "x", "y"]})
        result = dedup_dataframe(df)
        assert len(result) == 2

    def test_keeps_unique_rows(self):
        df = pd.DataFrame({"A": [1, 2, 3], "B": ["x", "y", "z"]})
        result = dedup_dataframe(df)
        assert len(result) == 3

    def test_dedup_against_db_removes_existing(self, in_memory_db):
        # Insert a row — use floats to match SQLite's REAL type
        existing = pd.DataFrame({"docdate": ["2025-01-01"], "docno": ["D001"],
                                  "contra_ledger_name": ["TEST"], "group_name": ["G"],
                                  "debit_amount": [100.0], "credit_amount": [0.0],
                                  "branch_id": ["1"]})
        existing.to_sql("bank_ledger", in_memory_db, if_exists="append", index=False)

        # Try to insert same row
        incoming = existing.copy()
        result = dedup_against_db(incoming, "bank_ledger", in_memory_db)
        assert len(result) == 0

    def test_dedup_against_db_keeps_new(self, in_memory_db):
        existing = pd.DataFrame({"docdate": ["2025-01-01"], "docno": ["D001"],
                                  "contra_ledger_name": ["TEST"], "group_name": ["G"],
                                  "debit_amount": [100], "credit_amount": [0],
                                  "branch_id": ["1"]})
        existing.to_sql("bank_ledger", in_memory_db, if_exists="append", index=False)

        new_row = pd.DataFrame({"docdate": ["2025-01-02"], "docno": ["D002"],
                                 "contra_ledger_name": ["OTHER"], "group_name": ["G"],
                                 "debit_amount": [200], "credit_amount": [0],
                                 "branch_id": ["1"]})
        result = dedup_against_db(new_row, "bank_ledger", in_memory_db)
        assert len(result) == 1
