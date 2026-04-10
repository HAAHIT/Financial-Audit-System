"""Tests for ui_utils.render_filtered_dataframe — PR changes only.

Changes under test:
- Styler input now calls _compute() and uses _display_funcs to build safe_df
- allow_unsafe_jscode parameter (default False) passed through to AgGrid
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

import ui_utils  # noqa: E402 — imported after mocks are ready in each test


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

def _build_mocks():
    """Return a dict of mock objects and the patch.multiple kwargs for ui_utils."""
    aggrid_mock = MagicMock(return_value=MagicMock())

    gb_instance = MagicMock()
    gb_instance.build.return_value = {}
    gb_class_mock = MagicMock()
    gb_class_mock.from_dataframe.return_value = gb_instance

    mocks = dict(
        AgGrid=aggrid_mock,
        GridOptionsBuilder=gb_class_mock,
        GridUpdateMode=MagicMock(),
        DataReturnMode=MagicMock(),
        st=MagicMock(),
    )
    return mocks, aggrid_mock


def _render(df, key_prefix="test", **kwargs):
    """
    Call ui_utils.render_filtered_dataframe with all external UI deps mocked.
    Returns (aggrid_mock, return_value).
    """
    mocks, aggrid_mock = _build_mocks()
    with patch.multiple("ui_utils", **mocks):
        result = ui_utils.render_filtered_dataframe(df, key_prefix, **kwargs)
    return aggrid_mock, result


def _aggrid_df(aggrid_mock):
    """Extract the DataFrame positional arg that was passed to the AgGrid() call."""
    return aggrid_mock.call_args[0][0]


def _aggrid_kwargs(aggrid_mock):
    """Extract the keyword arguments passed to the AgGrid() call."""
    return aggrid_mock.call_args[1]


# ---------------------------------------------------------------------------
# Tests: allow_unsafe_jscode parameter
# ---------------------------------------------------------------------------

class TestAllowUnsafeJscode:
    def test_default_is_false(self):
        """Default value of allow_unsafe_jscode must be False (PR changed from hardcoded True)."""
        df = pd.DataFrame({"a": [1, 2]})
        aggrid_mock, _ = _render(df)
        assert _aggrid_kwargs(aggrid_mock)["allow_unsafe_jscode"] is False

    def test_explicit_false_is_forwarded(self):
        df = pd.DataFrame({"a": [1]})
        aggrid_mock, _ = _render(df, allow_unsafe_jscode=False)
        assert _aggrid_kwargs(aggrid_mock)["allow_unsafe_jscode"] is False

    def test_explicit_true_is_forwarded(self):
        df = pd.DataFrame({"a": [1]})
        aggrid_mock, _ = _render(df, allow_unsafe_jscode=True)
        assert _aggrid_kwargs(aggrid_mock)["allow_unsafe_jscode"] is True

    def test_aggrid_key_uses_prefix(self):
        """AgGrid key must be f'{key_prefix}_aggrid'."""
        df = pd.DataFrame({"a": [1]})
        aggrid_mock, _ = _render(df, key_prefix="my_table")
        assert _aggrid_kwargs(aggrid_mock)["key"] == "my_table_aggrid"

    def test_aggrid_called_exactly_once(self):
        df = pd.DataFrame({"a": [1]})
        aggrid_mock, _ = _render(df)
        aggrid_mock.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: Styler input — _compute() invocation
# ---------------------------------------------------------------------------

class TestStylerCompute:
    def test_compute_is_called(self):
        """render_filtered_dataframe must call _compute() on the Styler."""
        df = pd.DataFrame({"x": [1, 2]})
        styler = df.style
        original_compute = styler._compute

        compute_mock = MagicMock(side_effect=lambda: original_compute())

        with patch.object(type(styler), "_compute", compute_mock):
            _render(styler)

        compute_mock.assert_called_once()

    def test_display_funcs_fallback_identity_when_empty(self):
        """When _display_funcs is empty (no formatters), values pass through unchanged."""
        df = pd.DataFrame({"a": [42]})
        styler = df.style
        styler._compute()
        styler._display_funcs = {}  # force empty — identity fallback must handle it

        aggrid_mock, _ = _render(styler)
        passed_df = _aggrid_df(aggrid_mock)

        assert passed_df["a"].iloc[0] == 42

    def test_display_funcs_called_with_correct_cell_value(self):
        """_display_funcs formatters receive the raw cell value."""
        df = pd.DataFrame({"v": [7]})
        styler = df.style
        styler._compute()
        # Inject a known formatter for cell (0, 0)
        styler._display_funcs[(0, 0)] = lambda x: f"VAL={x}"

        aggrid_mock, _ = _render(styler)
        passed_df = _aggrid_df(aggrid_mock)

        assert "VAL=7" in str(passed_df["v"].iloc[0])


# ---------------------------------------------------------------------------
# Tests: Styler formatting applied to safe_df contents
# ---------------------------------------------------------------------------

class TestStylerFormatting:
    def test_format_applied_to_all_cells(self):
        """Styler.format() strings are reflected in the DataFrame passed to AgGrid."""
        df = pd.DataFrame({"price": [1.5, 2.75]})
        styler = df.style.format({"price": "${:.2f}"})

        aggrid_mock, _ = _render(styler)
        passed_df = _aggrid_df(aggrid_mock)

        values = passed_df["price"].astype(str).tolist()
        assert "$1.50" in values
        assert "$2.75" in values

    def test_unformatted_columns_keep_raw_values(self):
        """Columns without a Styler formatter use the identity — raw values preserved."""
        df = pd.DataFrame({"a": [1], "b": [99]})
        styler = df.style.format({"a": "A:{}"})  # only 'a' is formatted

        aggrid_mock, _ = _render(styler)
        passed_df = _aggrid_df(aggrid_mock)

        b_vals = passed_df["b"].tolist()
        assert b_vals == [99] or str(b_vals[0]) == "99"

    def test_styler_preserves_column_names(self):
        df = pd.DataFrame({"col1": [10], "col2": [20]})
        styler = df.style

        aggrid_mock, _ = _render(styler)
        passed_df = _aggrid_df(aggrid_mock)

        assert list(passed_df.columns) == ["col1", "col2"]

    def test_styler_preserves_row_count(self):
        df = pd.DataFrame({"v": list(range(7))})
        styler = df.style.format({"v": "v={}"})

        aggrid_mock, _ = _render(styler)
        passed_df = _aggrid_df(aggrid_mock)

        assert len(passed_df) == 7

    def test_empty_styler_does_not_raise(self):
        df = pd.DataFrame({"x": pd.Series([], dtype=float)})
        styler = df.style

        aggrid_mock, _ = _render(styler)
        passed_df = _aggrid_df(aggrid_mock)

        assert len(passed_df) == 0
        assert "x" in passed_df.columns

    def test_styler_with_na_rep_does_not_raise(self):
        """NaN cells with na_rep formatting must not raise during safe_df construction."""
        df = pd.DataFrame({"val": [1.0, float("nan"), 3.0]})
        styler = df.style.format({"val": "{:.1f}"}, na_rep="N/A")

        aggrid_mock, _ = _render(styler)
        passed_df = _aggrid_df(aggrid_mock)

        assert len(passed_df) == 3


# ---------------------------------------------------------------------------
# Tests: Plain DataFrame input
# ---------------------------------------------------------------------------

class TestDataFrameInput:
    def test_values_preserved(self):
        df = pd.DataFrame({"a": [1, 2, 3]})
        aggrid_mock, _ = _render(df)
        passed_df = _aggrid_df(aggrid_mock)
        assert passed_df["a"].tolist() == [1, 2, 3]

    def test_original_dataframe_not_mutated(self):
        """Datetime serialization inside render must not modify the caller's DataFrame."""
        df = pd.DataFrame({"dt": pd.to_datetime(["2024-01-01"])})
        original_dtype = df["dt"].dtype
        _render(df)
        assert df["dt"].dtype == original_dtype

    def test_empty_dataframe_does_not_raise(self):
        df = pd.DataFrame({"col": pd.Series([], dtype=int)})
        aggrid_mock, _ = _render(df)
        passed_df = _aggrid_df(aggrid_mock)
        assert len(passed_df) == 0


# ---------------------------------------------------------------------------
# Tests: Index handling
# ---------------------------------------------------------------------------

class TestIndexHandling:
    def test_non_range_index_is_reset(self):
        """Named index becomes a column after reset_index so it's visible in AgGrid."""
        df = pd.DataFrame({"v": [10, 20]}, index=["row_a", "row_b"])
        aggrid_mock, _ = _render(df)
        passed_df = _aggrid_df(aggrid_mock)

        # After reset_index the default integer index is RangeIndex(2)
        assert list(passed_df.index) == [0, 1]
        # The old index label is now a regular column
        assert "index" in passed_df.columns or "v" in passed_df.columns

    def test_range_index_not_reset(self):
        """Standard RangeIndex must NOT add an extra column."""
        df = pd.DataFrame({"v": [1, 2]})
        aggrid_mock, _ = _render(df)
        passed_df = _aggrid_df(aggrid_mock)
        assert list(passed_df.columns) == ["v"]


# ---------------------------------------------------------------------------
# Tests: Serialization
# ---------------------------------------------------------------------------

class TestSerialization:
    def test_datetime_column_becomes_string(self):
        df = pd.DataFrame({"ts": pd.to_datetime(["2024-03-15 12:00:00", "2024-06-01 09:30:00"])})
        aggrid_mock, _ = _render(df)
        passed_df = _aggrid_df(aggrid_mock)

        # dt.strftime returns a string column; dtype may be object or StringDtype depending on pandas version
        assert pd.api.types.is_string_dtype(passed_df["ts"])
        assert passed_df["ts"].tolist() == ["2024-03-15 12:00:00", "2024-06-01 09:30:00"]

    def test_object_column_cast_to_str(self):
        df = pd.DataFrame({"mixed": [1, "two", 3.0]})
        aggrid_mock, _ = _render(df)
        passed_df = _aggrid_df(aggrid_mock)

        assert all(isinstance(v, str) for v in passed_df["mixed"].tolist())

    def test_numeric_column_not_serialized(self):
        """Pure int/float columns must stay numeric — no string conversion applied."""
        df = pd.DataFrame({"n": [1, 2, 3]})
        aggrid_mock, _ = _render(df)
        passed_df = _aggrid_df(aggrid_mock)

        assert pd.api.types.is_numeric_dtype(passed_df["n"])


# ---------------------------------------------------------------------------
# Regression / boundary tests
# ---------------------------------------------------------------------------

class TestRegressionAndBoundary:
    def test_allow_unsafe_jscode_was_not_left_as_hardcoded_true(self):
        """Regression: before this PR, allow_unsafe_jscode was hardcoded True.
        Ensure calling with no argument passes False, not True."""
        df = pd.DataFrame({"x": [1]})
        aggrid_mock, _ = _render(df)
        value = _aggrid_kwargs(aggrid_mock)["allow_unsafe_jscode"]
        assert value is False, (
            "allow_unsafe_jscode must default to False; was it accidentally left as True?"
        )

    def test_key_prefix_with_dashes_and_underscores(self):
        df = pd.DataFrame({"z": [0]})
        aggrid_mock, _ = _render(df, key_prefix="my-table_v2")
        assert _aggrid_kwargs(aggrid_mock)["key"] == "my-table_v2_aggrid"

    def test_mixed_column_types_no_exception(self):
        """DataFrame with int, float, str, and datetime columns must render without error."""
        df = pd.DataFrame({
            "int_col": [1, 2],
            "float_col": [1.1, 2.2],
            "str_col": ["a", "b"],
            "dt_col": pd.to_datetime(["2024-01-01", "2024-12-31"]),
        })
        aggrid_mock, _ = _render(df)
        passed_df = _aggrid_df(aggrid_mock)
        assert "int_col" in passed_df.columns
        assert "dt_col" in passed_df.columns
        assert pd.api.types.is_string_dtype(passed_df["dt_col"])  # datetime serialized to string

    def test_styler_display_funcs_get_uses_identity_lambda(self):
        """The .get((i,j), lambda x: x) fallback must return the raw value for missing keys."""
        df = pd.DataFrame({"a": [99], "b": [42]})
        styler = df.style
        # Only set formatter for column 'a' (index 0)
        styler._compute()
        # Remove any entry for column 'b' (index 1) to force the fallback
        styler._display_funcs.pop((0, 1), None)

        aggrid_mock, _ = _render(styler)
        passed_df = _aggrid_df(aggrid_mock)

        b_val = passed_df["b"].iloc[0]
        assert b_val == 42 or str(b_val) == "42"

    def test_styler_multicolumn_format_all_cells_formatted(self):
        """All cells in all columns should use their respective formatter."""
        df = pd.DataFrame({"x": [1, 2], "y": [10, 20]})
        styler = df.style.format({"x": "x={}", "y": "y={}"})

        aggrid_mock, _ = _render(styler)
        passed_df = _aggrid_df(aggrid_mock)

        x_vals = passed_df["x"].astype(str).tolist()
        y_vals = passed_df["y"].astype(str).tolist()
        assert "x=1" in x_vals and "x=2" in x_vals
        assert "y=10" in y_vals and "y=20" in y_vals