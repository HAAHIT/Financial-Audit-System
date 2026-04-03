"""
Central configuration for the Financial Audit System.
All thresholds, categories, and taxonomy definitions live here.
"""

# ============================================================
# AUDIT THRESHOLDS
# ============================================================
SPIKE_THRESHOLD_PCT = 30.0        # MoM overhead increase that triggers flag
DISCOUNT_ALARM_PCT = 10.0         # Buyer discount vs global avg that triggers flag
PROCUREMENT_VARIANCE_PCT = 20.0   # Purchase price variance vs baseline
BILLING_TOLERANCE = 1.0           # ₹ tolerance for billing math checks
SALARY_SPIKE_PCT = 25.0           # Salary sudden increase threshold
ZSCORE_THRESHOLD = 2.5            # Standard deviations for outlier detection
TRANSACTION_SIZE_LIMIT = 0        # Minimum transaction size filter (dashboard configurable)
CORRELATION_MIN_MONTHS = 3        # Minimum overlapping months for correlation
LOW_PRICE_CONSISTENCY_PCT = 10.0  # % below avg to flag "always low" buyer

# ============================================================
# AUDIT STATUS CATEGORIES
# ============================================================
AUDIT_STATUSES = [
    "Pending",
    "Checked",
    "Ignore",
    "Flagged",
    "Not Necessary to Check",
]

DEFAULT_AUDIT_STATUS = "Pending"

# ============================================================
# TRANSACTION TAXONOMY (from napkin notes)
# ============================================================
CREDIT_CATEGORIES = {
    "PARTY_PAYMENT": {
        "description": "Payment from party against product",
        "keywords": ["SUNDRY DEBTORS"],
    },
    "BANK_LOAN": {
        "description": "Bank loans",
        "keywords": ["LOAN", "BANK LOAN", "SECURED LOAN", "UNSECURED LOAN"],
    },
    "INVESTMENT_INCOME": {
        "description": "Payment against investments - rent, interest",
        "keywords": ["RENT", "INTEREST", "DIVIDEND", "INVESTMENT"],
    },
}

DEBIT_CATEGORIES = {
    "MACHINE_PURCHASE": {
        "description": "Machine / capital asset purchase",
        "keywords": ["MACHINE", "PLANT", "EQUIPMENT", "FIXED ASSET", "CAPITAL"],
    },
    "RAW_MATERIAL": {
        "description": "Raw material procurement",
        "keywords": [
            "SEED", "CRUDE SOYA", "CRUDE COTTON", "CRUDE SUNFLOWER",
            "REFINED SOYA", "REFINED COTTON", "REFINED SUNFLOWER",
            "SOYA", "COTTON", "SUNFLOWER", "OIL", "DOC",
            "SUNDRY CREDITORS",
        ],
    },
    "SERVICE_ROUTINE": {
        "description": "Routine services - testing, lab",
        "keywords": ["TESTING", "LAB", "INSPECTION", "QUALITY"],
    },
    "SERVICE_UNCOMMON": {
        "description": "Uncommon services - exhibition, event",
        "keywords": ["EXHIBITION", "EVENT", "CONFERENCE", "MARKETING"],
    },
    "TRANSPORT": {
        "description": "Transportation costs",
        "keywords": ["TRANSPORT", "FREIGHT", "LOGISTICS", "SHIPPING", "TRUCKING"],
    },
    "BROKERAGE": {
        "description": "Brokerage fees",
        "keywords": ["BROKERAGE", "BROKER", "COMMISSION"],
    },
    "GST_PAYMENT": {
        "description": "GST payments",
        "keywords": ["GST", "CGST", "SGST", "IGST"],
    },
    "STATUTORY": {
        "description": "Statutory payments",
        "keywords": ["PF", "ESI", "TDS", "PROFESSIONAL TAX", "STATUTORY"],
    },
    "SALARY": {
        "description": "Salary payments",
        "keywords": ["SALARY", "WAGES", "PAYROLL", "REMUNERATION"],
    },
    "DIVIDEND": {
        "description": "Dividend payments",
        "keywords": ["DIVIDEND"],
    },
    "INTER_BRANCH": {
        "description": "Inter-branch transfers (not a real expense)",
        "keywords": ["INTER BRANCH"],
    },
}

# ============================================================
# SERVICE GROUPS (for service-to-sales ratio)
# ============================================================
SERVICE_GROUP_KEYWORDS = ["BROKERAGE", "TRANSPORT", "FREIGHT", "TESTING", "LAB"]

# ============================================================
# DATABASE
# ============================================================
DB_NAME = "financial_data.db"
