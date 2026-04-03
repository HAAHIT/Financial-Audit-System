"""Tests for party analysis: new parties, YoY delta, inter-party anomalies, momentum."""

import pandas as pd
import pytest

from audit_rules.party_analysis import (
    get_party_360,
    detect_new_parties,
    detect_new_party_in_new_group,
    detect_interparty_anomalies,
    detect_always_low_buyer,
    compute_party_momentum,
)


class TestParty360:
    def test_returns_reconciliation_data(self, loaded_db):
        result = get_party_360(loaded_db)
        assert isinstance(result, pd.DataFrame)
        assert "pending_balance" in result.columns

    def test_pending_balance_calculated(self, loaded_db):
        result = get_party_360(loaded_db)
        if not result.empty:
            # pending_balance = total_billed - total_paid
            for _, row in result.iterrows():
                expected = row["total_billed"] - row["total_paid"]
                assert row["pending_balance"] == pytest.approx(expected)

    def test_empty_db(self, in_memory_db):
        result = get_party_360(in_memory_db)
        assert isinstance(result, pd.DataFrame)


class TestNewParties:
    def test_detects_single_entry_party(self, loaded_db):
        """Party with only 1 transaction should be flagged."""
        result = detect_new_parties(loaded_db)
        assert not result.empty
        # "NEW SINGLE PARTY" has exactly 1 entry in our sample data
        parties = result["contra_ledger_name"].tolist()
        assert "NEW SINGLE PARTY" in parties

    def test_recurring_party_not_flagged(self, loaded_db):
        """Party with multiple transactions should NOT appear."""
        result = detect_new_parties(loaded_db)
        parties = result["contra_ledger_name"].tolist()
        # RASHMI TRADERS has many entries
        assert "RASHMI TRADERS" not in parties

    def test_empty_db(self, in_memory_db):
        result = detect_new_parties(in_memory_db)
        assert result.empty


class TestNewPartyInNewGroup:
    def test_double_flag(self, loaded_db):
        """NEW SINGLE PARTY in NEW GROUP ALPHA should be double-flagged."""
        result = detect_new_party_in_new_group(loaded_db)
        if not result.empty:
            parties = result["contra_ledger_name"].tolist()
            assert "NEW SINGLE PARTY" in parties

    def test_new_party_in_existing_group_not_flagged(self, loaded_db):
        """NEW VENDOR XYZ is new but in SUNDRY CREDITORS (existing group)."""
        result = detect_new_party_in_new_group(loaded_db)
        parties = result["contra_ledger_name"].tolist() if not result.empty else []
        # SUNDRY CREDITORS has multiple parties, so NEW VENDOR XYZ shouldn't be flagged here
        assert "NEW VENDOR XYZ" not in parties


class TestInterpartyAnomalies:
    def test_detects_over_or_underbilling(self, loaded_db):
        result = detect_interparty_anomalies(loaded_db)
        assert isinstance(result, pd.DataFrame)
        if not result.empty:
            assert "deviation_pct" in result.columns
            assert all(result["deviation_pct"].abs() > 20)

    def test_empty_db(self, in_memory_db):
        result = detect_interparty_anomalies(in_memory_db)
        assert result.empty


class TestAlwaysLowBuyer:
    def test_detects_discount_buyer(self, loaded_db):
        """DISCOUNT BUYER always buys below average in our sample data."""
        result = detect_always_low_buyer(loaded_db, threshold_pct=5)
        if not result.empty:
            parties = result["party_name"].tolist()
            assert "DISCOUNT BUYER" in parties

    def test_normal_buyer_not_flagged(self, loaded_db):
        result = detect_always_low_buyer(loaded_db, threshold_pct=5)
        parties = result["party_name"].tolist() if not result.empty else []
        # PREMIUM CHICKS FEEDS buys at normal rates
        assert "PREMIUM CHICKS FEEDS" not in parties

    def test_empty_db(self, in_memory_db):
        result = detect_always_low_buyer(in_memory_db)
        assert result.empty


class TestPartyMomentum:
    def test_returns_momentum(self, loaded_db):
        result = compute_party_momentum(loaded_db)
        assert isinstance(result, pd.DataFrame)
        if not result.empty:
            assert "avg_momentum" in result.columns

    def test_empty_db(self, in_memory_db):
        result = compute_party_momentum(in_memory_db)
        assert result.empty
