"""
database.py — All data storage and retrieval for the Personal Finance Manager.

Uses SQLite to store everything in a single local file (finance.db).
Handles transactions, accounts, budgets, preferences, CSV import/export, and backups.
"""

import sqlite3
import pandas as pd
from datetime import datetime
from typing import Optional, Tuple, Union, Dict
import os
import io
import re

# Database file location. Override with FINANCE_DB_PATH env var if needed.
DB_PATH = os.getenv("FINANCE_DB_PATH", "finance.db")


# --- Shared category and account-type lists ---
# Imported by the views so renaming a category only requires editing one file.

INCOME_CATEGORIES = ["Salary", "Bonus", "Investment", "Side Hustle", "Other"]
EXPENSE_CATEGORIES = ["Housing", "Food", "Transportation", "Utilities", "Insurance",
                      "Healthcare", "Savings", "Debt", "Entertainment", "Other"]

ASSET_TYPES = ["Checking", "Savings", "401k", "Pension", "Shares/Brokerage",
               "Real Estate", "Other Assets"]
LIABILITY_TYPES = ["Credit Card", "Mortgage", "Loan", "Other Liabilities"]
ACCOUNT_TYPES = ASSET_TYPES + LIABILITY_TYPES


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
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
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
    with _connect() as conn:
        return pd.read_sql("SELECT * FROM budgets ORDER BY category", conn)


def delete_budget(budget_id: int) -> None:
    """Remove a budget by its ID."""
    with _connect() as conn:
        conn.execute("DELETE FROM budgets WHERE id = ?", (int(budget_id),))
        conn.commit()


# --- Preferences (key/value store for small UI state like the monthly goal) ---

def get_preference(key: str, default: Optional[str] = None) -> Optional[str]:
    """Read a stored preference, or return the default if it isn't set."""
    with _connect() as conn:
        row = conn.execute("SELECT value FROM preferences WHERE key = ?", (key,)).fetchone()
    return row[0] if row else default


def set_preference(key: str, value: str) -> None:
    """Store a preference, overwriting any existing value for the same key."""
    with _connect() as conn:
        conn.execute(
            "INSERT INTO preferences (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = ?",
            (key, str(value), str(value)),
        )
        conn.commit()


# --- CSV Import / Export ---

def export_transactions_csv() -> Optional[str]:
    """Export all transactions as a CSV string, or None if empty."""
    df = get_all_transactions()
    return df.to_csv(index=False) if not df.empty else None


# Column-name aliases used by the smart CSV importer, in priority order.
_DATE_ALIASES = ['date', 'transaction date', 'post date', 'posting date',
                 'completed date', 'settled date']
_AMOUNT_ALIASES = ['amount', 'value', 'local amount', 'cost']
_DEBIT_ALIASES = ['debit', 'money out']
_CREDIT_ALIASES = ['credit', 'money in']
_DESC_ALIASES = ['description', 'name', 'payee', 'memo', 'narrative', 'transaction description']
_CAT_ALIASES = ['category']
_TYPE_ALIASES = ['type', 'transaction type']


def _decode_csv(content: Union[str, bytes]) -> str:
    """Normalise raw CSV input to a UTF-8 string."""
    if isinstance(content, bytes):
        return content.decode("utf-8")
    return content


def _read_csv_smart(text: str) -> Tuple[pd.DataFrame, Optional[str]]:
    """
    Parse a CSV string, handling banks that ship without a header row.

    Some banks (Wells Fargo, some BofA exports) don't include a header. pandas
    treats the first data row as headers, so the "column names" look like
    actual data (e.g. "01/15/2026" instead of "Date"). Detect this: if no
    known date column is found but the first column name parses as a date,
    re-read the CSV without a header row and use a sensible default layout.

    Returns (dataframe, date_col_hint). The hint is the date column name when
    we already had to nominate one during smart-detection; None otherwise.
    """
    df = pd.read_csv(io.StringIO(text))
    df.columns = [str(c).strip().lower() for c in df.columns]

    if any(c in df.columns for c in _DATE_ALIASES):
        return df, None

    # No known date column — maybe the CSV is headerless.
    first_col_name = str(df.columns[0])
    try:
        pd.to_datetime(first_col_name)
    except (ValueError, TypeError):
        return df, None  # First column isn't a date — let the caller report a missing-column error.

    # First "column name" is a date → CSV was headerless. Re-read with auto-named columns.
    df = pd.read_csv(io.StringIO(text), header=None)
    if len(df.columns) < 3:
        return df, None  # Caller will detect the missing-columns case.

    # Most headerless bank CSVs follow: Date, Amount, [Type], [Check#], Description.
    df.columns = ['date', 'amount'] + [f'col{i}' for i in range(2, len(df.columns))]
    # The last text-like column is usually the description.
    for i in range(len(df.columns) - 1, 1, -1):
        col = df.columns[i]
        sample = df[col].dropna().head(5)
        looks_like_text = sample.apply(
            lambda v: isinstance(v, str) and not v.replace('.', '').replace('-', '').isdigit()
        ).any()
        if looks_like_text:
            df = df.rename(columns={col: 'description'})
            break

    return df, 'date'


def _find_csv_columns(df: pd.DataFrame, date_col_hint: Optional[str]) -> Dict[str, Optional[str]]:
    """Match the CSV's lowercased columns against our known aliases."""
    def _first_match(aliases):
        return next((c for c in aliases if c in df.columns), None)

    return {
        'date':   date_col_hint or _first_match(_DATE_ALIASES),
        'amount': _first_match(_AMOUNT_ALIASES),
        'debit':  _first_match(_DEBIT_ALIASES),
        'credit': _first_match(_CREDIT_ALIASES),
        'desc':   _first_match(_DESC_ALIASES),
        'cat':    _first_match(_CAT_ALIASES),
        'type':   _first_match(_TYPE_ALIASES),
    }


def _parse_csv_date(raw) -> str:
    """Turn whatever the CSV gave us into a YYYY-MM-DD string."""
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            return pd.to_datetime(raw, dayfirst=True).strftime("%Y-%m-%d")
    except Exception:
        return str(raw).strip()


def _clean_money(s) -> str:
    """Strip currency symbols/commas from a money-like string, leaving digits, dot, minus."""
    if pd.isnull(s):
        return ""
    return re.sub(r'[^\d\.-]', '', str(s).replace(',', ''))


def _parse_amount_and_type(row, cols: Dict[str, Optional[str]]) -> Optional[Tuple[float, str]]:
    """
    Extract (amount, type) for a row.

    Prefers a single Amount column (with optional explicit Type). If that's
    missing, falls back to separate Debit/Credit (or Money Out/Money In) columns.
    Returns None when the row has no usable amount.
    """
    amount_col, debit_col, credit_col, type_col = cols['amount'], cols['debit'], cols['credit'], cols['type']

    if amount_col and pd.notnull(row[amount_col]):
        raw_amt = _clean_money(row[amount_col])
        if not raw_amt or raw_amt == '-':
            return None
        amount_val = float(raw_amt)

        explicit_type = (str(row[type_col]).strip().title()
                         if type_col and pd.notnull(row[type_col]) else None)
        if explicit_type in ("Income", "Expense"):
            return abs(amount_val), explicit_type
        # No explicit type (or unknown one) — sign decides.
        if amount_val < 0:
            return abs(amount_val), "Expense"
        return amount_val, "Income"

    if debit_col and credit_col:
        debit_val = _clean_money(row[debit_col])
        credit_val = _clean_money(row[credit_col])
        if debit_val and float(debit_val) > 0:
            return float(debit_val), "Expense"
        if credit_val and float(credit_val) > 0:
            return float(credit_val), "Income"
        return None

    return None


def import_transactions_csv(csv_content: Union[str, bytes]) -> Tuple[int, Optional[str]]:
    """
    Import transactions from a CSV string using smart column mapping.
    Supports most major bank formats automatically, including Chase, Monzo,
    NatWest, Barclays, Bank of America, Wells Fargo, Revolut, and DCU.
    Returns (count_imported, error_message).
    """
    try:
        text = _decode_csv(csv_content)
        df, date_col_hint = _read_csv_smart(text)
    except Exception as e:
        return 0, f"Failed to parse CSV: {str(e)}"

    cols = _find_csv_columns(df, date_col_hint)

    if not cols['date']:
        return 0, f"Missing a date column. Found columns: {', '.join(df.columns)}"
    if not cols['amount'] and not (cols['debit'] and cols['credit']):
        return 0, f"Missing an amount column (or debit/credit columns). Found columns: {', '.join(df.columns)}"

    imported = 0
    errors = []

    for idx, row in df.iterrows():
        try:
            raw_date = row[cols['date']]
            if pd.isnull(raw_date):
                continue

            parsed = _parse_amount_and_type(row, cols)
            if parsed is None:
                continue
            amount, t_type = parsed
            if amount <= 0:
                continue  # skip zero-amount rows (e.g. auth holds)

            category = "Other"
            if cols['cat'] and pd.notnull(row[cols['cat']]) and str(row[cols['cat']]).strip():
                category = str(row[cols['cat']]).strip()

            desc = ""
            if cols['desc'] and pd.notnull(row[cols['desc']]):
                desc = str(row[cols['desc']]).strip()

            add_transaction(_parse_csv_date(raw_date), amount, category, t_type, desc)
            imported += 1
        except Exception as e:
            errors.append(f"Row {idx + 1}: {str(e)}")

    return imported, ("; ".join(errors) if errors else None)


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
