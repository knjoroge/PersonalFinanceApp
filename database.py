"""
database.py — All data storage and retrieval for the Personal Finance Manager.

Uses SQLite to store everything in a single local file (finance.db).
Handles transactions, accounts, budgets, preferences, CSV import/export, and backups.
"""

import sqlite3
import shutil
import pandas as pd
from datetime import datetime, timedelta
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

# Keyword → expense category guesses for CSV imports that have no category column.
# Matched against the (lower-cased) transaction description. First hit wins, so
# order the lists from most to least specific. Add a bank's common payees here.
_CATEGORY_KEYWORDS = {
    "Food":           ["grocery", "groceries", "supermarket", "tesco", "aldi", "lidl",
                        "sainsbury", "walmart", "whole foods", "restaurant", "cafe",
                        "coffee", "starbucks", "mcdonald", "uber eats", "deliveroo", "doordash"],
    "Transportation": ["uber", "lyft", "shell", "bp ", "chevron", "exxon", "fuel", "gas station",
                       "petrol", "parking", "transit", "metro", "train", "airline", "flight"],
    "Housing":        ["rent", "mortgage", "landlord", "hoa"],
    "Utilities":      ["electric", "water", "gas bill", "internet", "broadband", "comcast",
                       "verizon", "at&t", "phone", "mobile"],
    "Healthcare":     ["pharmacy", "doctor", "dental", "clinic", "hospital", "cvs", "walgreens"],
    "Insurance":      ["insurance", "geico", "allstate", "aetna"],
    "Entertainment":  ["netflix", "spotify", "hulu", "disney", "cinema", "movie", "steam",
                       "playstation", "xbox"],
    "Debt":           ["loan", "credit card payment", "interest"],
}


def guess_category(description: str) -> str:
    """Best-effort expense category from a transaction description (for CSV imports).

    Returns a matching EXPENSE_CATEGORIES name when a keyword is found, else "Other".
    Case-insensitive substring match — simple and predictable, no ML.
    """
    text = (description or "").lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return category
    return "Other"


ASSET_TYPES = ["Checking", "Savings", "401k", "Pension", "Shares/Brokerage",
               "Real Estate", "Other Assets"]
LIABILITY_TYPES = ["Credit Card", "Mortgage", "Loan", "Other Liabilities"]
ACCOUNT_TYPES = ASSET_TYPES + LIABILITY_TYPES


def _connect() -> sqlite3.Connection:
    """Open a connection to the SQLite database file."""
    return sqlite3.connect(DB_PATH)


def _exec(sql: str, params: tuple = ()) -> None:
    """Run a single write query (INSERT/UPDATE/DELETE) and commit it.

    Saves us from repeating the open-connection / commit dance in every function.
    """
    with _connect() as conn:
        conn.execute(sql, params)
        conn.commit()


def _validate_transaction(date: str, amount: float, category: str, t_type: str) -> None:
    """Check that a transaction's fields are sensible before saving."""
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
    """Create the database tables on first run. Safe to call repeatedly."""
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
    """Save a new income or expense entry to the database."""
    _validate_transaction(date, amount, category, t_type)
    _exec(
        "INSERT INTO transactions (date, amount, category, type, description) VALUES (?, ?, ?, ?, ?)",
        (date, amount, category.strip(), t_type, description),
    )


def get_all_transactions() -> pd.DataFrame:
    """Fetch every transaction in the database, newest first."""
    with _connect() as conn:
        return pd.read_sql("SELECT * FROM transactions ORDER BY date DESC", conn)


def delete_transaction(transaction_id: int) -> None:
    """Remove a single transaction by its database ID."""
    _exec("DELETE FROM transactions WHERE id = ?", (int(transaction_id),))


def update_transaction(transaction_id: int, date: str, amount: float,
                       category: str, t_type: str, description: str) -> None:
    """Replace the values of an existing transaction."""
    _validate_transaction(date, amount, category, t_type)
    _exec(
        "UPDATE transactions SET date=?, amount=?, category=?, type=?, description=? WHERE id=?",
        (date, amount, category, t_type, description, int(transaction_id)),
    )


def summarize(df: pd.DataFrame) -> Dict[str, float]:
    """Compute headline totals (income / expense / net / savings rate) from a transactions dataframe.

    Returned dict keys: 'income', 'expense', 'net', 'savings_rate'.
    Safe to call with an empty dataframe — all values default to 0.
    """
    if df.empty:
        return {'income': 0.0, 'expense': 0.0, 'net': 0.0, 'savings_rate': 0.0}
    income = float(df[df['type'] == 'Income']['amount'].sum())
    expense = float(df[df['type'] == 'Expense']['amount'].sum())
    net = income - expense
    savings_rate = (net / income * 100) if income > 0 else 0.0
    return {'income': income, 'expense': expense, 'net': net, 'savings_rate': savings_rate}


# --- Accounts ---

def add_or_update_account(name: str, account_type: str, balance: float) -> None:
    """Add a new account, or update the balance if an account with the same name already exists.

    Name matching is case-insensitive ("Chase" and "chase" are treated as the same account).
    """
    if not name or not name.strip():
        raise ValueError("Account name cannot be empty.")
    name = name.strip()
    last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _connect() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM accounts WHERE LOWER(name) = LOWER(?)", (name,))
        existing = cursor.fetchone()
        if existing:
            cursor.execute(
                "UPDATE accounts SET balance=?, last_updated=?, type=? WHERE id=?",
                (balance, last_updated, account_type, existing[0]),
            )
        else:
            cursor.execute(
                "INSERT INTO accounts (name, type, balance, last_updated) VALUES (?, ?, ?, ?)",
                (name, account_type, balance, last_updated),
            )
        conn.commit()


def get_all_accounts() -> pd.DataFrame:
    """Fetch all tracked accounts, sorted by type then name."""
    with _connect() as conn:
        return pd.read_sql("SELECT * FROM accounts ORDER BY type, name", conn)


def delete_account(account_id: int) -> None:
    """Remove a single account record by its database ID."""
    _exec("DELETE FROM accounts WHERE id = ?", (int(account_id),))


def get_net_worth() -> float:
    """Return the sum of all account balances (0.0 if no accounts exist)."""
    with _connect() as conn:
        result = conn.execute("SELECT SUM(balance) FROM accounts").fetchone()[0]
    return result if result else 0.0


# --- Budgets ---

def set_budget(category: str, monthly_limit: float) -> None:
    """Set or update a monthly spending limit for a category."""
    if monthly_limit <= 0:
        raise ValueError("Budget limit must be positive.")
    _exec(
        "INSERT INTO budgets (category, monthly_limit) VALUES (?, ?) "
        "ON CONFLICT(category) DO UPDATE SET monthly_limit = ?",
        (category, monthly_limit, monthly_limit),
    )


def get_all_budgets() -> pd.DataFrame:
    """Fetch every saved category budget, in alphabetical order."""
    with _connect() as conn:
        return pd.read_sql("SELECT * FROM budgets ORDER BY category", conn)


def delete_budget(budget_id: int) -> None:
    """Remove a category budget by its database ID."""
    _exec("DELETE FROM budgets WHERE id = ?", (int(budget_id),))


# --- Preferences (key/value store for small UI state like the monthly goal) ---

def get_preference(key: str, default: Optional[str] = None) -> Optional[str]:
    """Read a stored preference, or return the default if it isn't set."""
    with _connect() as conn:
        row = conn.execute("SELECT value FROM preferences WHERE key = ?", (key,)).fetchone()
    return row[0] if row else default


def set_preference(key: str, value: str) -> None:
    """Store a preference value, overwriting any existing value for the same key."""
    _exec(
        "INSERT INTO preferences (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = ?",
        (key, str(value), str(value)),
    )


# --- Currency (display-only; no FX conversion) ---

CURRENCY_KEY = "display_currency"
DEFAULT_CURRENCY = "$"
SUPPORTED_CURRENCIES = ["$", "£", "€"]


def get_currency() -> str:
    """Return the user's chosen display currency symbol (defaults to '$')."""
    return get_preference(CURRENCY_KEY, DEFAULT_CURRENCY) or DEFAULT_CURRENCY


def set_currency(symbol: str) -> None:
    """Save the user's chosen display currency. Rejects unknown symbols."""
    if symbol not in SUPPORTED_CURRENCIES:
        raise ValueError(
            f"Unsupported currency '{symbol}'. Pick one of: {', '.join(SUPPORTED_CURRENCIES)}."
        )
    set_preference(CURRENCY_KEY, symbol)


def format_money(value: float, decimals: int = 2) -> str:
    """Format a number with the user's chosen currency symbol.

    Picks the thousands/decimal separator from the currency choice so the
    output looks native — `$1,234.50`, `£1,234.50` (UK uses the same
    convention as US for personal finance), and `€1.234,50` (continental EU).
    Pure display helper — never converts, never rounds beyond `decimals`.
    """
    sym = get_currency()
    if sym == "€":
        # Continental EU: dot for thousands, comma for decimals.
        formatted = f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{sym}{formatted}"
    return f"{sym}{value:,.{decimals}f}"


# --- CSV import mapping presets (saved per bank in the preferences table) ---

# All preset keys live under this prefix so we can list them cheaply.
_CSV_PRESET_PREFIX = "csv_preset:"


def save_csv_mapping_preset(name: str, mapping: Dict[str, Optional[str]],
                            dayfirst: bool = True) -> None:
    """Save a column-mapping under a friendly name (e.g. "MyBank") so the user
    can re-apply it next time they import a file from the same bank.

    The mapping is stored as JSON inside the existing preferences table —
    no new schema needed. Names are case-insensitive.
    """
    import json
    name = (name or "").strip()
    if not name:
        raise ValueError("Preset name cannot be empty.")
    payload = json.dumps({"mapping": mapping, "dayfirst": bool(dayfirst)})
    set_preference(_CSV_PRESET_PREFIX + name.lower(), payload)


def list_csv_mapping_presets() -> list:
    """Return the names of every saved CSV mapping preset."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT key FROM preferences WHERE key LIKE ? ORDER BY key",
            (_CSV_PRESET_PREFIX + "%",),
        ).fetchall()
    return [r[0][len(_CSV_PRESET_PREFIX):] for r in rows]


def get_csv_mapping_preset(name: str) -> Optional[Dict]:
    """Look up a saved CSV mapping by name. Returns None if unknown."""
    import json
    raw = get_preference(_CSV_PRESET_PREFIX + (name or "").strip().lower())
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


def delete_csv_mapping_preset(name: str) -> None:
    """Remove a saved CSV mapping by name (no-op if it doesn't exist)."""
    _exec(
        "DELETE FROM preferences WHERE key = ?",
        (_CSV_PRESET_PREFIX + (name or "").strip().lower(),),
    )


# --- CSV Import / Export ---

def export_transactions_csv() -> Optional[str]:
    """Export all transactions as a CSV string. Returns None if there are no transactions."""
    df = get_all_transactions()
    return df.to_csv(index=False) if not df.empty else None


# Column-name aliases used by the smart CSV importer, in priority order.
# All lower-case — _read_csv_smart() already lower-cases incoming column names.
# To support a new bank, just add its column name to the right list below.
_CSV_ALIASES = {
    'date':   ['date', 'transaction date', 'post date', 'posting date',
               'completed date', 'settled date'],
    'amount': ['amount', 'value', 'local amount', 'cost'],
    'debit':  ['debit', 'money out'],
    'credit': ['credit', 'money in'],
    'desc':   ['description', 'name', 'payee', 'memo', 'narrative',
               'transaction description'],
    'cat':    ['category'],
    'type':   ['type', 'transaction type'],
}


def _decode_csv(content: Union[str, bytes]) -> str:
    """Convert raw CSV input (bytes or string) into a UTF-8 string."""
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

    if any(c in df.columns for c in _CSV_ALIASES['date']):
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
    """Match the CSV's lowercased column names against the known field aliases.

    Returns a dict mapping each logical field (date, amount, debit, credit,
    desc, cat, type) to the actual column name found in the CSV, or None
    when no match exists.
    """
    cols = {
        field: next((c for c in aliases if c in df.columns), None)
        for field, aliases in _CSV_ALIASES.items()
    }
    if date_col_hint:
        cols['date'] = date_col_hint
    return cols


def _parse_csv_date(raw, dayfirst: bool = True) -> str:
    """Turn whatever the CSV gave us into a YYYY-MM-DD string.

    `dayfirst` controls how ambiguous dates like "02/03/2026" are read.
    - dayfirst=True (default): "02/03/2026" → 2 March 2026 (UK style)
    - dayfirst=False:           "02/03/2026" → 3 February 2026 (US style)
    Unambiguous dates (e.g. "2026-03-15") parse the same either way.
    """
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            return pd.to_datetime(raw, dayfirst=dayfirst).strftime("%Y-%m-%d")
    except Exception:
        return str(raw).strip()


def _clean_money(s) -> str:
    """Strip currency symbols and commas from a money-like string, leaving digits, dot, minus."""
    if pd.isnull(s):
        return ""
    return re.sub(r'[^\d\.-]', '', str(s).replace(',', ''))


def _parse_amount_and_type(row, cols: Dict[str, Optional[str]]) -> Optional[Tuple[float, str]]:
    """
    Extract (amount, type) for a CSV row.

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


def _existing_transaction_keys() -> set:
    """Return a set of (date, amount, type, description) tuples for all stored transactions.

    Used by CSV import to skip rows that look like exact duplicates of existing entries.
    """
    with _connect() as conn:
        rows = conn.execute(
            "SELECT date, amount, type, COALESCE(description, '') FROM transactions"
        ).fetchall()
    return {(d, float(a), t, (desc or "").strip()) for d, a, t, desc in rows}


# Fields the importer needs at minimum. "amount" can be satisfied EITHER by a
# single amount column OR by a debit + credit pair (see _parse_amount_and_type).
_CSV_REQUIRED_FIELDS = ("date", "amount")


def analyze_csv(csv_content: Union[str, bytes]) -> Dict:
    """Inspect a CSV without importing it. Used by the UI to decide whether
    we can import in one click or need to ask the user to map columns.

    Returns a dict with:
      * 'preview'        — a DataFrame of the first 5 rows (or None on error)
      * 'columns'        — the list of column names found in the file
      * 'autodetected'   — mapping of logical-field → detected column name
                           (values can be None when not detected)
      * 'missing'        — list of required fields that auto-detect couldn't find
      * 'date_col_hint'  — internal hint for headerless CSVs (pass-through)
      * 'error'          — error message if the file couldn't be parsed
    """
    try:
        text = _decode_csv(csv_content)
        df, date_col_hint = _read_csv_smart(text)
    except Exception as e:
        return {
            'preview': None, 'columns': [], 'autodetected': {}, 'missing': list(_CSV_REQUIRED_FIELDS),
            'date_col_hint': None, 'error': f"Failed to parse CSV: {str(e)}",
        }

    cols = _find_csv_columns(df, date_col_hint)

    # "Amount" is considered satisfied if either the single Amount column OR
    # a debit/credit pair is present.
    has_amount = bool(cols['amount']) or (bool(cols['debit']) and bool(cols['credit']))
    missing = []
    if not cols['date']:
        missing.append('date')
    if not has_amount:
        missing.append('amount')

    return {
        'preview': df.head(5),
        'columns': list(df.columns),
        'autodetected': cols,
        'missing': missing,
        'date_col_hint': date_col_hint,
        'error': None,
    }


def import_transactions_csv(
    csv_content: Union[str, bytes],
    column_mapping: Optional[Dict[str, Optional[str]]] = None,
    dayfirst: bool = True,
) -> Tuple[int, int, Optional[str]]:
    """Import transactions from a CSV string.

    Supports most major bank formats automatically (Chase, Monzo, NatWest,
    Barclays, Bank of America, Wells Fargo, Revolut, DCU).

    For unknown banks, the caller can pass an explicit `column_mapping` from
    analyze_csv() output — e.g. `{'date': 'Trans Date', 'amount': 'Withdrawal',
    'desc': 'Memo'}` — to override auto-detect.

    `dayfirst` controls how ambiguous dates like "02/03/2026" are read.
    Pass False for US-style MM/DD dates, True (default) for UK-style DD/MM.

    Skips rows that exactly match an existing transaction (same date, amount,
    type, description) so re-importing the same statement is safe.

    All valid rows are inserted in a single batch for speed.

    Returns (count_imported, count_skipped_duplicates, error_message).
    """
    try:
        text = _decode_csv(csv_content)
        df, date_col_hint = _read_csv_smart(text)
    except Exception as e:
        return 0, 0, f"Failed to parse CSV: {str(e)}"

    # Start from auto-detection, then let the caller's mapping override any field.
    cols = _find_csv_columns(df, date_col_hint)
    if column_mapping:
        for field, col in column_mapping.items():
            if field in cols and col:
                cols[field] = col

    if not cols['date']:
        return 0, 0, f"Missing a date column. Found columns: {', '.join(df.columns)}"
    if not cols['amount'] and not (cols['debit'] and cols['credit']):
        return 0, 0, f"Missing an amount column (or debit/credit columns). Found columns: {', '.join(df.columns)}"

    existing = _existing_transaction_keys()
    seen_in_batch: set = set()
    rows_to_insert = []
    skipped = 0
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

            desc = ""
            if cols['desc'] and pd.notnull(row[cols['desc']]):
                desc = str(row[cols['desc']]).strip()

            if cols['cat'] and pd.notnull(row[cols['cat']]) and str(row[cols['cat']]).strip():
                category = str(row[cols['cat']]).strip()
            elif t_type == "Expense":
                # No category column — guess one from the description so the
                # pie chart and budgets aren't all lumped into "Other".
                category = guess_category(desc)
            else:
                category = "Other"

            date_str = _parse_csv_date(raw_date, dayfirst=dayfirst)
            _validate_transaction(date_str, amount, category, t_type)

            key = (date_str, float(amount), t_type, desc.strip())
            if key in existing or key in seen_in_batch:
                skipped += 1
                continue
            seen_in_batch.add(key)

            rows_to_insert.append((date_str, amount, category.strip(), t_type, desc))
        except Exception as e:
            errors.append(f"Row {idx + 1}: {str(e)}")

    if rows_to_insert:
        with _connect() as conn:
            conn.executemany(
                "INSERT INTO transactions (date, amount, category, type, description) VALUES (?, ?, ?, ?, ?)",
                rows_to_insert,
            )
            conn.commit()

    return len(rows_to_insert), skipped, ("; ".join(errors) if errors else None)


# --- Demo data (helper for empty-state onboarding) ---

def load_demo_data() -> int:
    """Populate the database with a small, realistic month of sample data.

    Used by the empty-state on the Dashboard so first-time users can click
    one button and immediately see what every page is supposed to look like.
    Skips silently if there are already transactions — never overwrites real data.
    Returns the number of transactions inserted (0 if it was a no-op).
    """
    if not get_all_transactions().empty:
        return 0

    today = datetime.now()
    # 30-day sample mixing salary, rent, groceries, transport, coffee, subscriptions.
    samples = [
        (0,  3500.00, "Salary",         "Income",  "Monthly salary"),
        (-2, 1200.00, "Housing",        "Expense", "Rent payment"),
        (-3,   85.40, "Food",           "Expense", "Whole Foods groceries"),
        (-4,   42.50, "Transportation", "Expense", "Shell gas"),
        (-5,   12.99, "Entertainment",  "Expense", "Netflix subscription"),
        (-7,    6.25, "Food",           "Expense", "Starbucks coffee"),
        (-8,   75.00, "Healthcare",     "Expense", "Dentist co-pay"),
        (-9,  220.00, "Utilities",      "Expense", "Electric + Internet bill"),
        (-11, 150.00, "Bonus",          "Income",  "Side hustle payment"),
        (-13,  29.99, "Entertainment",  "Expense", "Concert tickets"),
        (-15,  60.18, "Food",           "Expense", "Tesco groceries"),
        (-18, 100.00, "Savings",        "Expense", "Transfer to emergency fund"),
        (-20,  14.50, "Transportation", "Expense", "Uber ride"),
        (-22,  45.99, "Other",          "Expense", "Amazon purchase"),
        (-25,   9.99, "Entertainment",  "Expense", "Spotify subscription"),
        (-28,  18.75, "Food",           "Expense", "Lunch with team"),
    ]
    rows = [
        (
            (today + timedelta(days=offset)).strftime("%Y-%m-%d"),
            amount, category, t_type, desc,
        )
        for offset, amount, category, t_type, desc in samples
    ]
    with _connect() as conn:
        conn.executemany(
            "INSERT INTO transactions (date, amount, category, type, description) VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        # Three sample accounts to give Net Worth + the dashboard's net worth metric something to show.
        ts = today.strftime("%Y-%m-%d %H:%M:%S")
        conn.executemany(
            "INSERT INTO accounts (name, type, balance, last_updated) VALUES (?, ?, ?, ?)",
            [
                ("Demo Checking",  "Checking", 2400.00,  ts),
                ("Demo Savings",   "Savings",  8500.00,  ts),
                ("Demo Credit Card", "Credit Card", -450.00, ts),
            ],
        )
        conn.commit()
    return len(rows)


# --- Database Backup & Restore ---

def export_database() -> bytes:
    """Read the entire database file as raw bytes (for download)."""
    with open(DB_PATH, "rb") as f:
        return f.read()


def import_database(db_bytes: bytes) -> Tuple[bool, str]:
    """
    Replace the current database with an uploaded backup.

    Validates that the uploaded file is a real SQLite DB with the right tables
    before swapping it in. The previous database is preserved at finance.db.bak
    so a bad restore can still be rolled back manually.
    """
    temp_path = DB_PATH + ".tmp"
    backup_path = DB_PATH + ".bak"
    try:
        with open(temp_path, "wb") as f:
            f.write(db_bytes)

        with sqlite3.connect(temp_path) as conn:
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            if "transactions" not in tables or "accounts" not in tables:
                os.remove(temp_path)
                return False, "Invalid database: missing required tables (transactions, accounts)."

        # Keep a safety copy of the old DB before overwriting.
        if os.path.exists(DB_PATH):
            shutil.copy2(DB_PATH, backup_path)

        os.replace(temp_path, DB_PATH)
        return True, "Database restored successfully! Previous data saved as finance.db.bak."
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return False, f"Restore failed: {str(e)}"


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
