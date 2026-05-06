"""
database.py — All data storage and retrieval for the Personal Finance Manager.

Uses SQLite to store everything in a single local file (finance.db).
Handles transactions, accounts, budgets, CSV import/export, and backups.
"""

import sqlite3
import pandas as pd
from datetime import datetime
from typing import Optional, Tuple, Union
import os
import io
import re

# Database file location. Override with FINANCE_DB_PATH env var if needed.
DB_PATH = os.getenv("FINANCE_DB_PATH", "finance.db")


def _connect() -> sqlite3.Connection:
    """Shortcut to open a connection to the database."""
    return sqlite3.connect(DB_PATH)


def _validate_transaction(date: str, amount: float, category: str, t_type: str) -> None:
    """Shared validation for adding and updating transactions."""
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise ValueError("Date must be in YYYY-MM-DD format (e.g. '2026-01-15').")
    if amount <= 0:
        raise ValueError("Amount must be positive.")
    if not category or not category.strip():
        raise ValueError("Category cannot be empty.")
    if t_type not in ("Income", "Expense"):
        raise ValueError("Type must be 'Income' or 'Expense'.")


def init_db() -> None:
    """Create the database tables if they don't already exist."""
    with _connect() as conn:
        cursor = conn.cursor()
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
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                balance REAL NOT NULL,
                last_updated TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL UNIQUE,
                monthly_limit REAL NOT NULL
            )
        ''')
        conn.commit()


# --- Transactions ---

def add_transaction(date: str, amount: float, category: str, t_type: str, description: str) -> None:
    """Save a new income or expense entry."""
    _validate_transaction(date, amount, category, t_type)
    with _connect() as conn:
        conn.execute(
            "INSERT INTO transactions (date, amount, category, type, description) VALUES (?, ?, ?, ?, ?)",
            (date, amount, category.strip(), t_type, description),
        )
        conn.commit()


def get_all_transactions() -> pd.DataFrame:
    """Fetch every transaction, newest first."""
    with _connect() as conn:
        return pd.read_sql("SELECT * FROM transactions ORDER BY date DESC", conn)


def delete_transaction(transaction_id: int) -> None:
    """Remove a transaction by its ID."""
    with _connect() as conn:
        conn.execute("DELETE FROM transactions WHERE id = ?", (int(transaction_id),))
        conn.commit()


def update_transaction(transaction_id: int, date: str, amount: float,
                       category: str, t_type: str, description: str) -> None:
    """Edit an existing transaction with new values."""
    _validate_transaction(date, amount, category, t_type)
    with _connect() as conn:
        conn.execute(
            "UPDATE transactions SET date=?, amount=?, category=?, type=?, description=? WHERE id=?",
            (date, amount, category, t_type, description, int(transaction_id)),
        )
        conn.commit()


# --- Accounts ---

def add_or_update_account(name: str, account_type: str, balance: float) -> None:
    """Add a new account, or update the balance if it already exists."""
    if not name or not name.strip():
        raise ValueError("Account name cannot be empty.")
    with _connect() as conn:
        cursor = conn.cursor()
        last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("SELECT id FROM accounts WHERE name = ?", (name,))
        if cursor.fetchone():
            cursor.execute(
                "UPDATE accounts SET balance=?, last_updated=?, type=? WHERE name=?",
                (balance, last_updated, account_type, name),
            )
        else:
            cursor.execute(
                "INSERT INTO accounts (name, type, balance, last_updated) VALUES (?, ?, ?, ?)",
                (name, account_type, balance, last_updated),
            )
        conn.commit()


def get_all_accounts() -> pd.DataFrame:
    """Fetch all accounts, sorted by type then name."""
    with _connect() as conn:
        return pd.read_sql("SELECT * FROM accounts ORDER BY type, name", conn)


def delete_account(account_id: int) -> None:
    """Remove an account by its ID."""
    with _connect() as conn:
        conn.execute("DELETE FROM accounts WHERE id = ?", (int(account_id),))
        conn.commit()


def get_net_worth() -> float:
    """Sum of all account balances, or 0.0 if none exist."""
    with _connect() as conn:
        result = conn.execute("SELECT SUM(balance) FROM accounts").fetchone()[0]
    return result if result else 0.0


# --- Budgets ---

def set_budget(category: str, monthly_limit: float) -> None:
    """Set or update a monthly spending limit for a category."""
    if monthly_limit <= 0:
        raise ValueError("Budget limit must be positive.")
    with _connect() as conn:
        conn.execute(
            "INSERT INTO budgets (category, monthly_limit) VALUES (?, ?) "
            "ON CONFLICT(category) DO UPDATE SET monthly_limit = ?",
            (category, monthly_limit, monthly_limit),
        )
        conn.commit()


def get_all_budgets() -> pd.DataFrame:
    """Fetch all budgets, sorted alphabetically."""
    with _connect() as conn:
        return pd.read_sql("SELECT * FROM budgets ORDER BY category", conn)


def delete_budget(budget_id: int) -> None:
    """Remove a budget by its ID."""
    with _connect() as conn:
        conn.execute("DELETE FROM budgets WHERE id = ?", (int(budget_id),))
        conn.commit()


# --- CSV Import / Export ---

def export_transactions_csv() -> Optional[str]:
    """Export all transactions as a CSV string, or None if empty."""
    df = get_all_transactions()
    return df.to_csv(index=False) if not df.empty else None


def import_transactions_csv(csv_content: Union[str, bytes]) -> Tuple[int, Optional[str]]:
    """
    Import transactions from a CSV string using smart column mapping heuristics.
    Supports various bank formats (Chase, Monzo, NatWest, DCU) automatically.
    Returns (count_imported, error_message).
    """
    try:
        if isinstance(csv_content, bytes):
            csv_content = csv_content.decode("utf-8")
        df = pd.read_csv(io.StringIO(csv_content))
    except Exception as e:
        return 0, f"Failed to parse CSV: {str(e)}"

    # Lowercase all column names so we can match them regardless of casing
    original_cols = df.columns
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Try to find a column for each piece of data we need.
    # Banks use different names, so we check several common ones.
    date_col = next((c for c in ['date', 'transaction date', 'post date', 'posting date'] if c in df.columns), None)
    amount_col = next((c for c in ['amount', 'value', 'local amount', 'cost'] if c in df.columns), None)
    debit_col = next((c for c in ['debit', 'money out'] if c in df.columns), None)
    credit_col = next((c for c in ['credit', 'money in'] if c in df.columns), None)
    desc_col = next((c for c in ['description', 'name', 'payee', 'memo', 'transaction description'] if c in df.columns), None)
    cat_col = next((c for c in ['category'] if c in df.columns), None)
    type_col = next((c for c in ['type', 'transaction type'] if c in df.columns), None)

    if not date_col:
        return 0, f"Missing a date column. Found columns: {', '.join(original_cols)}"
        
    if not amount_col and not (debit_col and credit_col):
        return 0, f"Missing an amount column (or debit/credit columns). Found columns: {', '.join(original_cols)}"

    imported = 0
    errors = []
    
    for idx, row in df.iterrows():
        try:
            # Parse Date
            raw_date = row[date_col]
            if pd.isnull(raw_date):
                continue
            try:
                parsed_date = pd.to_datetime(raw_date).strftime("%Y-%m-%d")
            except Exception:
                parsed_date = str(raw_date).strip()

            # Parse Amount & Type
            amount = 0.0
            t_type = "Expense"
            
            explicit_type = str(row[type_col]).strip().title() if type_col and pd.notnull(row[type_col]) else None
            
            if amount_col and pd.notnull(row[amount_col]):
                raw_amt = str(row[amount_col]).replace(',', '')
                raw_amt = re.sub(r'[^\d\.-]', '', raw_amt)  # strip currency symbols etc.
                
                if not raw_amt or raw_amt == '-':
                    continue
                amount_val = float(raw_amt)
                
                if explicit_type in ("Income", "Expense"):
                    t_type = explicit_type
                    amount = abs(amount_val)
                else:
                    if amount_val < 0:
                        t_type = "Expense"
                        amount = abs(amount_val)
                    else:
                        t_type = "Income"
                        amount = amount_val
                        
            elif debit_col and credit_col:
                debit_val = str(row[debit_col]).replace(',', '') if pd.notnull(row[debit_col]) else ""
                credit_val = str(row[credit_col]).replace(',', '') if pd.notnull(row[credit_col]) else ""
                debit_val = re.sub(r'[^\d\.-]', '', debit_val)
                credit_val = re.sub(r'[^\d\.-]', '', credit_val)
                
                if debit_val and float(debit_val) > 0:
                    amount = float(debit_val)
                    t_type = "Expense"
                elif credit_val and float(credit_val) > 0:
                    amount = float(credit_val)
                    t_type = "Income"
                else:
                    continue
            else:
                continue
                
            if amount <= 0:
                continue  # skip zero-amount rows (e.g. auth holds)

            # Use the category from the CSV if available, otherwise default to "Other"
            category = "Other"
            if cat_col and pd.notnull(row[cat_col]) and str(row[cat_col]).strip():
                category = str(row[cat_col]).strip()

            desc = ""
            if desc_col and pd.notnull(row[desc_col]):
                desc = str(row[desc_col]).strip()

            add_transaction(parsed_date, amount, category, t_type, desc)
            imported += 1
            
        except Exception as e:
            errors.append(f"Row {idx + 1}: {str(e)}")

    error_msg = "; ".join(errors) if errors else None
    return imported, error_msg


# --- Database Backup & Restore ---

def export_database() -> bytes:
    """Read the entire database file as raw bytes (for download)."""
    with open(DB_PATH, "rb") as f:
        return f.read()


def import_database(db_bytes: bytes) -> Tuple[bool, str]:
    """
    Replace the current database with an uploaded backup.
    Validates the file is a real SQLite DB with the right tables first.
    """
    temp_path = DB_PATH + ".tmp"
    try:
        with open(temp_path, "wb") as f:
            f.write(db_bytes)

        with sqlite3.connect(temp_path) as conn:
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            if "transactions" not in tables or "accounts" not in tables:
                os.remove(temp_path)
                return False, "Invalid database: missing required tables (transactions, accounts)."

        os.replace(temp_path, DB_PATH)
        return True, "Database restored successfully!"
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return False, f"Restore failed: {str(e)}"


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
