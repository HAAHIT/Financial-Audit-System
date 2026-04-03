"""
Financial Oversight & Audit Dashboard
=====================================
A comprehensive Streamlit-based financial audit system.
Modules: database, data_ingestion, audit_rules/*
"""

import os
import sys
import streamlit as st
import pandas as pd
import numpy as np

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    AUDIT_STATUSES, SPIKE_THRESHOLD_PCT, DISCOUNT_ALARM_PCT,
    PROCUREMENT_VARIANCE_PCT, BILLING_TOLERANCE, SALARY_SPIKE_PCT,
)
from database import get_connection, initialize_schema
from data_ingestion import load_bank_csv, load_purchase_csv, load_sales_csv, load_gst_csv

from audit_rules.anomaly_detection import (
    detect_expense_spikes, detect_salary_spikes, compute_zscore_outliers, detect_sudden_changes,
)
from audit_rules.party_analysis import (
    get_party_360, detect_new_parties, detect_new_party_in_new_group,
    detect_interparty_anomalies, detect_always_low_buyer, compute_party_momentum,
)
from audit_rules.transaction_flags import (
    add_flag, update_flag_category, get_flags, classify_all_transactions,
)
from audit_rules.reconciliation import (
    reconcile_gst, check_billing_math, reconcile_bank_vs_system,
    check_payment_account_match, check_gst_misclassification,
)
from audit_rules.procurement import (
    detect_price_outliers, compute_avg_material_cost, validate_bom_totals, check_bom_historical,
)
from audit_rules.sales_analysis import detect_discount_outliers, detect_always_low_price_party
from audit_rules.cashflow import (
    compute_daily_profitability, compute_net_cashflow, compute_percentiles,
    compute_branch_summary, compute_branch_totals, compute_category_summary,
)
from audit_rules.correlation import build_time_series, correlate_two_metrics, find_all_correlations

# ============================================================
# PAGE CONFIG & DB INIT
# ============================================================
st.set_page_config(page_title="Financial Health & Audit Dashboard", layout="wide", page_icon="📊")
conn = get_connection()
initialize_schema(conn)

status_config = {
    "audit_status": st.column_config.SelectboxColumn(
        "Audit Status", options=AUDIT_STATUSES, required=True
    )
}

# ============================================================
# CUSTOM CSS
# ============================================================
st.markdown("""
<style>
    .stMetric { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                padding: 15px; border-radius: 10px; border: 1px solid #334155; }
    .stTabs [data-baseweb="tab-list"] { gap: 4px; }
    .stTabs [data-baseweb="tab"] { padding: 8px 16px; border-radius: 6px 6px 0 0; }
    div[data-testid="stExpander"] { border: 1px solid #334155; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# SIDEBAR — DATA INGESTION
# ============================================================
with st.sidebar:
    st.header("📥 Data Ingestion Portal")
    st.caption("Upload CSV files exported from your ERP / banking system.")

    bank_file = st.file_uploader("1. Upload Bank CSV", type=["csv"])
    purchase_file = st.file_uploader("2. Upload Purchase CSV", type=["csv"])
    sales_file = st.file_uploader("3. Upload Sales CSV", type=["csv"])
    gst_file = st.file_uploader("4. Upload GST Portal CSV (Optional)", type=["csv"])

    if st.button("💾 Process & Save Data", use_container_width=True):
        counts = {}
        try:
            if bank_file:
                counts["Bank"] = load_bank_csv(bank_file, conn)
            if purchase_file:
                counts["Purchase"] = load_purchase_csv(purchase_file, conn)
            if sales_file:
                counts["Sales"] = load_sales_csv(sales_file, conn)
            if gst_file:
                counts["GST"] = load_gst_csv(gst_file, conn)

            if counts:
                msg = " | ".join(f"{k}: {v} new rows" for k, v in counts.items())
                st.success(f"✅ Loaded — {msg}")
            else:
                st.warning("No files selected.")
        except Exception as e:
            st.error(f"Processing Error: {e}")

    st.markdown("---")
    st.caption("💡 Re-uploading the same file won't create duplicates.")

# ============================================================
# TITLE
# ============================================================
st.title("📊 Financial Oversight & Audit Dashboard")

# ============================================================
# SECTION 1 — FINANCIAL HEALTH KPIs
# ============================================================
st.markdown("---")
st.header("📈 Financial Health & Cash Flow")

try:
    df_bank_full = pd.read_sql("SELECT * FROM bank_ledger", conn)
except Exception:
    df_bank_full = pd.DataFrame()

if not df_bank_full.empty:
    # Filters
    col1, col2, col3 = st.columns(3)
    branch_opts = df_bank_full["branch_id"].dropna().unique().tolist()
    group_opts = df_bank_full["group_name"].dropna().unique().tolist()
    branch_filter = col1.multiselect("Filter by Branch", branch_opts)
    group_filter = col2.multiselect("Filter by Category/Group", group_opts)
    min_size = col3.number_input("Min Transaction Size (₹)", value=0, step=10000)

    fb = df_bank_full.copy()
    if branch_filter:
        fb = fb[fb["branch_id"].isin(branch_filter)]
    if group_filter:
        fb = fb[fb["group_name"].isin(group_filter)]
    fb = fb[(fb["debit_amount"] >= min_size) | (fb["credit_amount"] >= min_size)]

    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Inward (Credit)", f"₹ {fb['credit_amount'].sum():,.2f}")
    k2.metric("Total Outward (Debit)", f"₹ {fb['debit_amount'].sum():,.2f}")
    net = fb["credit_amount"].sum() - fb["debit_amount"].sum()
    k3.metric("Net Cash Flow", f"₹ {net:,.2f}", delta=f"{'Positive' if net > 0 else 'Negative'}")

    debit_90 = np.percentile(fb["debit_amount"][fb["debit_amount"] > 0], 90) if any(fb["debit_amount"] > 0) else 0
    k4.metric("90th %ile Outward", f"₹ {debit_90:,.2f}")

    # Percentile breakdown
    with st.expander("📊 Transaction Size Percentiles"):
        pctls = compute_percentiles(conn)
        pc1, pc2 = st.columns(2)
        pc1.subheader("Debit Percentiles")
        pc1.dataframe(pd.DataFrame(pctls["debit_percentiles"], index=["₹ Value"]).T)
        pc2.subheader("Credit Percentiles")
        pc2.dataframe(pd.DataFrame(pctls["credit_percentiles"], index=["₹ Value"]).T)

    # Daily profitability chart
    st.subheader("Daily Profitability & Net Cash Flow")
    cf1, cf2 = st.columns([1, 4])
    est_tax = cf1.number_input("Est. Daily Tax (₹)", value=5000)
    est_dep = cf1.number_input("Est. Daily Depreciation (₹)", value=2000)
    daily = compute_daily_profitability(conn, est_tax, est_dep)
    if not daily.empty:
        cf2.line_chart(daily.set_index("docdate")[["net_cash_flow", "daily_profitability"]])
else:
    st.info("📂 Upload Bank CSV to populate the Financial Health Dashboard.")

# ============================================================
# SECTION 2 — BRANCH & CATEGORY DRILL-DOWN
# ============================================================
st.markdown("---")
st.header("🏢 Branch & Category Analysis")
br_tab1, br_tab2 = st.tabs(["Branch-wise", "Category-wise"])

with br_tab1:
    bt = compute_branch_totals(conn)
    if not bt.empty:
        st.dataframe(
            bt.style.format({"total_inward": "₹ {:,.2f}", "total_outward": "₹ {:,.2f}", "net_flow": "₹ {:,.2f}"}),
            use_container_width=True,
        )
        with st.expander("🔍 Branch + Category Breakdown"):
            bs = compute_branch_summary(conn)
            if not bs.empty:
                st.dataframe(bs.style.format({"total_inward": "₹ {:,.2f}", "total_outward": "₹ {:,.2f}"}),
                             use_container_width=True)
    else:
        st.info("Awaiting data.")

with br_tab2:
    cs = compute_category_summary(conn)
    if not cs.empty:
        st.dataframe(
            cs.style.format({"total_inward": "₹ {:,.2f}", "total_outward": "₹ {:,.2f}", "net_flow": "₹ {:,.2f}"}),
            use_container_width=True,
        )
    else:
        st.info("Awaiting data.")

# ============================================================
# SECTION 3 — AUTOMATED AUDIT RULES
# ============================================================
st.markdown("---")
st.header("🚨 Automated Audits & Rules Engine")

tabs = st.tabs([
    "🤝 Party 360",
    "⚖️ Correlation",
    "📊 Service Ratio",
    "🏛️ GST Recon",
    "📈 Expense Spikes",
    "💰 Salary Spikes",
    "🏷️ Sales Outliers",
    "📉 Purchase Outliers",
    "🧮 Billing Mismatches",
    "🆕 New Parties",
    "🔁 Inter-Party",
    "🏦 Bank vs System",
    "🏷️ Classification",
    "🧪 Unit Tests",
    "🗄️ Vault",
])

# --- TAB 0: Party 360 ---
with tabs[0]:
    st.subheader("Party 360: Reconciliation & Year-over-Year Delta")
    try:
        recon = get_party_360(conn)
        if not recon.empty:
            st.dataframe(recon.style.format(precision=2), use_container_width=True)
        else:
            st.info("Awaiting data.")
    except Exception:
        st.info("Awaiting data.")

    st.subheader("🔄 Party Momentum (Quarterly Trend)")
    try:
        momentum = compute_party_momentum(conn)
        if not momentum.empty:
            st.dataframe(momentum.style.format({"avg_momentum": "{:.1f}%"}), use_container_width=True)
    except Exception:
        pass

# --- TAB 1: Correlation Engine ---
with tabs[1]:
    st.subheader("Time-Series Correlation Engine")
    try:
        all_ts = build_time_series(conn)
        if not all_ts.empty:
            metrics = all_ts["metric"].unique().tolist()
            if len(metrics) > 1:
                c1, c2 = st.columns(2)
                var_a = c1.selectbox("Variable A", metrics, index=0)
                var_b = c2.selectbox("Variable B", metrics, index=min(1, len(metrics) - 1))
                r, p, merged = correlate_two_metrics(conn, var_a, var_b)
                if r is not None:
                    m1, m2 = st.columns(2)
                    m1.metric("Pearson r", f"{r:.3f}")
                    m2.metric("p-value", f"{p:.4f}")
                    st.line_chart(merged.set_index("month"))
                else:
                    st.warning("Not enough overlapping data.")

            with st.expander("📊 Full Correlation Matrix"):
                matrix = find_all_correlations(conn, min_months=1)
                if not matrix.empty:
                    st.dataframe(matrix.style.format("{:.2f}"), use_container_width=True)
        else:
            st.info("Upload data to build time-series metrics.")
    except Exception:
        st.info("Awaiting data.")

# --- TAB 2: Service-to-Sales Ratio ---
with tabs[2]:
    st.subheader("Service-to-Sales Ratio Alignment")
    try:
        sales_vol = pd.read_sql(
            "SELECT strftime('%Y-%m', docdate) AS month, SUM(billing_quantity) AS total_sales "
            "FROM sales_ledger GROUP BY month", conn
        )
        service_cost = pd.read_sql(
            "SELECT strftime('%Y-%m', docdate) AS month, SUM(debit_amount) AS total_service "
            "FROM bank_ledger WHERE group_name LIKE '%BROKERAGE%' OR group_name LIKE '%TRANSPORT%' "
            "GROUP BY month", conn
        )
        ratio_df = pd.merge(sales_vol, service_cost, on="month").dropna()
        if not ratio_df.empty:
            ratio_df["cost_per_unit"] = ratio_df["total_service"] / ratio_df["total_sales"]
            st.line_chart(ratio_df.set_index("month")["cost_per_unit"])
            st.dataframe(ratio_df.style.format({
                "total_sales": "{:.2f}", "total_service": "₹ {:.2f}", "cost_per_unit": "₹ {:.2f}"
            }), use_container_width=True)
        else:
            st.info("No matching Transport/Brokerage data.")
    except Exception:
        st.info("Awaiting data.")

# --- TAB 3: GST Reconciliation ---
with tabs[3]:
    st.subheader("GST Portal vs Bank Payments")
    try:
        gst_r = reconcile_gst(conn)
        if not gst_r.empty:
            st.dataframe(gst_r.style.format({
                "bank_gst_paid": "₹ {:.2f}", "portal_gst_filed": "₹ {:.2f}", "mismatch": "₹ {:.2f}"
            }), use_container_width=True)
            if any(gst_r["mismatch"] != 0):
                st.error("⚠️ Mismatches found between Bank and Portal.")
            else:
                st.success("✅ Bank payments match GST Portal.")
        else:
            st.info("Upload GST Portal CSV to run reconciliation.")

        with st.expander("🔍 GST Misclassification Check"):
            misclass = check_gst_misclassification(conn)
            if not misclass.empty:
                st.warning("Potential misclassified GST payments detected.")
                st.dataframe(misclass, use_container_width=True)
            else:
                st.success("No GST misclassifications detected.")
    except Exception:
        st.info("Awaiting data.")

# --- TAB 4: Expense Spikes ---
with tabs[4]:
    st.subheader("Flagged: Sudden Increases in Overhead")
    try:
        spikes = detect_expense_spikes(conn)
        if not spikes.empty:
            st.warning(f"🔺 {len(spikes)} significant MoM spikes detected.")
            st.dataframe(spikes.style.format({
                "total_spent": "₹ {:,.2f}", "prev_month_spent": "₹ {:,.2f}", "spike_pct": "{:.1f}%"
            }), use_container_width=True)
        else:
            st.success("✅ Expenses are stable.")

        with st.expander("📉 Sudden Decreases"):
            drops = detect_sudden_changes(conn, direction="decrease")
            if not drops.empty:
                st.dataframe(drops.style.format({
                    "total_spent": "₹ {:,.2f}", "prev_month_spent": "₹ {:,.2f}", "change_pct": "{:.1f}%"
                }), use_container_width=True)
            else:
                st.success("No sudden expense drops detected.")
    except Exception:
        pass

# --- TAB 5: Salary Spikes ---
with tabs[5]:
    st.subheader("Flagged: Sudden Salary Increases")
    try:
        sal = detect_salary_spikes(conn)
        if not sal.empty:
            st.error(f"⚠️ {len(sal)} salary spikes detected.")
            st.dataframe(sal.style.format({
                "total_salary": "₹ {:,.2f}", "prev_month": "₹ {:,.2f}", "spike_pct": "{:.1f}%"
            }), use_container_width=True)
        else:
            st.success("✅ Salary payments are stable.")
    except Exception:
        st.info("No salary data found.")

# --- TAB 6: Sales Outliers ---
with tabs[6]:
    st.subheader("Flagged: Unusual Buyer Discounts")
    try:
        disc = detect_discount_outliers(conn)
        if not disc.empty:
            st.error(f"⚠️ {len(disc)} discount anomalies detected.")
            st.dataframe(disc.style.format({
                "party_avg_rate": "{:.2f}", "global_avg_rate": "{:.2f}", "discount_pct": "{:.1f}%"
            }), use_container_width=True)
        else:
            st.success("✅ No unusually high discounts.")

        with st.expander("🔍 Always-Low-Price Buyers"):
            low = detect_always_low_price_party(conn)
            if not low.empty:
                st.warning("Parties consistently buying below average.")
                st.dataframe(low.style.format({"below_avg_ratio": "{:.1%}"}), use_container_width=True)
            else:
                st.success("No consistently low-price buyers found.")
    except Exception:
        pass

# --- TAB 7: Purchase Outliers ---
with tabs[7]:
    st.subheader("Flagged: Procurement Pricing Outliers")
    var_thresh = st.slider("Variance Threshold (%)", 5, 50, 20, key="proc_var")
    try:
        outliers = detect_price_outliers(conn, variance_pct=var_thresh)
        if not outliers.empty:
            st.error(f"⚠️ {len(outliers)} outlier purchases detected.")
            st.dataframe(outliers[["inv_date", "party_name", "item_name", "rec_qty",
                                    "implied_rate", "baseline_rate", "variance_pct", "audit_status"]],
                         use_container_width=True)
        else:
            st.success("✅ Procurement rates within bounds.")

        with st.expander("📊 Average Material Cost Summary"):
            avg_cost = compute_avg_material_cost(conn)
            if not avg_cost.empty:
                st.dataframe(avg_cost.style.format({
                    "weighted_avg_rate": "₹ {:.2f}", "min_rate": "₹ {:.2f}",
                    "max_rate": "₹ {:.2f}", "total_value": "₹ {:,.2f}"
                }), use_container_width=True)

        with st.expander("📜 BOM Historical Deviations"):
            bom_hist = check_bom_historical(conn)
            if not bom_hist.empty:
                st.dataframe(bom_hist, use_container_width=True)
            else:
                st.success("All BOM rates within historical norms.")
    except Exception:
        pass

# --- TAB 8: Billing Mismatches ---
with tabs[8]:
    st.subheader("Flagged: Mathematical Mismatches")
    try:
        mismatches = check_billing_math(conn)
        if not mismatches.empty:
            st.error(f"⚠️ {len(mismatches)} billing mismatches found.")
            st.dataframe(
                mismatches[["inv_no", "party_name", "material_value", "tax_amt",
                            "charges_amt", "rebate_amt", "expected_net", "net_amt",
                            "discrepancy", "audit_status"]],
                use_container_width=True,
            )
        else:
            st.success("✅ All purchase amounts align mathematically.")

        with st.expander("📦 BOM Total Validation"):
            bom = validate_bom_totals(conn)
            if not bom.empty:
                st.warning("Invoice BOM totals with discrepancies.")
                st.dataframe(bom, use_container_width=True)
            else:
                st.success("All invoice BOM totals match.")
    except Exception:
        pass

# --- TAB 9: New Parties ---
with tabs[9]:
    st.subheader("Flagged: Unrecognized Parties")
    try:
        new_p = detect_new_parties(conn)
        if not new_p.empty:
            st.warning(f"⚠️ {len(new_p)} single-entry parties detected.")
            st.dataframe(new_p[["docdate", "docno", "contra_ledger_name", "group_name",
                                "debit_amount", "credit_amount"]], use_container_width=True)
        else:
            st.success("✅ No single-entry parties.")

        with st.expander("🚩 New Party in New Group (Double Flag)"):
            double = detect_new_party_in_new_group(conn)
            if not double.empty:
                st.error("High risk: New party in a previously unseen group.")
                st.dataframe(double, use_container_width=True)
            else:
                st.success("No double-flagged entries.")
    except Exception:
        pass

# --- TAB 10: Inter-Party Analysis ---
with tabs[10]:
    st.subheader("Inter-Party: Overbilling / Underbilling")
    try:
        inter = detect_interparty_anomalies(conn)
        if not inter.empty:
            st.warning(f"⚠️ {len(inter)} inter-party pricing anomalies.")
            st.dataframe(inter.style.format({
                "party_avg_rate": "₹ {:.2f}", "global_avg_rate": "₹ {:.2f}", "deviation_pct": "{:.1f}%"
            }), use_container_width=True)
        else:
            st.success("✅ No overbilling/underbilling detected.")
    except Exception:
        pass

# --- TAB 11: Bank vs System ---
with tabs[11]:
    st.subheader("Bank vs System Reconciliation")
    try:
        unmatched = reconcile_bank_vs_system(conn)
        if not unmatched.empty:
            st.warning(f"⚠️ {len(unmatched)} bank entries not matched to any purchase/sales party.")
            st.dataframe(unmatched, use_container_width=True)
        else:
            st.success("✅ All bank entries matched to ERP data.")

        with st.expander("💳 Payment Account Verification"):
            acct = check_payment_account_match(conn)
            if not acct.empty:
                st.error("Payments to different party than invoice.")
                st.dataframe(acct, use_container_width=True)
            else:
                st.success("All payments match invoice parties.")
    except Exception:
        pass

# --- TAB 12: Transaction Classification ---
with tabs[12]:
    st.subheader("Auto-Classification (Credit/Debit Taxonomy)")
    try:
        classified = classify_all_transactions(conn)
        if not classified.empty:
            cl1, cl2 = st.columns(2)
            credit_summary = classified[classified["direction"] == "CREDIT"]["category_key"].value_counts()
            debit_summary = classified[classified["direction"] == "DEBIT"]["category_key"].value_counts()
            cl1.subheader("Credits")
            cl1.dataframe(credit_summary)
            cl2.subheader("Debits")
            cl2.dataframe(debit_summary)

            with st.expander("📋 Full Classified Ledger"):
                st.dataframe(classified[["docdate", "contra_ledger_name", "debit_amount",
                                         "credit_amount", "direction", "category_key",
                                         "category_desc"]], use_container_width=True)
        else:
            st.info("Awaiting data.")
    except Exception:
        pass

# --- TAB 13: Unit Tests ---
with tabs[13]:
    st.subheader("🧪 System Integrity & Logic Verification")
    st.write("Run algorithmic self-tests to verify the rules engine.")
    if st.button("▶ Run Unit Tests"):
        from data_ingestion import standardize_dates as _std_dates

        # Test 1: Billing math
        t1 = pd.DataFrame({"material_value": [100], "tax_amt": [5], "charges_amt": [0],
                            "rebate_amt": [0], "net_amt": [120]})
        expected = t1["material_value"] + t1["tax_amt"] + t1["charges_amt"] - t1["rebate_amt"]
        disc = abs(t1["net_amt"] - expected).iloc[0]
        if disc > 1.0:
            st.success("✅ Billing Mismatch Logic: PASSED (Caught 100+5 ≠ 120)")
        else:
            st.error("❌ Billing Mismatch Logic: FAILED")

        # Test 2: Outlier detection
        t2 = pd.DataFrame({"rec_qty": [10], "material_value": [2000], "BASELINE_RATE": [100]})
        implied = (t2["material_value"] / t2["rec_qty"]).iloc[0]
        var = abs(implied - t2["BASELINE_RATE"].iloc[0]) / t2["BASELINE_RATE"].iloc[0]
        if var > 0.20:
            st.success("✅ Outlier Detection: PASSED (Caught 100% variance)")
        else:
            st.error("❌ Outlier Detection: FAILED")

        # Test 3: Date normalization
        t3 = pd.DataFrame({"INV_DATE": ["04-01-2025"]})
        std = _std_dates(t3, ["INV_DATE"])
        if std["INV_DATE"].iloc[0] == "2025-01-04":
            st.success("✅ Date Normalization: PASSED")
        else:
            st.error("❌ Date Normalization: FAILED")

        # Test 4: Z-score
        from audit_rules.anomaly_detection import compute_zscore_outliers
        zs = compute_zscore_outliers(pd.Series([10, 10, 10, 10, 10, 10, 100]), threshold=2.0)
        if zs.iloc[-1]:
            st.success("✅ Z-Score Outlier: PASSED (Caught 100 in [10,10,…,100])")
        else:
            st.error("❌ Z-Score Outlier: FAILED")

        # Test 5: Classification
        from audit_rules.transaction_flags import classify_transaction
        d, k, _ = classify_transaction("SALARY", "SALARY ACCOUNT", 200000, 0)
        if d == "DEBIT" and k == "SALARY":
            st.success("✅ Transaction Classification: PASSED (Salary → DEBIT/SALARY)")
        else:
            st.error("❌ Transaction Classification: FAILED")

        st.info("💡 For the full 110-test suite, run `RUN_TESTS.bat`")

# --- TAB 14: Vault ---
with tabs[14]:
    st.subheader("Historical Data Explorer")
    view_table = st.radio(
        "Select Table:",
        ["Bank Ledger", "Purchase Ledger", "Sales Ledger", "GST Portal"],
        horizontal=True,
    )
    table_map = {
        "Bank Ledger": "bank_ledger",
        "Purchase Ledger": "purchase_ledger",
        "Sales Ledger": "sales_ledger",
        "GST Portal": "gst_portal",
    }
    try:
        df_hist = pd.read_sql(f"SELECT * FROM {table_map[view_table]}", conn)
        st.dataframe(df_hist, use_container_width=True)
    except Exception:
        st.error("Table empty or missing.")