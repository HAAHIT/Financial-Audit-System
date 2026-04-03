"""Tests for transaction flagging: CRUD and auto-classification."""

import pytest
import pandas as pd

from audit_rules.transaction_flags import (
    add_flag,
    update_flag_category,
    get_flags,
    delete_flag,
    classify_transaction,
    classify_all_transactions,
)


class TestFlagCRUD:
    def test_add_flag(self, in_memory_db):
        flag_id = add_flag(in_memory_db, "bank_ledger", 1, "NEW_PARTY")
        assert flag_id is not None
        assert flag_id > 0

    def test_get_flags_returns_inserted(self, in_memory_db):
        add_flag(in_memory_db, "bank_ledger", 1, "NEW_PARTY", "Pending", "Test note")
        flags = get_flags(in_memory_db)
        assert len(flags) == 1
        assert flags.iloc[0]["flag_type"] == "NEW_PARTY"
        assert flags.iloc[0]["notes"] == "Test note"

    def test_update_category(self, in_memory_db):
        flag_id = add_flag(in_memory_db, "bank_ledger", 1, "SPIKE")
        success = update_flag_category(in_memory_db, flag_id, "Checked")
        assert success
        flags = get_flags(in_memory_db, category="Checked")
        assert len(flags) == 1

    def test_update_invalid_category_raises(self, in_memory_db):
        flag_id = add_flag(in_memory_db, "bank_ledger", 1, "SPIKE")
        with pytest.raises(ValueError):
            update_flag_category(in_memory_db, flag_id, "INVALID_STATUS")

    def test_delete_flag(self, in_memory_db):
        flag_id = add_flag(in_memory_db, "bank_ledger", 1, "SPIKE")
        success = delete_flag(in_memory_db, flag_id)
        assert success
        flags = get_flags(in_memory_db)
        assert len(flags) == 0

    def test_filter_by_table(self, in_memory_db):
        add_flag(in_memory_db, "bank_ledger", 1, "TYPE_A")
        add_flag(in_memory_db, "purchase_ledger", 2, "TYPE_B")
        bank_flags = get_flags(in_memory_db, table_name="bank_ledger")
        assert len(bank_flags) == 1
        assert bank_flags.iloc[0]["table_name"] == "bank_ledger"

    def test_filter_by_flag_type(self, in_memory_db):
        add_flag(in_memory_db, "bank_ledger", 1, "SPIKE")
        add_flag(in_memory_db, "bank_ledger", 2, "NEW_PARTY")
        spikes = get_flags(in_memory_db, flag_type="SPIKE")
        assert len(spikes) == 1


class TestClassifyTransaction:
    def test_credit_party_payment(self):
        direction, key, desc = classify_transaction(
            "SUNDRY DEBTORS FOR DOC", "RASHMI TRADERS", 0, 1000000
        )
        assert direction == "CREDIT"
        assert key == "PARTY_PAYMENT"

    def test_debit_raw_material(self):
        direction, key, desc = classify_transaction(
            "SUNDRY CREDITORS", "SOYA VENDOR", 500000, 0
        )
        assert direction == "DEBIT"
        assert key == "RAW_MATERIAL"

    def test_debit_salary(self):
        direction, key, desc = classify_transaction(
            "SALARY", "SALARY ACCOUNT", 200000, 0
        )
        assert direction == "DEBIT"
        assert key == "SALARY"

    def test_debit_gst(self):
        direction, key, desc = classify_transaction(
            "GST PAYMENTS", "GST PAYMENT", 45000, 0
        )
        assert direction == "DEBIT"
        assert key == "GST_PAYMENT"

    def test_debit_transport(self):
        direction, key, desc = classify_transaction(
            "TRANSPORT CHARGES", "TRANSPORT CO", 85000, 0
        )
        assert direction == "DEBIT"
        assert key == "TRANSPORT"

    def test_debit_brokerage(self):
        direction, key, desc = classify_transaction(
            "BROKERAGE", "BROKER XYZ", 42000, 0
        )
        assert direction == "DEBIT"
        assert key == "BROKERAGE"

    def test_debit_testing_service(self):
        direction, key, desc = classify_transaction(
            "TESTING CHARGES", "TESTING LAB", 25000, 0
        )
        assert direction == "DEBIT"
        assert key == "SERVICE_ROUTINE"

    def test_unclassified_credit(self):
        direction, key, desc = classify_transaction(
            "UNKNOWN GROUP", "UNKNOWN PARTY", 0, 50000
        )
        assert direction == "CREDIT"
        assert key == "OTHER_CREDIT"

    def test_unclassified_debit(self):
        direction, key, desc = classify_transaction(
            "UNKNOWN GROUP", "UNKNOWN PARTY", 50000, 0
        )
        assert direction == "DEBIT"
        assert key == "OTHER_DEBIT"

    def test_zero_value(self):
        direction, key, desc = classify_transaction("G", "P", 0, 0)
        assert direction == "UNKNOWN"


class TestClassifyAll:
    def test_classifies_all_transactions(self, loaded_db):
        result = classify_all_transactions(loaded_db)
        assert "direction" in result.columns
        assert "category_key" in result.columns
        assert len(result) == 20  # 20 sample bank rows
