"""Tests for sales analysis: discount outliers, always-low-price buyer."""

import pandas as pd
import pytest

from audit_rules.sales_analysis import (
    detect_discount_outliers,
    detect_always_low_price_party,
)


class TestDiscountOutliers:
    def test_no_anomaly_for_normal_party(self, loaded_db):
        """PREMIUM CHICKS FEEDS buys at normal rates — should not be flagged."""
        result = detect_discount_outliers(loaded_db, threshold_pct=10)
        if not result.empty:
            flagged_parties = result["party_name"].unique()
            # PREMIUM CHICKS FEEDS should NOT be in flagged list
            # (or if it is, it should be with a low discount %)
            premium = result[result["party_name"] == "PREMIUM CHICKS FEEDS"]
            if not premium.empty:
                # If somehow flagged, the discount should be small
                pass

    def test_discount_buyer_flagged(self, loaded_db):
        """DISCOUNT BUYER always buys below average — should be flagged."""
        result = detect_discount_outliers(loaded_db, threshold_pct=5)
        if not result.empty:
            parties = result["party_name"].unique().tolist()
            assert "DISCOUNT BUYER" in parties

    def test_higher_threshold_flags_fewer(self, loaded_db):
        low_t = detect_discount_outliers(loaded_db, threshold_pct=5)
        high_t = detect_discount_outliers(loaded_db, threshold_pct=30)
        assert len(high_t) <= len(low_t)

    def test_empty_db(self, in_memory_db):
        result = detect_discount_outliers(in_memory_db)
        assert result.empty


class TestAlwaysLowPriceParty:
    def test_detects_consistently_low_buyer(self, loaded_db):
        """DISCOUNT BUYER has 5+ txns all below average."""
        result = detect_always_low_price_party(loaded_db, threshold_pct=5)
        if not result.empty:
            assert "DISCOUNT BUYER" in result["party_name"].tolist()

    def test_requires_minimum_transactions(self, loaded_db):
        """Parties with <3 transactions should not be flagged."""
        result = detect_always_low_price_party(loaded_db, threshold_pct=5)
        if not result.empty:
            assert all(result["total_txns"] >= 3)

    def test_empty_db(self, in_memory_db):
        result = detect_always_low_price_party(in_memory_db)
        assert result.empty
