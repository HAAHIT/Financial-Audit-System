"""Tests for ui_utils.py — covers PR changes:
- Styler input: _compute() called, _display_funcs applied per-cell
- allow_unsafe_jscode parameter default (False) and pass-through
"""

import pandas as pd
import pytest
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_aggrid_mock():
    """Return a MagicMock that records the kwargs passed to AgGrid()."""
    return MagicMock(return_value=MagicMock())


def _patch_aggrid(mock_aggrid):
    """Context-manager patcher for st_aggrid symbols."""
    return patch.dict(
        "sys.modules",
        {
            "streamlit": MagicMock(),
            "st_aggrid": MagicMock(
                AgGrid=mock_aggrid,
                GridOptionsBuilder=_make_grid_options_builder(),
                GridUpdateMode=MagicMock(NO_UPDATE="NO_UPDATE"),
                DataReturnMode=MagicMock(FILTERED_AND_SORTED="FILTERED_AND_SORTED"),
            ),
        },
    )


def _make_grid_options_builder():
    """Minimal GridOptionsBuilder stub that satisfies the function's usage."""
    gb_instance = MagicMock()
    gb_instance.build.return_value = {}
    builder_cls = MagicMock()
    builder_cls.from_dataframe.return_value = gb_instance
    return builder_cls


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


class TestAllowUnsafeJscodeDefault:
    """allow_unsafe_jscode should default to False and be forwarded to AgGrid."""

    def test_default_is_false(self):
        mock_aggrid = _make_aggrid_mock()
        with _patch_aggrid(mock_aggrid):
            from importlib import import_module, reload
            import sys
            # Ensure fresh import with mocked modules
            if "ui_utils" in sys.modules:
                del sys.modules["ui_utils"]
            ui_utils = import_module("ui_utils")

            df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
            ui_utils.render_filtered_dataframe(df, key_prefix="test")

        _, kwargs = mock_aggrid.call_args
        assert kwargs.get("allow_unsafe_jscode") is False

    def test_explicit_false(self):
        mock_aggrid = _make_aggrid_mock()
        with _patch_aggrid(mock_aggrid):
            import sys
            if "ui_utils" in sys.modules:
                del sys.modules["ui_utils"]
            from importlib import import_module
            ui_utils = import_module("ui_utils")

            df = pd.DataFrame({"x": [10]})
            ui_utils.render_filtered_dataframe(df, "pfx", allow_unsafe_jscode=False)

        _, kwargs = mock_aggrid.call_args
        assert kwargs.get("allow_unsafe_jscode") is False

    def test_explicit_true_passed_through(self):
        mock_aggrid = _make_aggrid_mock()
        with _patch_aggrid(mock_aggrid):
            import sys
            if "ui_utils" in sys.modules:
                del sys.modules["ui_utils"]
            from importlib import import_module
            ui_utils = import_module("ui_utils")

            df = pd.DataFrame({"x": [10]})
            ui_utils.render_filtered_dataframe(df, "pfx", allow_unsafe_jscode=True)

        _, kwargs = mock_aggrid.call_args
        assert kwargs.get("allow_unsafe_jscode") is True


class TestAgGridKey:
    """key argument must be f'{key_prefix}_aggrid'."""

    def test_key_uses_prefix(self):
        mock_aggrid = _make_aggrid_mock()
        with _patch_aggrid(mock_aggrid):
            import sys
            if "ui_utils" in sys.modules:
                del sys.modules["ui_utils"]
            from importlib import import_module
            ui_utils = import_module("ui_utils")

            df = pd.DataFrame({"v": [1]})
            ui_utils.render_filtered_dataframe(df, "my_prefix")

        _, kwargs = mock_aggrid.call_args
        assert kwargs.get("key") == "my_prefix_aggrid"


class TestStylerInputComputeCalled:
    """When a Styler is passed, _compute() must be called before reading _display_funcs."""

    def test_compute_is_called_on_styler(self):
        mock_aggrid = _make_aggrid_mock()
        with _patch_aggrid(mock_aggrid):
            import sys
            if "ui_utils" in sys.modules:
                del sys.modules["ui_utils"]
            from importlib import import_module
            ui_utils = import_module("ui_utils")

            df = pd.DataFrame({"a": [1, 2]})
            styler = df.style
            styler._compute = MagicMock(return_value=styler)
            styler._display_funcs = {}  # no custom formatters

            ui_utils.render_filtered_dataframe(styler, "k")

        styler._compute.assert_called_once()


class TestStylerDisplayFuncsApplied:
    """Values in _display_funcs must be applied cell-by-cell in the output DataFrame."""

    def _run(self, styler, df, key_prefix="k"):
        mock_aggrid = _make_aggrid_mock()
        captured = {}

        def capture_aggrid(data, **kwargs):
            captured["data"] = data.copy()
            return MagicMock()

        mock_aggrid.side_effect = capture_aggrid

        with _patch_aggrid(mock_aggrid):
            import sys
            if "ui_utils" in sys.modules:
                del sys.modules["ui_utils"]
            from importlib import import_module
            ui_utils = import_module("ui_utils")
            ui_utils.render_filtered_dataframe(styler, key_prefix)

        return captured["data"]

    def test_formatter_applied_to_correct_cell(self):
        df = pd.DataFrame({"price": [9.99, 19.99]})
        styler = df.style
        styler._compute = MagicMock(return_value=styler)
        # Formatter for row 0, col 0 only
        styler._display_funcs = {(0, 0): lambda v: f"${v:.1f}"}

        result = self._run(styler, df)

        assert result["price"].iloc[0] == "$10.0"
        # Row 1 col 0 has no formatter — fallback lambda returns raw value
        assert result["price"].iloc[1] == 19.99

    def test_no_formatters_returns_raw_values(self):
        df = pd.DataFrame({"count": [5, 10]})
        styler = df.style
        styler._compute = MagicMock(return_value=styler)
        styler._display_funcs = {}  # empty → all use fallback

        result = self._run(styler, df)

        assert result["count"].iloc[0] == 5
        assert result["count"].iloc[1] == 10

    def test_all_cells_formatted(self):
        df = pd.DataFrame({"val": [1, 2], "label": ["a", "b"]})
        styler = df.style
        styler._compute = MagicMock(return_value=styler)
        styler._display_funcs = {
            (0, 0): lambda v: f"num:{v}",
            (1, 0): lambda v: f"num:{v}",
            (0, 1): lambda v: v.upper(),
            (1, 1): lambda v: v.upper(),
        }

        result = self._run(styler, df)

        assert result["val"].iloc[0] == "num:1"
        assert result["val"].iloc[1] == "num:2"
        assert result["label"].iloc[0] == "A"
        assert result["label"].iloc[1] == "B"

    def test_output_preserves_columns(self):
        df = pd.DataFrame({"x": [1], "y": [2], "z": [3]})
        styler = df.style
        styler._compute = MagicMock(return_value=styler)
        styler._display_funcs = {}

        result = self._run(styler, df)

        assert list(result.columns[:3]) == ["x", "y", "z"]

    def test_output_preserves_row_count(self):
        df = pd.DataFrame({"n": list(range(7))})
        styler = df.style
        styler._compute = MagicMock(return_value=styler)
        styler._display_funcs = {}

        result = self._run(styler, df)

        assert len(result) == 7


class TestPlainDataFramePath:
    """When a plain DataFrame (not Styler) is passed, it must be copied directly."""

    def _run(self, df):
        mock_aggrid = _make_aggrid_mock()
        captured = {}

        def capture_aggrid(data, **kwargs):
            captured["data"] = data.copy()
            return MagicMock()

        mock_aggrid.side_effect = capture_aggrid

        with _patch_aggrid(mock_aggrid):
            import sys
            if "ui_utils" in sys.modules:
                del sys.modules["ui_utils"]
            from importlib import import_module
            ui_utils = import_module("ui_utils")
            ui_utils.render_filtered_dataframe(df, "k")

        return captured["data"]

    def test_plain_df_values_preserved(self):
        df = pd.DataFrame({"col": [100, 200, 300]})
        result = self._run(df)
        assert list(result["col"]) == [100, 200, 300]

    def test_plain_df_not_mutated(self):
        df = pd.DataFrame({"col": ["hello", "world"]})
        original_values = list(df["col"])
        self._run(df)
        assert list(df["col"]) == original_values


class TestStylerEmptyDataFrame:
    """Styler wrapping an empty DataFrame should not raise."""

    def test_empty_styler_does_not_raise(self):
        mock_aggrid = _make_aggrid_mock()
        with _patch_aggrid(mock_aggrid):
            import sys
            if "ui_utils" in sys.modules:
                del sys.modules["ui_utils"]
            from importlib import import_module
            ui_utils = import_module("ui_utils")

            df = pd.DataFrame({"a": pd.Series([], dtype=float)})
            styler = df.style
            styler._compute = MagicMock(return_value=styler)
            styler._display_funcs = {}

            # Should not raise
            ui_utils.render_filtered_dataframe(styler, "empty_test")

        mock_aggrid.assert_called_once()


class TestStylerNonRangeIndex:
    """Styler whose underlying DataFrame has a non-RangeIndex must have its index reset."""

    def _run(self, styler):
        mock_aggrid = _make_aggrid_mock()
        captured = {}

        def capture_aggrid(data, **kwargs):
            captured["data"] = data.copy()
            return MagicMock()

        mock_aggrid.side_effect = capture_aggrid

        with _patch_aggrid(mock_aggrid):
            import sys
            if "ui_utils" in sys.modules:
                del sys.modules["ui_utils"]
            from importlib import import_module
            ui_utils = import_module("ui_utils")
            ui_utils.render_filtered_dataframe(styler, "k")

        return captured["data"]

    def test_named_index_is_reset(self):
        df = pd.DataFrame({"val": [1, 2]}, index=pd.Index(["r1", "r2"], name="row_id"))
        styler = df.style
        styler._compute = MagicMock(return_value=styler)
        styler._display_funcs = {}

        result = self._run(styler)

        # After reset_index, old index becomes a column
        assert "row_id" in result.columns
        assert isinstance(result.index, pd.RangeIndex)


class TestAllowUnsafeJscodeRegressionNotHardcoded:
    """Regression: allow_unsafe_jscode must NOT be hardcoded to True (old bug)."""

    def test_old_hardcoded_true_is_gone(self):
        """Calling with no explicit flag must produce False, not True."""
        mock_aggrid = _make_aggrid_mock()
        with _patch_aggrid(mock_aggrid):
            import sys
            if "ui_utils" in sys.modules:
                del sys.modules["ui_utils"]
            from importlib import import_module
            ui_utils = import_module("ui_utils")

            df = pd.DataFrame({"z": [0]})
            ui_utils.render_filtered_dataframe(df, "reg")

        _, kwargs = mock_aggrid.call_args
        assert kwargs.get("allow_unsafe_jscode") is not True, (
            "allow_unsafe_jscode is still hardcoded to True — regression detected"
        )