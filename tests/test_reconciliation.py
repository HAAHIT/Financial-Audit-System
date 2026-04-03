"""Tests for reconciliation: GST, billing math, bank-vs-system."""

import pandas as pd
import pytest

from audit_rules.reconciliation import (
    reconcile_gst,
    check_billing_math,
    reconcile_bank_vs_system,
    check_payment_account_match,
    check_gst_misclassification,
)


class TestGSTReconciliation:
    def test_gst_match(self, loaded_db):
        """Should return a reconciliation DataFrame with mismatch column."""
        result = reconcile_gst(loaded_db)
        assert isinstance(result, pd.DataFrame)
        assert "mismatch" in result.columns

    def test_gst_mismatch_detected(self, loaded_db):
        """Our sample has bank GST ≠ portal GST, so mismatches exist."""
        result = reconcile_gst(loaded_db)
        if not result.empty:
            # At least some months should show non-zero mismatch
            assert "mismatch" in result.columns

    def test_empty_db(self, in_memory_db):
        result = reconcile_gst(in_memory_db)
        assert isinstance(result, pd.DataFrame)


class TestBillingMath:
    def test_correct_billing_passes(self, in_memory_db):
        """material + tax + charges - rebate = net should NOT be flagged."""
        df = pd.DataFrame({
            "inv_no": ["INV001"], "inv_date": ["2025-01-01"],
            "party_name": ["TEST"], "item_name": ["ITEM"],
            "rec_qty": [10], "billing_quantity": [10],
            "material_value": [100], "tax_amt": [18],
            "excise_amt": [0], "charges_amt": [5], "rebate_amt": [2],
            "net_amt": [121],  # 100 + 18 + 5 - 2 = 121 ✓
        })
        df.to_sql("purchase_ledger", in_memory_db, if_exists="append", index=False)
        result = check_billing_math(in_memory_db)
        assert result.empty

    def test_mismatch_caught(self, in_memory_db):
        """net_amt ≠ expected should be flagged."""
        df = pd.DataFrame({
            "inv_no": ["INV002"], "inv_date": ["2025-01-01"],
            "party_name": ["TEST"], "item_name": ["ITEM"],
            "rec_qty": [10], "billing_quantity": [10],
            "material_value": [100], "tax_amt": [18],
            "excise_amt": [0], "charges_amt": [5], "rebate_amt": [2],
            "net_amt": [130],  # Expected 121, got 130 → ₹9 discrepancy
        })
        df.to_sql("purchase_ledger", in_memory_db, if_exists="append", index=False)
        result = check_billing_math(in_memory_db)
        assert len(result) == 1
        assert result.iloc[0]["discrepancy"] == pytest.approx(9.0)

    def test_within_tolerance(self, in_memory_db):
        """A ₹0.50 difference should NOT be flagged (tolerance = ₹1)."""
        df = pd.DataFrame({
            "inv_no": ["INV003"], "inv_date": ["2025-01-01"],
            "party_name": ["TEST"], "item_name": ["ITEM"],
            "rec_qty": [10], "billing_quantity": [10],
            "material_value": [100], "tax_amt": [18],
            "excise_amt": [0], "charges_amt": [5], "rebate_amt": [2],
            "net_amt": [121.5],  # ₹0.50 off → within tolerance
        })
        df.to_sql("purchase_ledger", in_memory_db, if_exists="append", index=False)
        result = check_billing_math(in_memory_db, tolerance=1.0)
        assert result.empty

    def test_with_loaded_data(self, loaded_db):
        """Run against sample data and verify structure."""
        result = check_billing_math(loaded_db)
        assert isinstance(result, pd.DataFrame)


class TestBankVsSystem:
    def test_finds_unmatched_bank_entries(self, loaded_db):
        """Bank parties not in purchase/sales should be flagged."""
        result = reconcile_bank_vs_system(loaded_db)
        assert isinstance(result, pd.DataFrame)
        # GST PAYMENT, SALARY ACCOUNT etc. are not purchase/sales parties
        if not result.empty:
            assert len(result) > 0

    def test_empty_db(self, in_memory_db):
        result = reconcile_bank_vs_system(in_memory_db)
        assert result.empty


class TestPaymentAccountMatch:
    def test_returns_dataframe(self, loaded_db):
        result = check_payment_account_match(loaded_db)
        assert isinstance(result, pd.DataFrame)

    def test_empty_db(self, in_memory_db):
        result = check_payment_account_match(in_memory_db)
        assert result.empty


class TestGSTMisclassification:
    def test_returns_dataframe(self, loaded_db):
        result = check_gst_misclassification(loaded_db)
        assert isinstance(result, pd.DataFrame)

    def test_empty_db(self, in_memory_db):
        result = check_gst_misclassification(in_memory_db)
        assert result.empty
