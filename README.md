# 💰 Personal Finance Manager

A friendly, easy-to-use app for managing your personal finances — built with Python.

Whether you're just starting to track your spending or looking for a smarter way to manage your money, this app gives you a clear picture of where your money goes, helps you set budgets, and even offers AI-powered financial advice.

---

## What Does It Do?

In short, this app helps you:

- **See your money at a glance** — A visual dashboard shows your income, expenses, savings rate, and net worth in one place.
- **Track every dollar** — Log income and expenses with categories like "Food", "Housing", or "Salary", and browse your full history.
- **Set spending budgets** — Choose a monthly limit for any category (e.g. "$500/month on Food") and watch a progress bar so you know when you're getting close.
- **Import from your bank** — Upload a CSV file exported from your bank to bulk-add transactions, or download your data as a backup.
- **Monitor your net worth** — Enter the balances of your bank accounts, retirement funds, and investments to see your total net worth.
- **Back up your data** — Download your entire database to keep a safe copy, and restore it any time.
- **Get AI advice** — Ask an AI financial advisor (powered by Google Gemini) questions about your finances, and use built-in calculators for budgeting rules and compound interest.

---

## Features at a Glance

| Feature | What It Does |
|---|---|
| 📊 **Dashboard** | Shows charts of your spending by category, income vs. expenses over time, and key stats like savings rate. |
| 🎯 **Category Budgets** | Set a spending limit per category and see colour-coded progress bars (green / yellow / red). |
| 💸 **Transactions** | Add, edit, or delete individual income and expense entries. Filter and paginate through your history. |
| 📁 **CSV Import/Export** | Upload a spreadsheet from your bank to import transactions in bulk, or download your data. |
| 🏦 **Net Worth & Accounts** | Track balances across checking, savings, 401k, brokerage, and other accounts. |
| 💾 **Backup & Restore** | Download your database file for safekeeping. Restore from a backup if anything goes wrong. |
| 🧠 **AI Financial Advisor** | Chat with an AI assistant that knows your financial data. Includes a 50/30/20 budget calculator and a compound interest visualiser. |

---

## What You'll Need Before Starting

1. **Python 3.8 or newer** — This is the programming language the app is built with.
   - You can check if you have it by opening a terminal and typing: `python --version`
   - If you don't have it, download it free from [python.org](https://www.python.org/downloads/)

2. **A Google Gemini API Key** *(optional)* — Only needed if you want to use the AI Advisor chat feature.
   - Get one for free at [Google AI Studio](https://aistudio.google.com/app/apikey)

---

## How to Set Up the App

Follow these steps in your terminal (the command-line application on your computer):

### Step 1 — Download the project

If you received this as a zip file, unzip it. If you're cloning from GitHub:

```bash
git clone https://github.com/YOUR_USERNAME/PersonalFinanceApp.git
cd PersonalFinanceApp
```

### Step 2 — Create an isolated environment (recommended)

This keeps the app's software packages separate from the rest of your computer:

```bash
python -m venv venv
```

Then activate it:

- **Mac / Linux:**
  ```bash
  source venv/bin/activate
  ```
- **Windows:**
  ```bash
  venv\Scripts\activate
  ```

You'll know it worked if you see `(venv)` at the start of your terminal prompt.

### Step 3 — Install the required packages

```bash
pip install -r requirements.txt
```

This downloads everything the app needs to run (it may take a minute).

---

## How to Use the App

### Starting the app

```bash
streamlit run app.py
```

This will open the app in your web browser automatically (usually at `http://localhost:8501`).

### Getting around

Use the **sidebar on the left** to switch between views:

| View | What to do there |
|---|---|
| **Dashboard** | See your financial overview. Add data in other tabs first to see charts appear! |
| **Transactions** | Add your income and expenses. Use CSV Import/Export to upload bank data or download a backup. |
| **Net Worth & Accounts** | Enter current balances for your bank and investment accounts. Also has database backup/restore. |
| **AI Advisor** | Enter your Gemini API key at the top, then ask the AI questions about your finances. |

---

## Importing Transactions from a Spreadsheet (CSV)

If you want to import transactions from your bank, save or export them as a `.csv` file with these columns:

| Column | Required? | Example |
|---|---|---|
| `date` | ✅ Yes | `2026-01-15` |
| `amount` | ✅ Yes | `150.00` |
| `category` | ✅ Yes | `Food` |
| `type` | ✅ Yes | `Income` or `Expense` |
| `description` | ❌ Optional | `Grocery shopping` |

> **Tip:** Most banks let you export your transaction history as CSV. You may need to rename the columns to match the table above.

---

## Running the Tests

The project includes automated tests to make sure everything works correctly. To run them:

```bash
# Run all tests and show details
python -m pytest tests/ -v

# Run tests and also show how much code is covered
python -m pytest tests/ -v --cov=. --cov-report=term-missing
```

---

## Where Is My Data Stored?

All your data is stored in a **local file called `finance.db`** on your own computer — nothing is sent to the cloud (except AI Advisor questions, which go to Google's Gemini API if you use that feature).

The database is created automatically the first time you start the app.

If you want to store the database somewhere else, you can set a custom path before starting:

```bash
FINANCE_DB_PATH=/path/to/my/custom.db streamlit run app.py
```

---

## Project Structure

Here's how the project files are organised — you don't need to understand this to use the app, but it's helpful if you want to explore or contribute:

```
PersonalFinanceApp/
├── app.py                  # The main file that starts the app
├── database.py             # Handles all data storage and retrieval
├── requirements.txt        # Lists the software packages the app needs
├── .env                    # Stores private settings like API keys (not shared)
├── .gitignore              # Tells Git which files to ignore
├── .streamlit/
│   └── config.toml         # Visual theme settings for the app
├── views/                  # Each screen/page of the app
│   ├── __init__.py         # Marks this folder as a Python package
│   ├── dashboard.py        # The main dashboard with charts and budgets
│   ├── transactions.py     # The page for adding and viewing transactions
│   ├── accounts.py         # The page for tracking account balances
│   └── advisor.py          # The AI advisor chat and calculators
└── tests/                  # Automated tests to verify the app works
    ├── __init__.py         # Marks this folder as a Python package
    ├── conftest.py         # Shared setup used by all tests
    └── test_database.py    # Tests for all database operations
```

---

## License

This is a personal project. Feel free to use and modify it for your own needs.
