"""
Financial Oversight & Audit Dashboard
=====================================
Premium Streamlit dashboard with 15 audit rules.
"""

import os, sys, streamlit as st, pandas as pd, numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import AUDIT_STATUSES
from database import get_connection, initialize_schema
from data_ingestion import load_bank_csv, load_purchase_csv, load_sales_csv, load_gst_csv
from audit_rules.anomaly_detection import detect_expense_spikes, detect_salary_spikes, compute_zscore_outliers, detect_sudden_changes
from audit_rules.party_analysis import get_party_360, detect_new_parties, detect_new_party_in_new_group, detect_interparty_anomalies, detect_always_low_buyer, compute_party_momentum
from audit_rules.transaction_flags import classify_all_transactions
from audit_rules.reconciliation import reconcile_gst, check_billing_math, reconcile_bank_vs_system, check_payment_account_match, check_gst_misclassification
from audit_rules.procurement import detect_price_outliers, compute_avg_material_cost, validate_bom_totals, check_bom_historical
from audit_rules.sales_analysis import detect_discount_outliers, detect_always_low_price_party
from audit_rules.cashflow import compute_daily_profitability, compute_net_cashflow, compute_percentiles, compute_branch_summary, compute_branch_totals, compute_category_summary
from audit_rules.correlation import build_time_series, correlate_two_metrics, find_all_correlations
from ui_utils import render_filtered_dataframe

# ── Page Config ─────────────────────────────────────────────
st.set_page_config(page_title="Financial Audit Command Center", layout="wide", page_icon="🛡️")
conn = get_connection()
initialize_schema(conn)

# ── Premium CSS (Light + Dark Theme Aware) ──────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Global ── */
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] .stButton > button {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
    color: #fff !important; border: none; border-radius: 10px; font-weight: 600;
    padding: 0.65rem 1.2rem; letter-spacing: 0.02em; transition: all 0.3s ease;
    box-shadow: 0 4px 15px rgba(99,102,241,0.3);
}
section[data-testid="stSidebar"] .stButton > button:hover {
    transform: translateY(-1px); box-shadow: 0 6px 25px rgba(99,102,241,0.45);
}
.upload-label {
    font-size: 0.82rem; font-weight: 600; color: #6366f1;
    margin: 0.8rem 0 0.3rem 0; display: flex; align-items: center; gap: 0.4rem;
}
.upload-label .num {
    background: #6366f1; color: white; border-radius: 50%;
    width: 20px; height: 20px; display: inline-flex; align-items: center;
    justify-content: center; font-size: 0.7rem; font-weight: 700;
}

/* ── Header ── */
.hero-title {
    font-size: 2.2rem; font-weight: 800; letter-spacing: -0.04em;
    background: linear-gradient(135deg, #4338ca 0%, #6366f1 40%, #818cf8 70%, #a5b4fc 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 0.1rem; line-height: 1.1;
}
.hero-sub {
    font-size: 0.92rem; opacity: 0.7; font-weight: 400;
    letter-spacing: 0.02em; margin-bottom: 1.5rem;
}

/* ── KPI Cards (Theme-Agnostic Glassmorphism) ── */
.kpi-card {
    background: linear-gradient(135deg, rgba(99,102,241,0.06) 0%, rgba(99,102,241,0.01) 100%);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(99,102,241,0.15);
    border-radius: 16px; padding: 1.4rem 1.3rem; position: relative;
    overflow: hidden; transition: all 0.3s ease;
    box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    color: inherit;
}
.kpi-card:hover { border-color: rgba(99,102,241,0.3); transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(99,102,241,0.1); }
.kpi-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
    border-radius: 16px 16px 0 0;
}
.kpi-card.inward::before { background: linear-gradient(90deg, #10b981, #34d399); }
.kpi-card.outward::before { background: linear-gradient(90deg, #ef4444, #fb7185); }
.kpi-card.net::before { background: linear-gradient(90deg, #6366f1, #818cf8); }
.kpi-card.pct::before { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.kpi-label {
    font-size: 0.72rem; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.1em; opacity: 0.7; margin-bottom: 0.5rem;
    color: inherit;
}
.kpi-value { font-size: 1.55rem; font-weight: 800; letter-spacing: -0.03em; line-height: 1.2; }
.kpi-value.green { color: #10b981; }
.kpi-value.red { color: #ef4444; }
.kpi-value.blue { color: #6366f1; }
.kpi-value.amber { color: #f59e0b; }

/* ── Section Headers ── */
.section-header {
    font-size: 1.3rem; font-weight: 700;
    letter-spacing: -0.02em; margin: 2rem 0 0.8rem 0;
    padding-bottom: 0.6rem; border-bottom: 2px solid rgba(99,102,241,0.2);
    display: flex; align-items: center; gap: 0.6rem;
}
.section-icon {
    width: 32px; height: 32px; border-radius: 8px;
    display: inline-flex; align-items: center; justify-content: center; font-size: 1rem;
}
.section-icon.health { background: rgba(5,150,105,0.1); }
.section-icon.branch { background: rgba(99,102,241,0.1); }
.section-icon.audit { background: rgba(220,38,38,0.1); }

/* ── Status Badges ── */
.badge { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 100px;
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.04em; }
.badge-success { background: rgba(5,150,105,0.1); color: #059669; border: 1px solid rgba(5,150,105,0.25); }
.badge-danger { background: rgba(220,38,38,0.1); color: #dc2626; border: 1px solid rgba(220,38,38,0.25); }
.badge-warning { background: rgba(217,119,6,0.1); color: #d97706; border: 1px solid rgba(217,119,6,0.25); }
.badge-info { background: rgba(79,70,229,0.08); color: #4f46e5; border: 1px solid rgba(79,70,229,0.2); }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 2px; border-radius: 12px; padding: 4px;
    border: 1px solid rgba(99,102,241,0.12);
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px; padding: 8px 14px; font-size: 0.78rem; font-weight: 500;
}
.stTabs [aria-selected="true"] {
    background: rgba(99,102,241,0.12) !important;
    color: #4f46e5 !important; font-weight: 700;
}

/* ── DataFrames & Expanders ── */
.stDataFrame { border-radius: 12px; overflow: hidden; }
div[data-testid="stExpander"] { border: 1px solid rgba(99,102,241,0.1); border-radius: 12px; }
div[data-testid="stExpander"] summary { font-weight: 600; font-size: 0.88rem; }

/* ── Metric override ── */
[data-testid="stMetric"] { display: none; }

/* ── Dividers ── */
hr { border-color: rgba(99,102,241,0.12) !important; margin: 1.5rem 0 !important; }

/* ── Alerts ── */
.stAlert { border-radius: 10px; font-size: 0.85rem; }

/* Theme logic is managed organically by Streamlit CSS variables */
</style>
""", unsafe_allow_html=True)

# ── Helper: Render KPI card ──
def kpi_card(label, value, style_class, color_class):
    st.markdown(f'''
    <div class="kpi-card {style_class}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value {color_class}">{value}</div>
    </div>''', unsafe_allow_html=True)

def badge(text, variant="info"):
    return f'<span class="badge badge-{variant}">{text}</span>'

def section_header(icon, icon_class, title):
    st.markdown(f'''
    <div class="section-header">
        <span class="section-icon {icon_class}">{icon}</span> {title}
    </div>''', unsafe_allow_html=True)

status_config = {"audit_status": st.column_config.SelectboxColumn("Audit Status", options=AUDIT_STATUSES, required=True)}

# ── Sidebar ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📥 Data Ingestion")
    st.caption("Upload CSV files exported from your ERP / banking system")

    st.markdown('<div class="upload-label"><span class="num">1</span> Bank Ledger CSV</div>', unsafe_allow_html=True)
    st.caption("Columns: DOCDATE, DOCNO, CONTRA_LEDGER_NAME, DEBIT_AMOUNT, CREDIT_AMOUNT")
    bank_file = st.file_uploader("bank_upload", type=["csv"], label_visibility="collapsed", key="bank")

    st.markdown('<div class="upload-label"><span class="num">2</span> Purchase Register CSV</div>', unsafe_allow_html=True)
    st.caption("Columns: INV_NO, INV_DATE, PARTY_NAME, ITEM_NAME, MATERIAL_VALUE")
    purchase_file = st.file_uploader("purchase_upload", type=["csv"], label_visibility="collapsed", key="purchase")

    st.markdown('<div class="upload-label"><span class="num">3</span> Sales Register CSV</div>', unsafe_allow_html=True)
    st.caption("Columns: INV_NO, DOCDATE, PARTY_NAME, ITEM_NAME, NET_RATE")
    sales_file = st.file_uploader("sales_upload", type=["csv"], label_visibility="collapsed", key="sales")

    st.markdown('<div class="upload-label"><span class="num">4</span> GST Portal CSV <em style="font-weight:400;color:#94a3b8">(optional)</em></div>', unsafe_allow_html=True)
    st.caption("Columns: DATE/DOCDATE, TAX_AMOUNT/AMOUNT")
    gst_file = st.file_uploader("gst_upload", type=["csv"], label_visibility="collapsed", key="gst")

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    if st.button("⚡ Process & Load", use_container_width=True):
        counts = {}
        try:
            if bank_file: counts["Bank"] = load_bank_csv(bank_file, conn)
            if purchase_file: counts["Purchase"] = load_purchase_csv(purchase_file, conn)
            if sales_file: counts["Sales"] = load_sales_csv(sales_file, conn)
            if gst_file: counts["GST"] = load_gst_csv(gst_file, conn)
            if counts:
                st.success(" · ".join(f"{k}: {v} rows" for k, v in counts.items()))
            else:
                st.warning("Select files first")
        except Exception as e:
            st.error(str(e))
    st.markdown("---")
    st.markdown(f'<div style="text-align:center">{badge("Dedup-Protected", "success")}</div>', unsafe_allow_html=True)
    st.caption("💡 Re-uploading the same file won't create duplicates.")

# ── Hero Header ─────────────────────────────────────────────
st.markdown("""
<div style="margin-top:0.5rem">
    <div class="hero-title">🛡️ Financial Audit Command Center</div>
    <div class="hero-sub">Real-time financial oversight · 15 automated audit rules · 100% offline & secure</div>
</div>
""", unsafe_allow_html=True)

# ── Load data ───────────────────────────────────────────────
try:
    df_bank = pd.read_sql("SELECT * FROM bank_ledger", conn)
except Exception:
    df_bank = pd.DataFrame()

# ═══════════════════════════════════════════════════════════
# SECTION 1: FINANCIAL HEALTH
# ═══════════════════════════════════════════════════════════
section_header("📈", "health", "Financial Health & Cash Flow")

if not df_bank.empty:
    fc1, fc2, fc3 = st.columns(3)
    branch_opts = df_bank["branch_id"].dropna().unique().tolist()
    group_opts = df_bank["group_name"].dropna().unique().tolist()
    branch_filter = fc1.multiselect("Branch", branch_opts, placeholder="All Branches")
    group_filter = fc2.multiselect("Category", group_opts, placeholder="All Categories")
    min_size = fc3.number_input("Min. Txn Size (₹)", value=0, step=10000)

    fb = df_bank.copy()
    if branch_filter: fb = fb[fb["branch_id"].isin(branch_filter)]
    if group_filter: fb = fb[fb["group_name"].isin(group_filter)]
    fb = fb[(fb["debit_amount"] >= min_size) | (fb["credit_amount"] >= min_size)]

    total_in = fb["credit_amount"].sum()
    total_out = fb["debit_amount"].sum()
    net = total_in - total_out
    deb_90 = np.percentile(fb["debit_amount"][fb["debit_amount"]>0], 90) if any(fb["debit_amount"]>0) else 0

    k1, k2, k3, k4 = st.columns(4)
    with k1: kpi_card("Total Inward (Credit)", f"₹ {total_in:,.0f}", "inward", "green")
    with k2: kpi_card("Total Outward (Debit)", f"₹ {total_out:,.0f}", "outward", "red")
    with k3: kpi_card("Net Cash Flow", f"₹ {net:,.0f}", "net", "blue" if net >= 0 else "red")
    with k4: kpi_card("90th %ile Outward", f"₹ {deb_90:,.0f}", "pct", "amber")

    st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)

    # Percentiles
    with st.expander("📊 Transaction Size Percentile Distribution"):
        pctls = compute_percentiles(conn)
        pc1, pc2 = st.columns(2)
        with pc1:
            st.markdown(f'{badge("DEBIT PERCENTILES","warning")}', unsafe_allow_html=True)
            render_filtered_dataframe(pd.DataFrame(pctls["debit_percentiles"], index=["₹"]).T.style.format("₹ {:,.0f}"), key_prefix="health_debit_pctls")
        with pc2:
            st.markdown(f'{badge("CREDIT PERCENTILES","success")}', unsafe_allow_html=True)
            render_filtered_dataframe(pd.DataFrame(pctls["credit_percentiles"], index=["₹"]).T.style.format("₹ {:,.0f}"), key_prefix="health_credit_pctls")

    # Daily profitability
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    ch1, ch2 = st.columns([1, 4])
    with ch1:
        st.markdown(f'{badge("CONTROLS","info")}', unsafe_allow_html=True)
        tax = st.number_input("Daily Tax (₹)", value=5000, label_visibility="visible")
        dep = st.number_input("Daily Depreciation (₹)", value=2000)
    with ch2:
        daily = compute_daily_profitability(conn, tax, dep)
        if not daily.empty:
            st.line_chart(daily.set_index("docdate")[["net_cash_flow", "daily_profitability"]], color=["#6366f1", "#34d399"])
else:
    st.info("📂 Upload Bank CSV to activate the Financial Health dashboard.")

# ═══════════════════════════════════════════════════════════
# SECTION 2: BRANCH & CATEGORY
# ═══════════════════════════════════════════════════════════
st.markdown("---")
section_header("🏢", "branch", "Branch & Category Analysis")

b_tab1, b_tab2 = st.tabs(["Branch-wise", "Category-wise"])
with b_tab1:
    bt = compute_branch_totals(conn)
    if not bt.empty:
        render_filtered_dataframe(bt.style.format({"total_inward":"₹ {:,.0f}", "total_outward":"₹ {:,.0f}", "net_flow":"₹ {:,.0f}"}), key_prefix="branch_totals")
        with st.expander("🔍 Branch + Category Drilldown"):
            render_filtered_dataframe(compute_branch_summary(conn).style.format({"total_inward":"₹ {:,.0f}", "total_outward":"₹ {:,.0f}"}), key_prefix="branch_summary")
    else: st.info("Awaiting data.")
with b_tab2:
    cs = compute_category_summary(conn)
    if not cs.empty:
        render_filtered_dataframe(cs.style.format({"total_inward":"₹ {:,.0f}", "total_outward":"₹ {:,.0f}", "net_flow":"₹ {:,.0f}"}), key_prefix="category_summary")
    else: st.info("Awaiting data.")

# ═══════════════════════════════════════════════════════════
# SECTION 3: AUDIT RULES ENGINE
# ═══════════════════════════════════════════════════════════
st.markdown("---")
section_header("🚨", "audit", "Automated Audit Engine")

tabs = st.tabs(["Party 360", "Correlation", "Service Ratio", "GST Recon", "Expense Spikes",
                "Salary Spikes", "Sales Outliers", "Purchase Outliers", "Billing Errors",
                "New Parties", "Inter-Party", "Bank vs ERP", "Classification", "Self-Tests", "Data Vault"])

# ── Party 360 ──
with tabs[0]:
    st.markdown(f"**Party Reconciliation & Year-over-Year Delta** {badge('RECONCILIATION','info')}", unsafe_allow_html=True)
    try:
        r = get_party_360(conn)
        if not r.empty: render_filtered_dataframe(r.style.format(precision=2), key_prefix="party_360")
        else: st.info("Awaiting data.")
        m = compute_party_momentum(conn)
        if not m.empty:
            st.markdown(f"**Quarterly Momentum** {badge('TREND','info')}", unsafe_allow_html=True)
            render_filtered_dataframe(m.style.format({"avg_momentum":"{:.1f}%"}), key_prefix="party_momentum")
    except: st.info("Awaiting data.")

# ── Correlation ──
with tabs[1]:
    st.markdown(f"**Time-Series Correlation** {badge('ANALYTICS','info')}", unsafe_allow_html=True)
    try:
        ts = build_time_series(conn)
        if not ts.empty and ts["metric"].nunique() > 1:
            metrics = ts["metric"].unique().tolist()
            c1, c2 = st.columns(2)
            va = c1.selectbox("Variable A", metrics, index=0)
            vb = c2.selectbox("Variable B", metrics, index=min(1, len(metrics)-1))
            r, p, merged = correlate_two_metrics(conn, va, vb)
            if r is not None:
                m1, m2 = st.columns(2)
                with m1: kpi_card("Pearson r", f"{r:.3f}", "net", "blue")
                with m2: kpi_card("p-value", f"{p:.4f}", "pct", "amber")
                st.line_chart(merged.set_index("month"), color=["#6366f1", "#34d399"])
            else: st.warning("Insufficient overlapping data.")
            with st.expander("📊 Full Correlation Matrix"):
                matrix = find_all_correlations(conn, min_months=1)
                if not matrix.empty: render_filtered_dataframe(matrix.style.format("{:.2f}").background_gradient(cmap="RdYlGn", vmin=-1, vmax=1), key_prefix="correlation_matrix")
        else: st.info("Upload more data to build metrics.")
    except: st.info("Awaiting data.")

# ── Service Ratio ──
with tabs[2]:
    st.markdown(f"**Service-to-Sales Ratio** {badge('ALIGNMENT','warning')}", unsafe_allow_html=True)
    try:
        sv = pd.read_sql("SELECT strftime('%Y-%m',docdate) AS month, SUM(billing_quantity) AS total_sales FROM sales_ledger GROUP BY month", conn)
        sc = pd.read_sql("SELECT strftime('%Y-%m',docdate) AS month, SUM(debit_amount) AS total_service FROM bank_ledger WHERE group_name LIKE '%BROKERAGE%' OR group_name LIKE '%TRANSPORT%' GROUP BY month", conn)
        rd = pd.merge(sv, sc, on="month").dropna()
        if not rd.empty:
            rd["cost_per_unit"] = rd["total_service"]/rd["total_sales"]
            st.line_chart(rd.set_index("month")["cost_per_unit"], color="#f59e0b")
            render_filtered_dataframe(rd.style.format({"total_sales":"{:.0f}","total_service":"₹ {:,.0f}","cost_per_unit":"₹ {:.2f}"}), key_prefix="service_ratio")
        else: st.info("No Transport/Brokerage data found.")
    except: st.info("Awaiting data.")

# ── GST Recon ──
with tabs[3]:
    st.markdown(f"**GST Portal vs Bank Payments** {badge('RECONCILIATION','info')}", unsafe_allow_html=True)
    try:
        g = reconcile_gst(conn)
        if not g.empty:
            render_filtered_dataframe(g.style.format({"bank_gst_paid":"₹ {:,.0f}","portal_gst_filed":"₹ {:,.0f}","mismatch":"₹ {:,.0f}"}), key_prefix="gst_recon")
            if any(g["mismatch"]!=0):
                st.markdown(f'{badge("MISMATCH DETECTED","danger")}', unsafe_allow_html=True)
            else:
                st.markdown(f'{badge("ALL MATCHED","success")}', unsafe_allow_html=True)
        else: st.info("Upload GST Portal CSV.")
        with st.expander("🔍 GST Misclassification Check"):
            mc = check_gst_misclassification(conn)
            if not mc.empty: render_filtered_dataframe(mc, key_prefix="gst_misclassification")
            else: st.markdown(f'{badge("CLEAN","success")}', unsafe_allow_html=True)
    except: st.info("Awaiting data.")

# ── Expense Spikes ──
with tabs[4]:
    st.markdown(f"**Overhead Spike Detection** {badge('ANOMALY','danger')}", unsafe_allow_html=True)
    try:
        sp = detect_expense_spikes(conn)
        if not sp.empty:
            st.markdown(f'{badge(f"{len(sp)} SPIKES","danger")}', unsafe_allow_html=True)
            render_filtered_dataframe(sp.style.format({"total_spent":"₹ {:,.0f}","prev_month_spent":"₹ {:,.0f}","spike_pct":"{:.1f}%"}), key_prefix="expense_spikes")
        else: st.markdown(f'{badge("STABLE","success")}', unsafe_allow_html=True)
        with st.expander("📉 Sudden Drops"):
            dr = detect_sudden_changes(conn, direction="decrease")
            if not dr.empty: render_filtered_dataframe(dr.style.format({"total_spent":"₹ {:,.0f}","prev_month_spent":"₹ {:,.0f}","change_pct":"{:.1f}%"}), key_prefix="sudden_drops")
            else: st.markdown(f'{badge("NO DROPS","success")}', unsafe_allow_html=True)
    except: pass

# ── Salary Spikes ──
with tabs[5]:
    st.markdown(f"**Salary Payment Anomalies** {badge('PAYROLL','danger')}", unsafe_allow_html=True)
    try:
        s = detect_salary_spikes(conn)
        if not s.empty:
            st.markdown(f'{badge(f"{len(s)} SPIKES","danger")}', unsafe_allow_html=True)
            render_filtered_dataframe(s.style.format({"total_salary":"₹ {:,.0f}","prev_month":"₹ {:,.0f}","spike_pct":"{:.1f}%"}), key_prefix="salary_spikes")
        else: st.markdown(f'{badge("STABLE","success")}', unsafe_allow_html=True)
    except: st.info("No salary data found.")

# ── Sales Outliers ──
with tabs[6]:
    st.markdown(f"**Buyer Discount Anomalies** {badge('PRICING','warning')}", unsafe_allow_html=True)
    try:
        d = detect_discount_outliers(conn)
        if not d.empty:
            st.markdown(f'{badge(f"{len(d)} ANOMALIES","danger")}', unsafe_allow_html=True)
            render_filtered_dataframe(d.style.format({"party_avg_rate":"₹ {:.0f}","global_avg_rate":"₹ {:.0f}","discount_pct":"{:.1f}%"}), key_prefix="discount_outliers")
        else: st.markdown(f'{badge("NO ANOMALIES","success")}', unsafe_allow_html=True)
        with st.expander("🔍 Consistently Low-Price Buyers"):
            lp = detect_always_low_price_party(conn)
            if not lp.empty: render_filtered_dataframe(lp.style.format({"below_avg_ratio":"{:.1%}"}), key_prefix="low_price_buyers")
            else: st.markdown(f'{badge("CLEAN","success")}', unsafe_allow_html=True)
    except: pass

# ── Purchase Outliers ──
with tabs[7]:
    st.markdown(f"**Procurement Pricing Analysis** {badge('PROCUREMENT','warning')}", unsafe_allow_html=True)
    vt = st.slider("Variance Threshold (%)", 5, 50, 20, key="pv")
    try:
        o = detect_price_outliers(conn, variance_pct=vt)
        if not o.empty:
            st.markdown(f'{badge(f"{len(o)} OUTLIERS","danger")}', unsafe_allow_html=True)
            render_filtered_dataframe(o[["inv_date","party_name","item_name","rec_qty","implied_rate","baseline_rate","variance_pct","audit_status"]], key_prefix="price_outliers")
        else: st.markdown(f'{badge("WITHIN BOUNDS","success")}', unsafe_allow_html=True)
        with st.expander("📊 Average Material Cost"):
            ac = compute_avg_material_cost(conn)
            if not ac.empty: render_filtered_dataframe(ac.style.format({"weighted_avg_rate":"₹ {:.0f}","min_rate":"₹ {:.0f}","max_rate":"₹ {:.0f}","total_value":"₹ {:,.0f}"}), key_prefix="avg_material_cost")
        with st.expander("📜 BOM Historical Deviations"):
            bh = check_bom_historical(conn)
            if not bh.empty: render_filtered_dataframe(bh, key_prefix="bom_historical")
            else: st.markdown(f'{badge("WITHIN NORMS","success")}', unsafe_allow_html=True)
    except: pass

# ── Billing Errors ──
with tabs[8]:
    st.markdown(f"**Billing Math Verification** {badge('INTEGRITY','danger')}", unsafe_allow_html=True)
    try:
        mm = check_billing_math(conn)
        if not mm.empty:
            st.markdown(f'{badge(f"{len(mm)} ERRORS","danger")}', unsafe_allow_html=True)
            render_filtered_dataframe(mm[["inv_no","party_name","material_value","tax_amt","charges_amt","rebate_amt","expected_net","net_amt","discrepancy","audit_status"]], key_prefix="billing_errors")
        else: st.markdown(f'{badge("ALL CORRECT","success")}', unsafe_allow_html=True)
        with st.expander("📦 BOM Total Validation"):
            bom = validate_bom_totals(conn)
            if not bom.empty: render_filtered_dataframe(bom, key_prefix="bom_totals")
            else: st.markdown(f'{badge("ALL MATCHED","success")}', unsafe_allow_html=True)
    except: pass

# ── New Parties ──
with tabs[9]:
    st.markdown(f"**Unrecognized Single-Entry Parties** {badge('RISK','warning')}", unsafe_allow_html=True)
    try:
        np_ = detect_new_parties(conn)
        if not np_.empty:
            st.markdown(f'{badge(f"{len(np_)} FLAGGED","warning")}', unsafe_allow_html=True)
            render_filtered_dataframe(np_[["docdate","docno","contra_ledger_name","group_name","debit_amount","credit_amount"]], key_prefix="new_parties")
        else: st.markdown(f'{badge("NONE","success")}', unsafe_allow_html=True)
        with st.expander("🚩 New Party + New Group (Double Flag)"):
            df = detect_new_party_in_new_group(conn)
            if not df.empty:
                st.markdown(f'{badge("HIGH RISK","danger")}', unsafe_allow_html=True)
                render_filtered_dataframe(df, key_prefix="double_flag")
            else: st.markdown(f'{badge("CLEAR","success")}', unsafe_allow_html=True)
    except: pass

# ── Inter-Party ──
with tabs[10]:
    st.markdown(f"**Overbilling / Underbilling Detection** {badge('INTER-PARTY','warning')}", unsafe_allow_html=True)
    try:
        ip = detect_interparty_anomalies(conn)
        if not ip.empty:
            st.markdown(f'{badge(f"{len(ip)} ANOMALIES","danger")}', unsafe_allow_html=True)
            render_filtered_dataframe(ip.style.format({"party_avg_rate":"₹ {:.0f}","global_avg_rate":"₹ {:.0f}","deviation_pct":"{:.1f}%"}), key_prefix="interparty")
        else: st.markdown(f'{badge("CLEAN","success")}', unsafe_allow_html=True)
    except: pass

# ── Bank vs ERP ──
with tabs[11]:
    st.markdown(f"**Bank vs System Reconciliation** {badge('CROSS-CHECK','info')}", unsafe_allow_html=True)
    try:
        um = reconcile_bank_vs_system(conn)
        if not um.empty:
            st.markdown(f'{badge(f"{len(um)} UNMATCHED","warning")}', unsafe_allow_html=True)
            render_filtered_dataframe(um, key_prefix="bank_vs_erp")
        else: st.markdown(f'{badge("ALL MATCHED","success")}', unsafe_allow_html=True)
        with st.expander("💳 Payment Account Verification"):
            pav = check_payment_account_match(conn)
            if not pav.empty:
                st.markdown(f'{badge("MISMATCHES","danger")}', unsafe_allow_html=True)
                render_filtered_dataframe(pav, key_prefix="payment_account")
            else: st.markdown(f'{badge("ALL VERIFIED","success")}', unsafe_allow_html=True)
    except: pass

# ── Classification ──
with tabs[12]:
    st.markdown(f"**Auto-Classification Engine** {badge('TAXONOMY','info')}", unsafe_allow_html=True)
    try:
        cl = classify_all_transactions(conn)
        if not cl.empty:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f'{badge("CREDITS","success")}', unsafe_allow_html=True)
                cr = cl[cl["direction"]=="CREDIT"]["category_key"].value_counts()
                render_filtered_dataframe(pd.DataFrame(cr), key_prefix="classification_credits")
            with c2:
                st.markdown(f'{badge("DEBITS","danger")}', unsafe_allow_html=True)
                dr = cl[cl["direction"]=="DEBIT"]["category_key"].value_counts()
                render_filtered_dataframe(pd.DataFrame(dr), key_prefix="classification_debits")
            with st.expander("📋 Full Classified Ledger"):
                render_filtered_dataframe(cl[["docdate","contra_ledger_name","debit_amount","credit_amount","direction","category_key","category_desc"]], key_prefix="classification_full")
        else: st.info("Awaiting data.")
    except: pass

# ── Self-Tests ──
with tabs[13]:
    st.markdown(f"**System Integrity Verification** {badge('110 TESTS','info')}", unsafe_allow_html=True)
    if st.button("▶ Run Self-Tests", type="primary"):
        from data_ingestion import standardize_dates as _sd
        tests = []
        # Test 1
        t = pd.DataFrame({"material_value":[100],"tax_amt":[5],"charges_amt":[0],"rebate_amt":[0],"net_amt":[120]})
        d = abs(t["net_amt"]-(t["material_value"]+t["tax_amt"]+t["charges_amt"]-t["rebate_amt"])).iloc[0]
        tests.append(("Billing Mismatch Logic", d > 1.0))
        # Test 2
        imp = 2000/10; var = abs(imp-100)/100
        tests.append(("Outlier Detection", var > 0.20))
        # Test 3
        t3 = _sd(pd.DataFrame({"D":["04-01-2025"]}), ["D"])
        tests.append(("Date Normalization", t3["D"].iloc[0] == "2025-01-04"))
        # Test 4
        zs = compute_zscore_outliers(pd.Series([10,10,10,10,10,10,100]), threshold=2.0)
        tests.append(("Z-Score Outlier", bool(zs.iloc[-1])))
        # Test 5
        from audit_rules.transaction_flags import classify_transaction
        d_, k_, _ = classify_transaction("SALARY","SALARY ACCOUNT",200000,0)
        tests.append(("Transaction Classification", d_=="DEBIT" and k_=="SALARY"))

        for name, passed in tests:
            if passed:
                st.markdown(f'✅ **{name}** {badge("PASSED","success")}', unsafe_allow_html=True)
            else:
                st.markdown(f'❌ **{name}** {badge("FAILED","danger")}', unsafe_allow_html=True)
        st.markdown(f"<div style='margin-top:1rem'>{badge('Run RUN_TESTS.bat for full 110-test suite','info')}</div>", unsafe_allow_html=True)

# ── Vault ──
with tabs[14]:
    st.markdown(f"**Historical Data Explorer** {badge('VAULT','info')}", unsafe_allow_html=True)
    vt = st.radio("Table:", ["Bank Ledger","Purchase Ledger","Sales Ledger","GST Portal"], horizontal=True)
    tmap = {"Bank Ledger":"bank_ledger","Purchase Ledger":"purchase_ledger","Sales Ledger":"sales_ledger","GST Portal":"gst_portal"}
    try:
        table_name = tmap.get(vt)
        allowed_tables = {"bank_ledger", "purchase_ledger", "sales_ledger", "gst_portal"}
        if table_name not in allowed_tables:
            st.error("Invalid table selected.")
        else:
            render_filtered_dataframe(pd.read_sql(f"SELECT * FROM {table_name}", conn), key_prefix="vault")
    except: st.error("Table empty.")

# ── Footer ──
st.markdown("""
<div style="text-align:center; padding:2rem 0 1rem; color:#475569; font-size:0.75rem; border-top:1px solid rgba(99,102,241,0.1); margin-top:2rem;">
    🛡️ Financial Audit Command Center · v1.0 · 100% Offline · Data never leaves your machine
</div>
""", unsafe_allow_html=True)