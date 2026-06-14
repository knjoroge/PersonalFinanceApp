# 💰 Personal Finance Manager

A friendly, easy-to-use app for managing your personal finances — built with Python.

Track your spending, set budgets, monitor your net worth, and get AI-powered financial advice — all from your browser.

---

## Quick Start

If you have Python 3.8+ and `make` installed, this is the fastest way to get running:

```bash
git clone https://github.com/YOUR_USERNAME/PersonalFinanceApp.git
cd PersonalFinanceApp
make setup   # Creates a virtual environment and installs everything
make run     # Opens the app in your browser
```

That's it! The app will open at `http://localhost:8501`.

You can also type `make` on its own to see all available commands.

> **Don't have `make`?** (common on Windows) Run these instead:
> ```bash
> python -m venv venv
> source venv/bin/activate   # Windows: venv\Scripts\activate
> pip install -r requirements.txt
> streamlit run app.py
> ```

---

## What Does It Do?

- **See your money at a glance** — A visual dashboard shows income, expenses, savings rate, and net worth.
- **Track every dollar** — Log income and expenses with categories and browse your full history.
- **Set spending budgets** — Choose a monthly limit for any category and watch colour-coded progress bars.
- **Import from your bank** — Upload a CSV from your bank to bulk-add transactions, or download your data.
- **Monitor your net worth** — Enter balances for assets (bank accounts, retirement funds, investments) *and* liabilities (credit cards, mortgages, loans) for a true net-worth picture.
- **Back up your data** — Download your entire database to keep a safe copy, and restore it any time.
- **Get AI advice** — Ask an AI assistant (powered by Google Gemini) questions about your finances.

---

## Features at a Glance

| Feature | What It Does |
|---|---|
| 📊 **Dashboard** | Charts of spending by category, income vs expenses over time, and key stats. |
| 🎯 **Category Budgets** | Set spending limits per category with green/yellow/red progress bars. |
| 💸 **Transactions** | Add, edit, delete, search, and filter by type, category, or date range. Income shows as `+`, expenses as `-`, with running totals for the current filter. |
| 📁 **CSV Import/Export** | Upload bank spreadsheets or download your data as CSV. Uncategorised rows are auto-categorised from their description. |
| 🏦 **Net Worth & Accounts** | Track assets (checking, savings, 401k, brokerage, real estate) and liabilities (credit cards, mortgages, loans), broken down into Total Assets / Total Liabilities / Net Worth. |
| 💾 **Backup & Restore** | Download/restore your database file for safekeeping. Restores auto-save your prior data as `finance.db.bak`. |
| 🧠 **AI Advisor** | Chat with an AI that knows your data. Includes 50/30/20 and compound interest calculators. |
| 🛟 **Safe Deletes** | Removing transactions, accounts, or budgets always asks for confirmation first. |

---

## What You'll Need

1. **Python 3.8+** — Check with `python --version`. Download from [python.org](https://www.python.org/downloads/) if needed.
2. **A Gemini API Key** *(optional)* — Only for the AI chat feature. Get one free at [Google AI Studio](https://aistudio.google.com/app/apikey). Either paste it into the sidebar at runtime, or add `GEMINI_API_KEY=your-key` to a `.env` file in the project root and the app will pick it up automatically on startup (the `.env` file is gitignored, so your key stays local).

---

## Getting Around

Use the **sidebar on the left** to switch between views:

| View | What to do there |
|---|---|
| **Dashboard** | See your financial overview. Add data in other tabs first! |
| **Transactions** | Add income and expenses. Use CSV Import/Export for bulk data. |
| **Net Worth & Accounts** | Enter current balances for your accounts. Has backup/restore too. |
| **AI Advisor** | Chat with an AI that knows your finances. **Privacy note:** API keys are never saved to disk, and the AI only sees your aggregate totals, never your individual transactions. |

---

## Smart CSV Import

You don't need to manually rename columns or reformat your bank's CSV export. Just upload it directly and the app will figure it out.

The smart importer has been tested with exports from **Chase**, **Monzo**, **NatWest**, **Barclays**, **Bank of America**, **Wells Fargo**, **Revolut**, and **DCU**. It recognises all of these column names automatically:

| What we need | Column names we recognise |
|---|---|
| **Date** | `Date`, `Transaction Date`, `Post Date`, `Posting Date`, `Completed Date`, `Settled Date` |
| **Amount** | `Amount`, `Value`, `Local Amount`, `Cost` — or split `Debit`/`Credit` or `Money Out`/`Money In` columns |
| **Description** | `Description`, `Name`, `Payee`, `Memo`, `Narrative`, `Transaction Description` |
| **Category** | `Category` (if missing, expenses are auto-categorised from their description — see below) |
| **Type** | `Type`, `Transaction Type` (if missing, positive amounts = Income, negative = Expense) |

> **How it works:** If your bank uses a single "Amount" column with negative numbers for purchases, the app treats negative = Expense and positive = Income. If your bank has separate "Debit" / "Credit" columns (like NatWest) or "Money Out" / "Money In" (like Barclays), those are used instead. CSVs without a header row (like Wells Fargo) are also detected and handled automatically.
>
> **Re-importing is safe:** rows that exactly match an existing transaction (same date, amount, type, and description) are skipped automatically, so you won't end up with duplicates if you upload an overlapping statement.
>
> **Auto-categorisation:** when your CSV has no `Category` column, the app guesses an expense category from each transaction's description (e.g. "TESCO" → Food, "Uber" → Transportation, "Netflix" → Entertainment). Anything it doesn't recognise falls back to "Other". You can tune the keyword list in `_CATEGORY_KEYWORDS` in `database.py`.

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
├── app.py              # Starts the app and builds the sidebar navigation
├── database.py         # All data storage and retrieval
├── Makefile            # One-command setup, run, and test
├── requirements.txt    # Python package dependencies
├── README.md           # This file
├── USER_GUIDE.md       # Step-by-step walkthrough for first-time users
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
    ├── test_database.py
    ├── test_dashboard.py
    └── test_views.py
```

---

## License

Personal project. Feel free to use and modify for your own needs.
