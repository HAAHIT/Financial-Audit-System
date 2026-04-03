"""Tests for correlation engine: Pearson correlation, edge cases."""

import pandas as pd
import numpy as np
import pytest

from audit_rules.correlation import (
    build_time_series,
    correlate,
    correlate_two_metrics,
    find_all_correlations,
)


class TestCorrelate:
    def test_perfect_positive(self):
        a = pd.Series([1, 2, 3, 4, 5])
        b = pd.Series([2, 4, 6, 8, 10])
        r, p = correlate(a, b)
        assert r == pytest.approx(1.0, abs=0.01)

    def test_perfect_negative(self):
        a = pd.Series([1, 2, 3, 4, 5])
        b = pd.Series([10, 8, 6, 4, 2])
        r, p = correlate(a, b)
        assert r == pytest.approx(-1.0, abs=0.01)

    def test_no_correlation(self):
        np.random.seed(42)
        a = pd.Series(np.random.randn(100))
        b = pd.Series(np.random.randn(100))
        r, p = correlate(a, b)
        assert abs(r) < 0.3

    def test_single_data_point(self):
        a = pd.Series([1])
        b = pd.Series([2])
        r, p = correlate(a, b)
        assert r is None
        assert p is None

    def test_empty_series(self):
        a = pd.Series([], dtype=float)
        b = pd.Series([], dtype=float)
        r, p = correlate(a, b)
        assert r is None


class TestBuildTimeSeries:
    def test_returns_dataframe(self, loaded_db):
        result = build_time_series(loaded_db)
        assert isinstance(result, pd.DataFrame)
        assert "month" in result.columns
        assert "metric" in result.columns
        assert "val" in result.columns

    def test_has_multiple_metrics(self, loaded_db):
        result = build_time_series(loaded_db)
        assert result["metric"].nunique() > 1

    def test_empty_db(self, in_memory_db):
        result = build_time_series(in_memory_db)
        assert result.empty


class TestCorrelateMetrics:
    def test_two_metrics(self, loaded_db):
        ts = build_time_series(loaded_db)
        if ts["metric"].nunique() >= 2:
            metrics = ts["metric"].unique()
            r, p, merged = correlate_two_metrics(loaded_db, metrics[0], metrics[1])
            assert isinstance(merged, pd.DataFrame)

    def test_empty_db(self, in_memory_db):
        r, p, merged = correlate_two_metrics(in_memory_db, "A", "B")
        assert r is None


class TestCorrelationMatrix:
    def test_returns_matrix(self, loaded_db):
        result = find_all_correlations(loaded_db, min_months=1)
        assert isinstance(result, pd.DataFrame)

    def test_empty_db(self, in_memory_db):
        result = find_all_correlations(in_memory_db)
        assert result.empty
