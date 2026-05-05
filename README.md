# 💰 Personal Finance Manager

A friendly, easy-to-use app for managing your personal finances — built with Python.

Track your spending, set budgets, monitor your net worth, and get AI-powered financial advice — all from your browser.

---

## Quick Start (30 seconds)

If you have Python 3.8+ and `make` installed, this is the fastest way to get running:

```bash
git clone https://github.com/YOUR_USERNAME/PersonalFinanceApp.git
cd PersonalFinanceApp
make setup   # Creates a virtual environment and installs everything
make run     # Opens the app in your browser
```

That's it! The app will open at `http://localhost:8501`.

> **Don't have `make`?** See [Manual Setup](#manual-setup) below.

---

## What Does It Do?

- **See your money at a glance** — A visual dashboard shows income, expenses, savings rate, and net worth.
- **Track every dollar** — Log income and expenses with categories and browse your full history.
- **Set spending budgets** — Choose a monthly limit for any category and watch colour-coded progress bars.
- **Import from your bank** — Upload a CSV from your bank to bulk-add transactions, or download your data.
- **Monitor your net worth** — Enter balances for bank accounts, retirement funds, and investments.
- **Back up your data** — Download your entire database to keep a safe copy, and restore it any time.
- **Get AI advice** — Ask an AI assistant (powered by Google Gemini) questions about your finances.

---

## Features at a Glance

| Feature | What It Does |
|---|---|
| 📊 **Dashboard** | Charts of spending by category, income vs expenses over time, and key stats. |
| 🎯 **Category Budgets** | Set spending limits per category with green/yellow/red progress bars. |
| 💸 **Transactions** | Add, edit, delete, filter, and paginate through your transaction history. |
| 📁 **CSV Import/Export** | Upload bank spreadsheets or download your data as CSV. |
| 🏦 **Net Worth & Accounts** | Track balances across checking, savings, 401k, brokerage, etc. |
| 💾 **Backup & Restore** | Download/restore your database file for safekeeping. |
| 🧠 **AI Advisor** | Chat with an AI that knows your data. Includes 50/30/20 and compound interest calculators. |

---

## What You'll Need

1. **Python 3.8+** — Check with `python --version`. Download from [python.org](https://www.python.org/downloads/) if needed.
2. **A Gemini API Key** *(optional)* — Only for the AI chat feature. Get one free at [Google AI Studio](https://aistudio.google.com/app/apikey).

---

## Manual Setup

If you don't have `make`, follow these steps in your terminal:

### 1. Download the project

```bash
git clone https://github.com/YOUR_USERNAME/PersonalFinanceApp.git
cd PersonalFinanceApp
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it:
- **Mac / Linux:** `source venv/bin/activate`
- **Windows:** `venv\Scripts\activate`

You'll see `(venv)` at the start of your prompt when it's active.

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the app

```bash
streamlit run app.py
```

---

## Getting Around

Use the **sidebar on the left** to switch between views:

| View | What to do there |
|---|---|
| **Dashboard** | See your financial overview. Add data in other tabs first! |
| **Transactions** | Add income and expenses. Use CSV Import/Export for bulk data. |
| **Net Worth & Accounts** | Enter current balances for your accounts. Has backup/restore too. |
| **AI Advisor** | Enter your Gemini API key, then ask the AI questions about your finances. |

---

## Importing Transactions from CSV

Export transactions from your bank as a `.csv` file with these columns:

| Column | Required? | Example |
|---|---|---|
| `date` | ✅ Yes | `2026-01-15` |
| `amount` | ✅ Yes | `150.00` |
| `category` | ✅ Yes | `Food` |
| `type` | ✅ Yes | `Income` or `Expense` |
| `description` | ❌ Optional | `Grocery shopping` |

> **Tip:** Most banks let you export as CSV. You may need to rename columns to match the table above.

---

## Running Tests

```bash
make test
```

Or manually:

```bash
python -m pytest tests/ -v
python -m pytest tests/ -v --cov=. --cov-report=term-missing
```

---

## Where Is My Data?

Everything is stored in a **local file called `finance.db`** on your computer — nothing goes to the cloud (except AI questions, which go to Google Gemini if you use that feature).

Custom storage path:
```bash
FINANCE_DB_PATH=/path/to/custom.db streamlit run app.py
```

---

## Project Structure

```
PersonalFinanceApp/
├── app.py              # Main entry point — starts the app
├── database.py         # All data storage and retrieval
├── Makefile            # One-command setup and run
├── requirements.txt    # Python package dependencies
├── .env                # Private settings (not shared)
├── .gitignore          # Files Git should ignore
├── .streamlit/
│   └── config.toml     # Visual theme settings
├── views/              # Each screen of the app
│   ├── dashboard.py    # Dashboard with charts and budgets
│   ├── transactions.py # Adding and viewing transactions
│   ├── accounts.py     # Account balances and backups
│   └── advisor.py      # AI advisor and calculators
└── tests/              # Automated tests
    ├── conftest.py     # Shared test setup
    └── test_database.py
```

---

## License

Personal project. Feel free to use and modify for your own needs.
