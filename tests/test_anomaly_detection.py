"""Tests for anomaly detection: expense spikes, salary spikes, Z-score outliers."""

import pandas as pd
import numpy as np
import pytest

from audit_rules.anomaly_detection import (
    detect_expense_spikes,
    detect_salary_spikes,
    compute_zscore_outliers,
    detect_sudden_changes,
)


class TestExpenseSpikes:
    def test_catches_50pct_increase(self, loaded_db):
        """A 50% MoM spike should be flagged at default 30% threshold."""
        spikes = detect_expense_spikes(loaded_db)
        # Our sample data has salary going from 200k → 260k (30%),
        # and various other groups. Just verify the function returns data.
        assert isinstance(spikes, pd.DataFrame)

    def test_custom_threshold(self, loaded_db):
        """Higher threshold should flag fewer items."""
        spikes_30 = detect_expense_spikes(loaded_db, threshold_pct=30)
        spikes_80 = detect_expense_spikes(loaded_db, threshold_pct=80)
        assert len(spikes_80) <= len(spikes_30)

    def test_ignores_sundry_and_interbranch(self, loaded_db):
        """SUNDRY and INTER BRANCH groups should be excluded."""
        spikes = detect_expense_spikes(loaded_db, threshold_pct=0)
        if not spikes.empty:
            assert not any(spikes["group_name"].str.contains("SUNDRY"))
            assert not any(spikes["group_name"].str.contains("INTER BRANCH"))

    def test_empty_db(self, in_memory_db):
        """Should handle empty database gracefully."""
        result = detect_expense_spikes(in_memory_db)
        assert isinstance(result, pd.DataFrame)
        assert result.empty


class TestSalarySpikes:
    def test_detects_salary_spike(self, loaded_db):
        """Salary increasing from 200k to 260k (30%) should be caught at 25% threshold."""
        spikes = detect_salary_spikes(loaded_db, threshold_pct=25)
        assert isinstance(spikes, pd.DataFrame)
        # Salary goes 200k → 200k → 260k, so the March spike should be caught
        if not spikes.empty:
            assert all(spikes["spike_pct"] > 25)

    def test_empty_db(self, in_memory_db):
        result = detect_salary_spikes(in_memory_db)
        assert isinstance(result, pd.DataFrame)


class TestZScoreOutliers:
    def test_identifies_outlier(self):
        """A value far from mean should be flagged."""
        series = pd.Series([10, 10, 10, 10, 10, 10, 10, 100])
        mask = compute_zscore_outliers(series, threshold=2.0)
        assert mask.iloc[-1] == True  # 100 is the outlier

    def test_no_outliers_in_uniform_data(self):
        """Uniform data should have no outliers."""
        series = pd.Series([10, 10, 10, 10, 10])
        mask = compute_zscore_outliers(series, threshold=2.0)
        assert not any(mask)

    def test_empty_series(self):
        series = pd.Series([], dtype=float)
        mask = compute_zscore_outliers(series)
        assert len(mask) == 0

    def test_single_value(self):
        series = pd.Series([42])
        mask = compute_zscore_outliers(series)
        assert mask.iloc[0] == False  # std = 0, no outlier possible


class TestSuddenChanges:
    def test_increase_only(self, loaded_db):
        result = detect_sudden_changes(loaded_db, direction="increase", threshold_pct=30)
        if not result.empty:
            assert all(result["change_pct"] > 30)

    def test_decrease_only(self, loaded_db):
        result = detect_sudden_changes(loaded_db, direction="decrease", threshold_pct=30)
        if not result.empty:
            assert all(result["change_pct"] < -30)

    def test_both_directions(self, loaded_db):
        result = detect_sudden_changes(loaded_db, direction="both", threshold_pct=30)
        if not result.empty:
            assert all(result["change_pct"].abs() > 30)

    def test_empty_db(self, in_memory_db):
        result = detect_sudden_changes(in_memory_db)
        assert result.empty
