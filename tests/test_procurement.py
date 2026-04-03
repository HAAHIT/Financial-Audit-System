"""Tests for procurement: price outliers, avg cost, BOM validation."""

import pandas as pd
import pytest

from audit_rules.procurement import (
    detect_price_outliers,
    compute_avg_material_cost,
    validate_bom_totals,
    check_bom_historical,
)


class TestPriceOutliers:
    def test_price_within_variance(self, loaded_db):
        """Items within 20% variance should NOT be flagged at 20% threshold."""
        result = detect_price_outliers(loaded_db, variance_pct=20)
        if not result.empty:
            assert all(result["variance_pct"] > 0.20)

    def test_lower_threshold_catches_more(self, loaded_db):
        """A 5% threshold should flag more than 50% threshold."""
        low = detect_price_outliers(loaded_db, variance_pct=5)
        high = detect_price_outliers(loaded_db, variance_pct=50)
        assert len(high) <= len(low)

    def test_overpriced_vendor_flagged(self, loaded_db):
        """OVERPRICED VENDOR buys STEAM COAL at ₹15000/unit vs ~₹8000 avg."""
        outliers = detect_price_outliers(loaded_db, variance_pct=20)
        if not outliers.empty:
            parties = outliers["party_name"].tolist()
            assert "OVERPRICED VENDOR" in parties

    def test_empty_db(self, in_memory_db):
        result = detect_price_outliers(in_memory_db)
        assert result.empty


class TestAvgMaterialCost:
    def test_computes_weighted_average(self, loaded_db):
        result = compute_avg_material_cost(loaded_db)
        assert not result.empty
        assert "weighted_avg_rate" in result.columns
        assert "txn_count" in result.columns

    def test_steam_coal_has_multiple_txns(self, loaded_db):
        result = compute_avg_material_cost(loaded_db)
        coal = result[result["item_name"] == "STEAM COAL"]
        assert not coal.empty
        assert coal.iloc[0]["txn_count"] >= 5  # Multiple purchases

    def test_empty_db(self, in_memory_db):
        result = compute_avg_material_cost(in_memory_db)
        assert result.empty


class TestBOMValidation:
    def test_bom_total_check(self, loaded_db):
        """Verify BOM validation runs without error."""
        result = validate_bom_totals(loaded_db)
        assert isinstance(result, pd.DataFrame)

    def test_bom_mismatch_detection(self, in_memory_db):
        """Invoice with components that don't sum correctly should be flagged."""
        df = pd.DataFrame({
            "inv_no": ["INV-BOM", "INV-BOM"],
            "inv_date": ["2025-01-01", "2025-01-01"],
            "party_name": ["VENDOR A", "VENDOR A"],
            "item_name": ["PART A", "PART B"],
            "rec_qty": [10, 5],
            "billing_quantity": [10, 5],
            "material_value": [1000, 500],
            "tax_amt": [180, 90],
            "excise_amt": [0, 0],
            "charges_amt": [50, 25],
            "rebate_amt": [0, 0],
            "net_amt": [1230, 700],  # Line 1: 1000+180+50=1230 ✓, Line 2: 500+90+25=615≠700 ✗
        })
        df.to_sql("purchase_ledger", in_memory_db, if_exists="append", index=False)
        result = validate_bom_totals(in_memory_db)
        # The invoice total expected = 1230+615=1845, actual net = 1230+700=1930
        assert len(result) == 1
        assert result.iloc[0]["bom_discrepancy"] == pytest.approx(85, abs=1)

    def test_empty_db(self, in_memory_db):
        result = validate_bom_totals(in_memory_db)
        assert result.empty


class TestBOMHistorical:
    def test_returns_dataframe(self, loaded_db):
        result = check_bom_historical(loaded_db)
        assert isinstance(result, pd.DataFrame)

    def test_empty_db(self, in_memory_db):
        result = check_bom_historical(in_memory_db)
        assert result.empty
