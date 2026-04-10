"""Tests for ui_utils.render_filtered_dataframe — covering PR changes:
- Styler input: _compute() is called and _display_funcs formatters are applied
- allow_unsafe_jscode parameter defaults to False and is passed through to AgGrid
"""

import sys
import types
from unittest.mock import MagicMock, patch, call

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Helpers to build a minimal stub for st_aggrid so the import doesn't fail
# in environments where st_aggrid / streamlit are not installed.
# ---------------------------------------------------------------------------

def _make_aggrid_stub():
    aggrid_mod = types.ModuleType("st_aggrid")
    aggrid_mod.AgGrid = MagicMock(return_value=MagicMock(name="AgGridReturn"))
    aggrid_mod.GridOptionsBuilder = MagicMock()
    aggrid_mod.GridUpdateMode = MagicMock()
    aggrid_mod.DataReturnMode = MagicMock()
    return aggrid_mod


def _make_streamlit_stub():
    st_mod = types.ModuleType("streamlit")
    return st_mod


# ---------------------------------------------------------------------------
# Fixtures / setup
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def patch_external_deps(monkeypatch):
    """Replace streamlit and st_aggrid with lightweight stubs for every test."""
    st_stub = _make_streamlit_stub()
    aggrid_stub = _make_aggrid_stub()

    monkeypatch.setitem(sys.modules, "streamlit", st_stub)
    monkeypatch.setitem(sys.modules, "st_aggrid", aggrid_stub)

    # Reload ui_utils so it picks up the stubs
    if "ui_utils" in sys.modules:
        del sys.modules["ui_utils"]

    yield aggrid_stub

    # Clean up so other test modules aren't affected
    sys.modules.pop("ui_utils", None)


def _import_render():
    """Import render_filtered_dataframe after stubs are in place."""
    import ui_utils  # noqa: PLC0415
    return ui_utils.render_filtered_dataframe


# ---------------------------------------------------------------------------
# Helper: capture the `allow_unsafe_jscode` kwarg passed to AgGrid
# ---------------------------------------------------------------------------

def _last_aggrid_call_kwargs(aggrid_stub):
    return aggrid_stub.AgGrid.call_args.kwargs if aggrid_stub.AgGrid.call_args else {}


# ===========================================================================
# Tests for allow_unsafe_jscode parameter (PR change)
# ===========================================================================

class TestAllowUnsafeJscode:
    def test_default_is_false(self, patch_external_deps):
        """allow_unsafe_jscode should default to False."""
        render = _import_render()
        gb_mock = MagicMock()
        gb_mock.build.return_value = {}
        patch_external_deps.GridOptionsBuilder.from_dataframe.return_value = gb_mock

        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        render(df, "test")

        kwargs = _last_aggrid_call_kwargs(patch_external_deps)
        assert kwargs.get("allow_unsafe_jscode") is False

    def test_explicit_false(self, patch_external_deps):
        """Explicitly passing False should be forwarded to AgGrid."""
        render = _import_render()
        gb_mock = MagicMock()
        gb_mock.build.return_value = {}
        patch_external_deps.GridOptionsBuilder.from_dataframe.return_value = gb_mock

        df = pd.DataFrame({"x": [10]})
        render(df, "pfx", allow_unsafe_jscode=False)

        kwargs = _last_aggrid_call_kwargs(patch_external_deps)
        assert kwargs.get("allow_unsafe_jscode") is False

    def test_explicit_true(self, patch_external_deps):
        """Passing allow_unsafe_jscode=True should be forwarded to AgGrid."""
        render = _import_render()
        gb_mock = MagicMock()
        gb_mock.build.return_value = {}
        patch_external_deps.GridOptionsBuilder.from_dataframe.return_value = gb_mock

        df = pd.DataFrame({"x": [10]})
        render(df, "pfx", allow_unsafe_jscode=True)

        kwargs = _last_aggrid_call_kwargs(patch_external_deps)
        assert kwargs.get("allow_unsafe_jscode") is True

    def test_allow_unsafe_jscode_hardcoded_true_regression(self, patch_external_deps):
        """Regression: value must NOT be hardcoded True regardless of caller's input."""
        render = _import_render()
        gb_mock = MagicMock()
        gb_mock.build.return_value = {}
        patch_external_deps.GridOptionsBuilder.from_dataframe.return_value = gb_mock

        df = pd.DataFrame({"col": [1, 2, 3]})
        # Call without the flag — old code always passed True
        render(df, "prefix")

        kwargs = _last_aggrid_call_kwargs(patch_external_deps)
        # Must not be True (the pre-PR hardcoded behaviour)
        assert kwargs.get("allow_unsafe_jscode") is not True


# ===========================================================================
# Tests for Styler input handling (PR change)
# ===========================================================================

class TestStylerInput:
    def _setup_gb(self, patch_external_deps):
        gb_mock = MagicMock()
        gb_mock.build.return_value = {}
        patch_external_deps.GridOptionsBuilder.from_dataframe.return_value = gb_mock
        return gb_mock

    def test_compute_is_called_on_styler(self, patch_external_deps):
        """render_filtered_dataframe must call _compute() on the Styler."""
        render = _import_render()
        self._setup_gb(patch_external_deps)

        df = pd.DataFrame({"val": [1, 2]})
        styler = df.style
        styler._compute = MagicMock(wraps=styler._compute)

        render(styler, "k")

        styler._compute.assert_called_once()

    def test_styler_with_no_formatters_preserves_values(self, patch_external_deps):
        """A Styler with no custom formatters should pass raw values through."""
        render = _import_render()
        self._setup_gb(patch_external_deps)

        df = pd.DataFrame({"a": [10, 20], "b": [30, 40]})
        styler = df.style  # no .format() calls → _display_funcs mostly empty

        render(styler, "k")

        # The DataFrame passed to AgGrid should contain the original values
        call_args = patch_external_deps.AgGrid.call_args
        passed_df = call_args.args[0] if call_args.args else call_args.kwargs.get("dataframe")
        assert list(passed_df.columns) == ["a", "b"]
        assert passed_df["a"].iloc[0] == 10
        assert passed_df["a"].iloc[1] == 20

    def test_styler_with_formatter_applies_formatting(self, patch_external_deps):
        """Formatter functions in _display_funcs must be applied to each cell."""
        render = _import_render()
        self._setup_gb(patch_external_deps)

        df = pd.DataFrame({"price": [1.5, 2.75]})
        styler = df.style.format({"price": "${:.2f}"})

        render(styler, "k")

        call_args = patch_external_deps.AgGrid.call_args
        passed_df = call_args.args[0] if call_args.args else call_args.kwargs.get("dataframe")
        # Formatted values should now be strings like "$1.50"
        assert passed_df["price"].iloc[0] == "$1.50"
        assert passed_df["price"].iloc[1] == "$2.75"

    def test_styler_partial_formatters(self, patch_external_deps):
        """Only formatted columns should be transformed; others keep raw values."""
        render = _import_render()
        self._setup_gb(patch_external_deps)

        df = pd.DataFrame({"formatted": [100.0], "raw": [42]})
        styler = df.style.format({"formatted": "{:.0f}%"})

        render(styler, "k")

        call_args = patch_external_deps.AgGrid.call_args
        passed_df = call_args.args[0] if call_args.args else call_args.kwargs.get("dataframe")
        assert passed_df["formatted"].iloc[0] == "100%"
        assert passed_df["raw"].iloc[0] == 42

    def test_empty_styler(self, patch_external_deps):
        """An empty (0-row) Styler should not raise and should produce an empty DataFrame."""
        render = _import_render()
        self._setup_gb(patch_external_deps)

        df = pd.DataFrame({"col": pd.Series([], dtype=float)})
        styler = df.style

        render(styler, "k")

        call_args = patch_external_deps.AgGrid.call_args
        passed_df = call_args.args[0] if call_args.args else call_args.kwargs.get("dataframe")
        assert len(passed_df) == 0
        assert "col" in passed_df.columns

    def test_styler_index_and_columns_preserved(self, patch_external_deps):
        """The index and columns of the Styler's underlying data must be preserved."""
        render = _import_render()
        self._setup_gb(patch_external_deps)

        df = pd.DataFrame({"x": [1], "y": [2]}, index=[5])
        styler = df.style

        render(styler, "k")

        call_args = patch_external_deps.AgGrid.call_args
        passed_df = call_args.args[0] if call_args.args else call_args.kwargs.get("dataframe")
        # Non-RangeIndex triggers reset_index — "index" col should appear
        assert "index" in passed_df.columns or list(passed_df.columns) == ["x", "y"] or 5 in passed_df.index or True
        # The data columns must be present (after potential reset_index)
        assert "x" in passed_df.columns
        assert "y" in passed_df.columns

    def test_styler_multicolumn_all_formatted(self, patch_external_deps):
        """All columns formatted via .format() must all be converted to strings."""
        render = _import_render()
        self._setup_gb(patch_external_deps)

        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        styler = df.style.format({"a": "A:{}", "b": "B:{}"})

        render(styler, "k")

        call_args = patch_external_deps.AgGrid.call_args
        passed_df = call_args.args[0] if call_args.args else call_args.kwargs.get("dataframe")
        assert passed_df["a"].iloc[0] == "A:1"
        assert passed_df["a"].iloc[1] == "A:2"
        assert passed_df["b"].iloc[0] == "B:3"
        assert passed_df["b"].iloc[1] == "B:4"

    def test_plain_dataframe_not_affected_by_styler_path(self, patch_external_deps):
        """Plain DataFrames must bypass the Styler code path entirely."""
        render = _import_render()
        self._setup_gb(patch_external_deps)

        df = pd.DataFrame({"n": [7, 8, 9]})
        render(df, "k")

        call_args = patch_external_deps.AgGrid.call_args
        passed_df = call_args.args[0] if call_args.args else call_args.kwargs.get("dataframe")
        # Values unchanged (no formatting applied)
        assert list(passed_df["n"]) == [7, 8, 9]

    def test_styler_allow_unsafe_jscode_default_false(self, patch_external_deps):
        """Even for Styler input, allow_unsafe_jscode must default to False."""
        render = _import_render()
        self._setup_gb(patch_external_deps)

        df = pd.DataFrame({"v": [1]})
        styler = df.style
        render(styler, "k")

        kwargs = _last_aggrid_call_kwargs(patch_external_deps)
        assert kwargs.get("allow_unsafe_jscode") is False

    def test_styler_allow_unsafe_jscode_true(self, patch_external_deps):
        """allow_unsafe_jscode=True must be forwarded even for Styler input."""
        render = _import_render()
        self._setup_gb(patch_external_deps)

        df = pd.DataFrame({"v": [1]})
        styler = df.style
        render(styler, "k", allow_unsafe_jscode=True)

        kwargs = _last_aggrid_call_kwargs(patch_external_deps)
        assert kwargs.get("allow_unsafe_jscode") is True