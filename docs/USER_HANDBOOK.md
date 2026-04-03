# 📘 Financial Oversight & Audit System
## Client Handbook — v1.0

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Requirements](#2-system-requirements)
3. [Installation & First Launch](#3-installation--first-launch)
4. [Data Preparation & Upload](#4-data-preparation--upload)
5. [Dashboard Overview](#5-dashboard-overview)
6. [Feature Guide — Financial Health](#6-feature-guide--financial-health)
7. [Feature Guide — Audit Rules Engine](#7-feature-guide--audit-rules-engine)
8. [Feature Guide — Data Vault](#8-feature-guide--data-vault)
9. [System Self-Tests](#9-system-self-tests)
10. [Configuration & Thresholds](#10-configuration--thresholds)
11. [What This System Can Do](#11-what-this-system-can-do)
12. [What This System Cannot Do](#12-what-this-system-cannot-do)
13. [Troubleshooting](#13-troubleshooting)
14. [Data Security & Backup](#14-data-security--backup)
15. [Glossary](#15-glossary)

---

## 1. Introduction

The **Financial Oversight & Audit System** is an automated financial audit
dashboard designed for manufacturing and trading businesses. It ingests
transaction data from your ERP system (Bank, Purchase, Sales, and GST records),
stores it in a local database, and runs **15 automated audit checks** to flag
unusual activity, pricing anomalies, billing errors, and reconciliation
mismatches.

### Purpose

The system helps auditors and financial controllers:

- Get a **real-time financial health snapshot** (cash flow, daily profitability)
- **Flag unusual transactions** automatically (spikes, new parties, pricing
  outliers)
- **Reconcile** bank payments against GST portal data and ERP records
- **Track party behaviour** over time (momentum, always-low buyers,
  overbilling)
- **Verify billing math** and Bill of Materials (BOM) accuracy
- **Classify** all transactions into a standard taxonomy (Credit/Debit
  categories)

### How It Works

```
ERP CSV Exports → Upload via Dashboard → SQLite Database → 15 Audit Rules → Flags & Reports
```

All data stays **100% local on your machine**. Nothing is sent to the internet.

---

## 2. System Requirements

| Requirement    | Minimum                          | Recommended              |
|---------------|----------------------------------|--------------------------|
| Operating Sys. | Windows 10 or later             | Windows 11               |
| Python        | 3.9+                             | 3.12+                    |
| RAM           | 4 GB                             | 8 GB                     |
| Disk Space    | 500 MB (app + data)              | 2 GB                     |
| Browser       | Any modern browser               | Chrome / Edge            |
| Network       | Not required (fully offline)     | —                        |

---

## 3. Installation & First Launch

### Step 1: Install Python (one time only)

If Python is not already installed:

1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download the latest Python 3.x installer
3. **IMPORTANT**: Check the box ☑ **"Add Python to PATH"** during installation
4. Click "Install Now"

### Step 2: Launch the Application

1. Open the `Financial Audit System` folder
2. **Double-click `START.bat`**
3. Wait for the green text to say **"Launching dashboard..."**
4. Your browser will open automatically to **http://localhost:8501**

```
[1/3] Python found.
[2/3] Checking dependencies...
[3/3] Launching dashboard...

========================================================
  Dashboard will open in your default browser.
  Press Ctrl+C in this window to stop the server.
========================================================
```

> **First-time launch** may take 2–3 minutes to install libraries. Subsequent
> launches are instant.

### Step 3: Stopping the Application

- Press **Ctrl+C** in the terminal window, or
- Simply **close the terminal window**

---

## 4. Data Preparation & Upload

### Supported File Formats

The system accepts **CSV files** exported from your ERP system. Four types are
supported:

| File Type      | Required Columns                                            | Purpose                         |
|---------------|------------------------------------------------------------|---------------------------------|
| **Bank CSV**   | DOCDATE, DOCNO, CONTRA_LEDGER_NAME, GROUP_NAME, DEBIT_AMOUNT, CREDIT_AMOUNT, BRANCH_ID | Cash flow, KPIs, party analysis |
| **Purchase CSV** | INV_NO, INV_DATE, PARTY_NAME, ITEM_NAME, REC_QTY, MATERIAL_VALUE, TAX_AMT, CHARGES_AMT, REBATE_AMT, NET_AMT | Procurement audits, BOM checks  |
| **Sales CSV**  | INV_NO, DOCDATE, PARTY_NAME, ITEM_NAME, BILLING_QUANTITY, NET_RATE, MATERIAL_VALUE | Sales outliers, discount checks |
| **GST Portal** | DOCDATE (or DATE), TAX_AMOUNT (or AMOUNT)                  | GST reconciliation              |

### How to Upload

1. Open the dashboard in your browser
2. Use the **sidebar** (left panel) titled "📥 Data Ingestion Portal"
3. Click **"Browse files"** under the appropriate section
4. Select your CSV file
5. Click **"💾 Process & Save Data"**
6. You'll see a confirmation: `✅ Loaded — Bank: 1929 new rows`

### Important Notes on Data Upload

- **ERP header rows are handled automatically.** Your CSV can have "Details
  for..." junk rows at the top; the system skips them.
- **Dates are normalized automatically.** Whether your dates are `04-01-2025`,
  `2025-01-04`, or `04/01/2025`, they all get standardised.
- **Duplicate prevention.** Uploading the same file twice does NOT create
  duplicate rows. The system uses content hashing to detect duplicates.
- **Data is appended.** Each upload adds new data to the existing database.
  Upload week-by-week or month-by-month — it all accumulates.
- **Recommended limit: 200 MB per file** for optimal browser performance.

---

## 5. Dashboard Overview

The dashboard is divided into three main sections:

### Section A: Financial Health & Cash Flow (Top)

Displays real-time KPIs and profitability charts.

- **Total Inward (Credit)** — Sum of all incoming payments
- **Total Outward (Debit)** — Sum of all outgoing payments
- **Net Cash Flow** — Credit minus Debit (green = positive, red = negative)
- **90th Percentile Outward** — The transaction size below which 90% of
  debits fall (helps identify large outliers)

### Section B: Branch & Category Analysis (Middle)

Two tabs:

- **Branch-wise** — Each branch's total inward, outward, and net flow. Expand
  "Branch + Category Breakdown" for detailed group-level data within each
  branch.
- **Category-wise** — Group-level totals across all branches (e.g., SUNDRY
  CREDITORS, SALARY, GST PAYMENTS).

### Section C: Automated Audit Rules Engine (Bottom)

**15 tabs**, each running a different audit check. Described in detail in
Section 7 below.

---

## 6. Feature Guide — Financial Health

### 6.1 Interactive Filters

At the top of the dashboard, three filters let you slice data:

| Filter            | What it does                                  |
|-------------------|----------------------------------------------|
| Filter by Branch  | Show only selected branch(es)                 |
| Filter by Category | Show only selected group(s)                  |
| Min Transaction Size | Hide transactions below this ₹ amount       |

These filters affect the KPIs and the chart below them.

### 6.2 Transaction Size Percentiles

Click the **"📊 Transaction Size Percentiles"** expander to see the full
percentile distribution of your transactions:

| Percentile | Meaning                                      |
|-----------|----------------------------------------------|
| P10       | 10% of transactions are below this amount     |
| P25       | Lower quartile                                |
| P50       | Median transaction size                       |
| P75       | Upper quartile                                |
| P90       | 90% of transactions are below this amount     |
| P95       | Only 5% of transactions exceed this           |
| P99       | Only 1% of transactions exceed this (extreme) |

### 6.3 Daily Profitability & Net Cash Flow Chart

An interactive line chart showing:

- **Net Cash Flow** = daily credits − daily debits
- **Daily Profitability** = net cash flow − estimated tax − estimated
  depreciation

Use the sliders on the left to adjust:
- **Est. Daily Tax (₹)** — e.g., 5000
- **Est. Daily Depreciation (₹)** — e.g., 2000

This provides a "What-If" analysis tool for understanding true daily
profitability after deductions.

---

## 7. Feature Guide — Audit Rules Engine

The system has **15 audit tabs**. Each runs a specific rule against your data.

---

### Tab 1: 🤝 Party 360

**What it does:** Provides a complete view of each party — total billed vs
total paid, pending balance, year-over-year delta, and last year's ledger
balance.

**How to use:** Review the table sorted by `pending_balance` (descending). Large
pending balances indicate unreconciled amounts.

**Sub-section — Party Momentum:** Shows quarterly payment trend per party. A
high `avg_momentum` means increasing payments quarter-over-quarter.

---

### Tab 2: ⚖️ Correlation Engine

**What it does:** Computes Pearson correlation between any two financial
metrics (e.g., "Bank Debit: TRANSPORT CHARGES" vs "Sales Vol: YELLOW SOYA
DOC").

**How to use:**
1. Pick **Variable A** and **Variable B** from the dropdowns
2. The system shows the **Pearson r** coefficient and **p-value**
3. r close to +1 = strong positive correlation; close to -1 = strong negative

**Use case:** Verify if transport costs scale with sales volume. If r < 0.5,
transport spending may be disconnected from actual sales.

---

### Tab 3: 📊 Service-to-Sales Ratio

**What it does:** Checks if external service costs (Brokerage, Transport) scale
proportionally with sales quantity.

**How to use:** Review the `cost_per_unit` trend line. A spike means service
costs increased without a proportional increase in sales.

---

### Tab 4: 🏛️ GST Reconciliation

**What it does:** Compares GST payments in bank records against GST portal
data.

**How to use:**
1. Upload both Bank CSV and GST Portal CSV
2. The table shows monthly bank GST paid, portal GST filed, and the mismatch
3. Any non-zero mismatch row is highlighted in red

**Sub-section — GST Misclassification:** Flags payments tagged as GST that
are statistically unusual (potential misclassification).

---

### Tab 5: 📈 Expense Spikes

**What it does:** Detects sudden month-over-month increases (>30%) in any
expense group.

**How to use:** Review the flagged rows. `spike_pct` shows the percentage
increase. Check if the spike is legitimate (e.g., annual payment) or
suspicious.

**Sub-section — Sudden Decreases:** Also flags unusual drops in spending
(potential missed payments).

---

### Tab 6: 💰 Salary Spikes

**What it does:** Specifically monitors salary/payroll payments for sudden
increases (>25%).

**How to use:** A salary spike could indicate unauthorized raises, ghost
employees, or data entry errors.

---

### Tab 7: 🏷️ Sales Outliers

**What it does:** Identifies buyers receiving significantly larger discounts
than the global average (>10% below average rate).

**How to use:** Review the `discount_pct` column. High values indicate a buyer
is consistently getting below-market prices.

**Sub-section — Always-Low-Price Buyers:** Flags parties where >80% of their
transactions are below the average rate AND they have 3+ transactions.

---

### Tab 8: 📉 Purchase Outliers

**What it does:** Compares each purchase's unit rate against the historical
baseline for that item. Flags purchases where the variance exceeds the
threshold.

**How to use:**
1. Adjust the **Variance Threshold (%)** slider (default: 20%)
2. Review flagged purchases — high variance means overpaying or underpaying
   compared to historical norms

**Sub-sections:**
- **Average Material Cost Summary** — Weighted average rate per item, with
  min/max/std deviation
- **BOM Historical Deviations** — Flags line items where the unit rate deviates
  >30% from historical averages

---

### Tab 9: 🧮 Billing Mismatches

**What it does:** Verifies the billing math:
`material_value + tax_amt + charges_amt - rebate_amt ≈ net_amt`

Any line where the difference exceeds ₹1 is flagged.

**Sub-section — BOM Total Validation:** Groups all line items in an invoice and
checks if the component totals match the invoice totals.

---

### Tab 10: 🆕 New Parties

**What it does:** Flags parties that appear only once in the entire bank
ledger. A single-entry party could indicate a fake vendor, test transaction, or
one-off payment requiring review.

**Sub-section — New Party in New Group (Double Flag):** Extra warning for
parties that are BOTH new AND appear in a group never seen before.

---

### Tab 11: 🔁 Inter-Party Analysis

**What it does:** Detects overbilling and underbilling by comparing each
party's average purchase rate against the global average per item. Flags
deviations >20%.

**Use case:** If Vendor A charges 40% above the market rate for STEAM COAL,
this tab will flag it.

---

### Tab 12: 🏦 Bank vs System Reconciliation

**What it does:** Identifies bank transactions that don't correspond to any
known purchase/sales party in the ERP system. These could be direct bank
transactions not captured in ERP.

**Sub-section — Payment Account Verification:** Checks if payments went to the
party named on the invoice (catches misrouted payments).

---

### Tab 13: 🏷️ Transaction Classification

**What it does:** Automatically classifies every bank transaction into the
standard taxonomy:

**Credits (Inward):**  
- Party Payment (against product)  
- Bank Loans  
- Investment Income (rent, interest)

**Debits (Outward):**  
- Machine Purchase  
- Raw Material (Soya, Cotton, Sunflower, etc.)  
- Services (Routine/Uncommon)  
- Transport  
- Brokerage  
- GST Payments  
- Statutory Payments (PF, ESI, TDS)  
- Salary  
- Dividend  
- Inter-Branch Transfers

**How to use:** Review the credit/debit summary counts, then expand the
full classified ledger for the complete breakdown.

---

### Tab 14: 🧪 Unit Tests

**What it does:** Runs 5 in-app self-tests to verify the core audit logic is
working correctly:

| Test                     | What it Verifies                          |
|--------------------------|------------------------------------------|
| Billing Mismatch Logic   | Catches ₹15 discrepancy (100+5 ≠ 120)   |
| Outlier Detection        | Flags 100% variance in purchase rate      |
| Date Normalization       | Converts DD-MM-YYYY to YYYY-MM-DD         |
| Z-Score Outlier          | Identifies statistical outlier (100 in [10,10,...]) |
| Transaction Classification | Correctly classifies Salary as DEBIT/SALARY |

For the full 110-test suite, run **`RUN_TESTS.bat`** from the project folder.

---

## 8. Feature Guide — Data Vault

### Tab 15: 🗄️ Vault (Historical Data Explorer)

**What it does:** Browse all raw data stored in the system.

**How to use:**
1. Select a table: Bank Ledger, Purchase Ledger, Sales Ledger, or GST Portal
2. The full table is displayed with all columns
3. Use this to spot-check data, export subsets, or verify ingestion

---

## 9. System Self-Tests

The system includes **110 automated unit tests** covering every audit rule.

### Running Tests

1. Double-click **`RUN_TESTS.bat`** in the project folder
2. Wait ~6 seconds
3. Results will show:

```
======================== 110 passed in 6.00s =========================
```

### What the Tests Cover

| Module                   | Tests | Validates                             |
|--------------------------|-------|---------------------------------------|
| Data Ingestion           | 18    | CSV parsing, dates, dedup, numerics   |
| Anomaly Detection        | 14    | Expense spikes, salary spikes, Z-score|
| Party Analysis           | 15    | New parties, YoY, inter-party, momentum|
| Transaction Flags        | 18    | Flag CRUD, taxonomy classification    |
| Reconciliation           | 13    | GST match, billing math, bank-vs-ERP  |
| Procurement              | 12    | Price outliers, avg cost, BOM checks  |
| Sales Analysis           | 7     | Discount outliers, low-price buyers   |
| Correlation              | 12    | Pearson r, p-value, edge cases        |
| Cash Flow                | 1+    | Daily P&L, percentiles, branch totals |

---

## 10. Configuration & Thresholds

All audit thresholds are defined in **`config.py`**. You can adjust these
without modifying any other code:

| Setting                   | Default | Description                                |
|--------------------------|---------|--------------------------------------------|
| `SPIKE_THRESHOLD_PCT`    | 30.0    | % MoM increase to flag as expense spike     |
| `DISCOUNT_ALARM_PCT`     | 10.0    | % below avg to flag as buyer discount       |
| `PROCUREMENT_VARIANCE_PCT`| 20.0   | % variance in purchase price to flag        |
| `BILLING_TOLERANCE`      | 1.0     | ₹ tolerance for billing math checks         |
| `SALARY_SPIKE_PCT`       | 25.0    | % MoM increase to flag as salary spike      |
| `ZSCORE_THRESHOLD`       | 2.5     | Standard deviations for outlier detection   |
| `CORRELATION_MIN_MONTHS` | 3       | Min months for reliable correlation         |
| `LOW_PRICE_CONSISTENCY_PCT`| 10.0  | % below avg for always-low buyer flag       |

### Audit Status Categories

When reviewing flagged items, you can set each to:

| Status              | Meaning                               |
|--------------------|---------------------------------------|
| Pending            | Not yet reviewed                       |
| Checked            | Reviewed and verified — no issue       |
| Ignore             | Reviewed — not relevant to audit       |
| Flagged            | Requires further investigation         |
| Not Necessary to Check | Low-priority — skip                |

---

## 11. What This System Can Do

✅ **Financial Health Monitoring**
- Total inward/outward, net cash flow, daily profitability
- Transaction size percentiles (P10–P99)
- Branch-wise and category-wise breakdown with drill-down

✅ **Automated Anomaly Detection**
- Expense spikes (MoM >30%)
- Salary spikes (MoM >25%)
- Z-score outlier detection on any numeric series
- Sudden increase/decrease detection (both directions)

✅ **Party Intelligence**
- Full party reconciliation (billed vs paid vs pending)
- Year-over-year delta and last year's ledger balance
- New party detection (single-entry flag)
- New party in new group (double flag)
- Inter-party overbilling/underbilling
- Always-low-price buyer detection
- Quarterly party momentum tracking

✅ **Reconciliation**
- GST portal vs bank payment matching
- GST misclassification detection
- Bank vs ERP system reconciliation (catches unrecorded bank transactions)
- Payment account verification (money went to the right party)
- Billing math validation (material + tax + charges − rebate = net)
- BOM total validation and historical deviation checks

✅ **Sales & Procurement Audit**
- Buyer discount outlier detection
- Average material cost computation with min/max/std
- Procurement pricing variance analysis (configurable threshold)
- Service-to-sales ratio monitoring

✅ **Time-Series Analysis**
- Pearson correlation between any two metrics
- Full correlation matrix across all datasets
- Configurable minimum months for reliability

✅ **Auto-Classification**
- Every transaction auto-tagged: Credit (Party/Loan/Investment) or Debit
  (Machine/RawMaterial/Service/Transport/Brokerage/GST/Statutory/Salary/
  Dividend/InterBranch)

✅ **Data Integrity**
- Duplicate prevention on re-upload
- Date normalization (handles DD-MM-YYYY, YYYY-MM-DD, MM/DD/YYYY)
- ERP header row detection (skips junk rows)
- 110 automated unit tests

---

## 12. What This System Cannot Do

❌ **Real-time ERP Integration**
- Data must be manually exported from ERP and uploaded. There is no live
  API connection to Tally, SAP, or other ERP systems.

❌ **Multi-User / Role-Based Access**
- This is a single-user desktop application. There is no login system,
  user roles, or audit trail for who viewed what.

❌ **Stock / Inventory Tracking**
- The system analyses financial transactions. It does NOT track physical
  stock levels, warehouse locations, or production schedules.

❌ **Material Utilization Tracking**
- While it can flag procurement pricing issues, it cannot track WHERE
  purchased materials are being used in production (requires MRP data).

❌ **Automated Email / SMS Alerts**
- Flags are displayed in the dashboard only. There is no automated
  notification system.

❌ **PDF Report Generation**
- Data is viewable on-screen. For PDF exports, use the browser's Print
  function (Ctrl+P → Save as PDF).

❌ **Historical Comparison Across Years**
- Year-over-year analysis requires data from multiple years in the
  database. With only 1 week of data, YoY features will show N/A.

❌ **Invoice Image / Document Attachment**
- The system works with numeric CSV data only. It cannot store or display
  scanned invoices, bills, or supporting documents.

---

## 13. Troubleshooting

### "Python was not found"

**Solution:** Install Python from [python.org](https://www.python.org/downloads/)
and check ☑ "Add Python to PATH".

### START.bat gets stuck at "Installing dependencies"

**Solution:** This is normal on first launch (downloading ~150 MB of
libraries). Wait 3–5 minutes. If it truly freezes, press Ctrl+C, close the
window, and re-run START.bat.

### Dashboard shows "Awaiting Data"

**Solution:** You need to upload CSV files first. Use the sidebar to upload
Bank, Purchase, and/or Sales CSVs.

### Browser doesn't open automatically

**Solution:** Manually open your browser and go to
**http://localhost:8501**

### "Address already in use" error

**Solution:** Another instance is already running. Close all terminal windows
and try again, or open http://localhost:8501 directly.

### Charts show wrong dates or no data

**Solution:** Run the migration script:
```
py migrate_dates.py
```
Then refresh the dashboard (Ctrl+R in browser).

### Dashboard is slow with large datasets

**Solution:**
- Use the "Min Transaction Size" filter to exclude small transactions
- Filter by specific branch or category
- Consider loading data in monthly batches rather than all at once

---

## 14. Data Security & Backup

### Where is my data stored?

All data is stored locally in **`financial_data.db`** (SQLite file) in the
same folder as the application. **Nothing is sent to the cloud or internet.**

### How to back up

Simply **copy the `financial_data.db` file** to a safe location. This single
file contains all your bank, purchase, sales, GST, and audit flag data.

### How to restore from backup

Replace the `financial_data.db` file with your backup copy and restart the
application.

### How to reset (fresh start)

Delete the `financial_data.db` file and restart. A new empty database will be
created automatically.

---

## 15. Glossary

| Term                  | Definition                                            |
|-----------------------|------------------------------------------------------|
| **BOM**               | Bill of Materials — components/items within an invoice |
| **Contra Ledger**     | The other party in a bank transaction                 |
| **Debit**             | Money going out (payment)                             |
| **Credit**            | Money coming in (receipt)                             |
| **Group Name**        | Category classification in the ERP system             |
| **GST**               | Goods & Services Tax                                  |
| **Implied Rate**      | Unit price derived from material_value ÷ quantity     |
| **MoM**               | Month-over-Month comparison                           |
| **Net Amount**        | Final invoice amount after all additions/deductions   |
| **Pearson r**         | Correlation coefficient (-1 to +1)                    |
| **Percentile**        | % of values that fall below a given number            |
| **Spike**             | A sudden, significant increase beyond the threshold   |
| **Variance**          | Difference from the expected/average value             |
| **YoY**               | Year-over-Year comparison                             |
| **Z-Score**           | Number of standard deviations from the mean           |

---

## File Structure Reference

```
Financial Audit System/
│
├── START.bat              ← Double-click to launch
├── RUN_TESTS.bat          ← Double-click to run 110 tests
├── app.py                 ← Main dashboard application
├── config.py              ← All thresholds (edit this to tune)
├── database.py            ← Database schema
├── data_ingestion.py      ← CSV parsing & loading
├── requirements.txt       ← Python dependencies
├── financial_data.db      ← Your data (back this up!)
├── migrate_dates.py       ← One-time date format fixer
│
├── audit_rules/           ← Business logic modules
│   ├── anomaly_detection.py
│   ├── cashflow.py
│   ├── correlation.py
│   ├── party_analysis.py
│   ├── procurement.py
│   ├── reconciliation.py
│   ├── sales_analysis.py
│   └── transaction_flags.py
│
├── tests/                 ← 110 automated tests
│   ├── conftest.py
│   ├── test_anomaly_detection.py
│   ├── test_cashflow.py
│   ├── test_correlation.py
│   ├── test_data_ingestion.py
│   ├── test_party_analysis.py
│   ├── test_procurement.py
│   ├── test_reconciliation.py
│   ├── test_sales_analysis.py
│   └── test_transaction_flags.py
│
├── docs/                  ← Documentation
│   ├── USER_HANDBOOK.md   ← This file
│   └── images/            ← Dashboard screenshots
│
├── bank.csv               ← Sample data
├── purchase.csv           ← Sample data
└── sale.csv               ← Sample data
```

---

## Support

For questions, issues, or feature requests, contact the development team.

**Version:** 1.0  
**Last Updated:** April 2025  
**Python:** 3.9+  
**Framework:** Streamlit  
**Database:** SQLite (local, no server required)

---

*This document is part of the Financial Oversight & Audit System deliverable.*
