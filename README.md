# Financial Oversight & Audit System

An automated financial audit dashboard for manufacturing and trading businesses.

## Quick Start

1. Install [Python 3.9+](https://www.python.org/downloads/) (check "Add to PATH")
2. Double-click **`START.bat`**
3. Dashboard opens at **http://localhost:8501**

## What's Inside

- **15 automated audit checks** — expense spikes, new parties, GST reconciliation, pricing outliers, and more
- **110 unit tests** — run `RUN_TESTS.bat` to verify system integrity
- **100% offline** — all data stays on your machine in `financial_data.db`
- **Duplicate-proof** — re-uploading the same CSV won't create duplicate rows

## Documentation

📘 See [`docs/USER_HANDBOOK.md`](docs/USER_HANDBOOK.md) for the complete client handbook.

## Configuration

Edit [`config.py`](config.py) to adjust audit thresholds (spike %, discount %, variance %, etc.)
