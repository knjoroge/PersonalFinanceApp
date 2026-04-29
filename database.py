"""
database.py — All data storage and retrieval for the Personal Finance Manager.

This file handles everything related to saving and reading data. It uses
SQLite, a simple file-based database that stores all your information in
a single file called "finance.db" on your computer.

The main things this file lets the app do:
  - Create the database tables when the app starts for the first time
  - Add, view, edit, and delete transactions (income and expenses)
  - Add, view, and delete financial accounts (for net worth tracking)
  - Set and manage monthly budgets for spending categories
  - Import and export transactions as CSV (spreadsheet) files
  - Back up and restore the entire database
"""

import sqlite3
import pandas as pd
from datetime import datetime
import os
import io

# Where the database file is stored. By default it's "finance.db" in
# the project folder, but you can override it by setting the
# FINANCE_DB_PATH environment variable before starting the app.
DB_PATH = os.getenv("FINANCE_DB_PATH", "finance.db")


def init_db():
    """
    Creates the database tables if they don't already exist.

    This runs every time the app starts. If the tables are already
    there, nothing happens — your data is safe. If they're missing
    (e.g. first time running), they get created.

    Three tables are set up:
      - transactions: stores every income and expense entry
      - accounts: stores bank/investment account balances for net worth
      - budgets: stores monthly spending limits per category
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Table for tracking income and expenses
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                type TEXT NOT NULL,
                description TEXT
            )
        ''')

        # Table for tracking account balances (used for net worth)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                balance REAL NOT NULL,
                last_updated TEXT NOT NULL
            )
        ''')

        # Table for monthly budget goals per spending category
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL UNIQUE,
                monthly_limit REAL NOT NULL
            )
        ''')

        conn.commit()


# =========================================================================
#  TRANSACTION OPERATIONS
#  Functions for adding, viewing, editing, and deleting income/expense entries.
# =========================================================================

def add_transaction(date, amount, category, t_type, description):
    """
    Saves a new income or expense entry to the database.

    Parameters:
        date (str):        The date of the transaction (e.g. "2026-01-15").
        amount (float):    How much money — must be a positive number.
        category (str):    What the money was for (e.g. "Food", "Salary").
        t_type (str):      Either "Income" or "Expense".
        description (str): An optional note about the transaction.

    Raises:
        ValueError: If the amount is zero or negative, the category is
                    blank, or the type isn't "Income" or "Expense".
    """
    if amount <= 0:
        raise ValueError("Amount must be positive.")
    if not category or not category.strip():
        raise ValueError("Category cannot be empty.")
    if t_type not in ("Income", "Expense"):
        raise ValueError("Type must be 'Income' or 'Expense'.")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO transactions (date, amount, category, type, description)
            VALUES (?, ?, ?, ?, ?)
        ''', (date, amount, category.strip(), t_type, description))
        conn.commit()


def get_all_transactions():
    """
    Retrieves every transaction from the database, newest first.

    Returns:
        A Pandas DataFrame with columns: id, date, amount, category,
        type, description. Returns an empty DataFrame if there are
        no transactions yet.
    """
    with sqlite3.connect(DB_PATH) as conn:
        query = "SELECT * FROM transactions ORDER BY date DESC"
        df = pd.read_sql(query, conn)
    return df


def delete_transaction(transaction_id):
    """
    Permanently removes a transaction from the database.

    Parameters:
        transaction_id (int): The unique ID of the transaction to delete.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transactions WHERE id = ?", (int(transaction_id),))
        conn.commit()


def update_transaction(transaction_id, date, amount, category, t_type, description):
    """
    Edits an existing transaction with new values.

    Parameters:
        transaction_id (int): The unique ID of the transaction to update.
        date (str):           The new date.
        amount (float):       The new amount — must be positive.
        category (str):       The new category.
        t_type (str):         The new type ("Income" or "Expense").
        description (str):    The new description.

    Raises:
        ValueError: If the amount is zero or negative.
    """
    if amount <= 0:
        raise ValueError("Amount must be positive.")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE transactions
            SET date = ?, amount = ?, category = ?, type = ?, description = ?
            WHERE id = ?
        ''', (date, amount, category, t_type, description, int(transaction_id)))
        conn.commit()


# =========================================================================
#  ACCOUNT OPERATIONS
#  Functions for managing bank/investment accounts and calculating net worth.
# =========================================================================

def add_or_update_account(name, account_type, balance):
    """
    Adds a new account or updates the balance of an existing one.

    If an account with the given name already exists, its balance and
    timestamp are updated. If it doesn't exist, a new account is created.

    Parameters:
        name (str):          The account name (e.g. "Chase Checking").
        account_type (str):  The kind of account (e.g. "Checking", "401k").
        balance (float):     The current balance in dollars.

    Raises:
        ValueError: If the account name is empty or only whitespace.
    """
    if not name or not name.strip():
        raise ValueError("Account name cannot be empty.")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Check whether this account already exists in the database
        cursor.execute("SELECT id FROM accounts WHERE name = ?", (name,))
        result = cursor.fetchone()

        if result:
            # Account exists — just update its balance and timestamp
            cursor.execute('''
                UPDATE accounts 
                SET balance = ?, last_updated = ?, type = ?
                WHERE name = ?
            ''', (balance, last_updated, account_type, name))
        else:
            # New account — insert a fresh row
            cursor.execute('''
                INSERT INTO accounts (name, type, balance, last_updated)
                VALUES (?, ?, ?, ?)
            ''', (name, account_type, balance, last_updated))

        conn.commit()


def get_all_accounts():
    """
    Retrieves all accounts, sorted by type and then by name.

    Returns:
        A Pandas DataFrame with columns: id, name, type, balance,
        last_updated. Returns an empty DataFrame if no accounts exist.
    """
    with sqlite3.connect(DB_PATH) as conn:
        query = "SELECT * FROM accounts ORDER BY type, name"
        df = pd.read_sql(query, conn)
    return df


def delete_account(account_id):
    """
    Permanently removes an account from the database.

    Parameters:
        account_id (int): The unique ID of the account to delete.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM accounts WHERE id = ?", (int(account_id),))
        conn.commit()


def get_net_worth():
    """
    Calculates your total net worth by adding up all account balances.

    Returns:
        float: The sum of all account balances, or 0.0 if no accounts exist.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(balance) FROM accounts")
        result = cursor.fetchone()[0]
    return result if result else 0.0


# =========================================================================
#  BUDGET OPERATIONS
#  Functions for setting and managing monthly spending limits per category.
# =========================================================================

def set_budget(category, monthly_limit):
    """
    Sets (or updates) a monthly spending budget for a category.

    If a budget for this category already exists, the limit is updated.
    If not, a new budget entry is created.

    Parameters:
        category (str):      The spending category (e.g. "Food", "Housing").
        monthly_limit (float): The maximum amount to spend per month.

    Raises:
        ValueError: If the monthly limit is zero or negative.
    """
    if monthly_limit <= 0:
        raise ValueError("Budget limit must be positive.")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO budgets (category, monthly_limit) 
            VALUES (?, ?)
            ON CONFLICT(category) DO UPDATE SET monthly_limit = ?
        ''', (category, monthly_limit, monthly_limit))
        conn.commit()


def get_all_budgets():
    """
    Retrieves all budget entries, sorted alphabetically by category.

    Returns:
        A Pandas DataFrame with columns: id, category, monthly_limit.
    """
    with sqlite3.connect(DB_PATH) as conn:
        query = "SELECT * FROM budgets ORDER BY category"
        df = pd.read_sql(query, conn)
    return df


def delete_budget(budget_id):
    """
    Permanently removes a budget entry from the database.

    Parameters:
        budget_id (int): The unique ID of the budget to delete.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM budgets WHERE id = ?", (int(budget_id),))
        conn.commit()


# =========================================================================
#  CSV IMPORT / EXPORT
#  Functions for importing transactions from spreadsheet files and
#  exporting your transactions as a downloadable CSV.
# =========================================================================

def export_transactions_csv():
    """
    Converts all transactions into CSV (spreadsheet) format.

    Returns:
        str: A CSV-formatted string ready for download, or None if
             there are no transactions to export.
    """
    df = get_all_transactions()
    if df.empty:
        return None
    return df.to_csv(index=False)


def import_transactions_csv(csv_content):
    """
    Reads transactions from a CSV string and adds them to the database.

    The CSV must have these columns: date, amount, category, type.
    An optional "description" column is also supported.

    Each row is validated individually — valid rows are imported and
    invalid rows are skipped with an error message explaining why.

    Parameters:
        csv_content (str or bytes): The raw CSV data to import.

    Returns:
        tuple: (number_imported, error_message)
            - number_imported (int): How many rows were successfully added.
            - error_message (str or None): A summary of any row-level
              errors, or None if everything went smoothly.
    """
    # Parse the CSV content into a table
    try:
        if isinstance(csv_content, bytes):
            csv_content = csv_content.decode("utf-8")
        df = pd.read_csv(io.StringIO(csv_content))
    except Exception as e:
        return 0, f"Failed to parse CSV: {str(e)}"

    # Make sure the CSV has the columns we need
    required_cols = {"date", "amount", "category", "type"}
    if not required_cols.issubset(set(df.columns)):
        missing = required_cols - set(df.columns)
        return 0, f"Missing required columns: {', '.join(missing)}"

    # Process each row one at a time
    imported = 0
    errors = []
    for idx, row in df.iterrows():
        try:
            amount = float(row["amount"])
            if amount <= 0:
                errors.append(f"Row {idx + 1}: Amount must be positive")
                continue
            t_type = str(row["type"]).strip()
            if t_type not in ("Income", "Expense"):
                errors.append(f"Row {idx + 1}: Type must be 'Income' or 'Expense'")
                continue
            add_transaction(
                str(row["date"]).strip(),
                amount,
                str(row["category"]).strip(),
                t_type,
                str(row.get("description", "")).strip() if pd.notnull(row.get("description")) else ""
            )
            imported += 1
        except Exception as e:
            errors.append(f"Row {idx + 1}: {str(e)}")

    error_msg = "; ".join(errors) if errors else None
    return imported, error_msg


# =========================================================================
#  DATABASE BACKUP & RESTORE
#  Functions for downloading a copy of your database and restoring
#  from a previous backup.
# =========================================================================

def export_database():
    """
    Reads the entire database file and returns it as raw bytes.

    This is used for the "Download Backup" feature so you can save
    a copy of all your data.

    Returns:
        bytes: The raw contents of the database file.
    """
    with open(DB_PATH, "rb") as f:
        return f.read()


def import_database(db_bytes):
    """
    Replaces the current database with data from an uploaded backup.

    Safety checks:
      1. Writes the uploaded data to a temporary file first.
      2. Verifies it's a valid SQLite database.
      3. Checks that the required tables ("transactions" and "accounts") exist.
      4. Only then replaces the current database.

    Parameters:
        db_bytes (bytes): The raw bytes of the uploaded .db file.

    Returns:
        tuple: (success, message)
            - success (bool): True if the restore worked, False otherwise.
            - message (str): A human-readable result or error message.
    """
    try:
        # Write the uploaded data to a temporary file for validation
        temp_path = DB_PATH + ".tmp"
        with open(temp_path, "wb") as f:
            f.write(db_bytes)

        # Try opening it as a database to make sure it's valid
        with sqlite3.connect(temp_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            if "transactions" not in tables or "accounts" not in tables:
                os.remove(temp_path)
                return False, "Invalid database: missing required tables (transactions, accounts)."

        # Everything looks good — swap in the restored database
        os.replace(temp_path, DB_PATH)
        return True, "Database restored successfully!"
    except Exception as e:
        # Clean up the temp file if something went wrong
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return False, f"Restore failed: {str(e)}"


if __name__ == "__main__":
    # If you run this file directly (not through the app), it just
    # creates the database tables and confirms it worked.
    init_db()
    print("Database initialized successfully.")
