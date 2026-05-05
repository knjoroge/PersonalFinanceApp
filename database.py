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
    Import transactions from a CSV string. Returns (count_imported, error_message).
    The CSV needs columns: date, amount, category, type. Optional: description.
    """
    try:
        if isinstance(csv_content, bytes):
            csv_content = csv_content.decode("utf-8")
        df = pd.read_csv(io.StringIO(csv_content))
    except Exception as e:
        return 0, f"Failed to parse CSV: {str(e)}"

    required = {"date", "amount", "category", "type"}
    if not required.issubset(set(df.columns)):
        missing = required - set(df.columns)
        return 0, f"Missing required columns: {', '.join(missing)}"

    imported, errors = 0, []
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
            desc = str(row.get("description", "")).strip() if pd.notnull(row.get("description")) else ""
            add_transaction(str(row["date"]).strip(), amount, str(row["category"]).strip(), t_type, desc)
            imported += 1
        except Exception as e:
            errors.append(f"Row {idx + 1}: {str(e)}")

    return imported, "; ".join(errors) if errors else None


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
