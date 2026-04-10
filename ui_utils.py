import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
from pandas.io.formats.style import Styler

def render_filtered_dataframe(df: pd.DataFrame, key_prefix: str, allow_unsafe_jscode: bool = False):
    """
    Render a Pandas DataFrame or Styler as an interactive AgGrid table with client-side filtering and sorting.
    
    This function copies and normalizes the input data (accepts a DataFrame or a pandas Styler), preserves non-RangeIndex labels by resetting the index, and serializes datetime and object columns to strings to ensure compatibility with AgGrid. It builds grid options with filtering, sorting, resizing, and column menus, injects minimal custom CSS, and returns an AgGrid component configured to return filtered and sorted data.
    
    Parameters:
        df (pd.DataFrame | pandas.io.formats.style.Styler): The data to display; if a Styler is provided its underlying DataFrame is used.
        key_prefix (str): Prefix used to build a stable Streamlit component key (final key is f"{key_prefix}_aggrid").
    
    Returns:
        AgGrid: An st_aggrid.AgGrid component instance showing the provided data, configured to return filtered and sorted rows.
    """
    # If the input is a Styler, extract the underlying dataframe and apply its formatters
    from pandas.io.formats.style import Styler
    if isinstance(df, Styler):
        data = df.data
        # _display_funcs is a dictionary mapping (row_index, col_index) to a formatter function
        # Compute the styled dataframe so that _display_funcs is fully populated
        df._compute()
        # Build a new dataframe with the formatted string values
        safe_df = pd.DataFrame(
            [[df._display_funcs.get((i, j), lambda x: x)(data.iloc[i,j]) for j in range(data.shape[1])] for i in range(data.shape[0])],
            index=data.index,
            columns=data.columns
        )
    else:
        safe_df = df.copy()

    # Reset index if it's not a standard RangeIndex so the index labels don't disappear in AgGrid
    if not isinstance(safe_df.index, pd.RangeIndex):
        safe_df = safe_df.reset_index()

    # 1. Brutal Serialization to un-break AgGrid JSON Parsing
    for col in safe_df.columns:
        if pd.api.types.is_datetime64_any_dtype(safe_df[col]):
            safe_df[col] = safe_df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
        elif getattr(safe_df[col], 'dtype', None) == 'object':
            safe_df[col] = safe_df[col].astype(str)

    # 2. Basic GridOptions
    gb = GridOptionsBuilder.from_dataframe(safe_df)
    gb.configure_default_column(
        filterable=True,
        sortable=True,
        resizable=True,
        # Enable column menus for the filtering/hamburger
        menuTabs=['filterMenuTab', 'generalMenuTab', 'columnsMenuTab']
    )
    # Removing selection mode to match st.dataframe's visual purity by default,
    # unless you explicitly want row selection checkboxes.
    # gb.configure_selection(selection_mode="single", use_checkbox=True)
    gridOptions = gb.build()

    # Custom CSS injection to ensure the iframe/ag-grid wrapper expands properly
    custom_css = {
        ".ag-root-wrapper": {"width": "100%", "height": "100%"},
        ".ag-header-cell-label": {"justify-content": "center"}
    }

    # 3. Component Rendering
    return AgGrid(
        safe_df,
        gridOptions=gridOptions,
        update_mode=GridUpdateMode.NO_UPDATE, # Changed from SELECTION/VALUE since we mainly want a view/filter replacement for st.dataframe
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        fit_columns_on_grid_load=False, # Disabled so columns don't crush into invisibility on wide datasets
        theme="alpine", # 'alpine' or 'streamlit' are generally safest in this version
        height=400,
        custom_css=custom_css,
        allow_unsafe_jscode=allow_unsafe_jscode,
        key=f"{key_prefix}_aggrid",
    )
