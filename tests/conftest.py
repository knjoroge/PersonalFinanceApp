"""
conftest.py — Shared test setup used by all tests in this folder.

This file is automatically loaded by pytest before running any tests.
It provides "fixtures" — reusable pieces of setup that tests can request.

Key fixtures defined here:
  - use_temp_database: Makes every test use a fresh, temporary database
    so tests never affect your real data.
  - sample_transactions: Pre-fills the test database with example
    income and expense entries.
  - sample_accounts: Pre-fills the test database with example bank
    and investment accounts.
"""

import pytest
import sys
import os

# Add the project root folder to Python's search path so that
# "import database" works from inside the tests folder.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import database as db


@pytest.fixture(autouse=True)
def use_temp_database(tmp_path, monkeypatch):
    """
    Redirects all database operations to a temporary file.

    This runs automatically before every single test (autouse=True).
    It creates a fresh, empty database in a temporary folder so that:
      - Tests never read or write your real finance.db
      - Each test starts with a clean slate
      - The temporary database is deleted after the test finishes
    """
    test_db = str(tmp_path / "test_finance.db")
    monkeypatch.setattr(db, "DB_PATH", test_db)
    db.init_db()
    yield test_db


@pytest.fixture
def sample_transactions():
    """
    Adds a set of example transactions to the test database.

    After this fixture runs, the database will contain:
      - 1 income entry: $5,000 salary
      - 3 expense entries: $1,200 rent, $150 groceries, $200 entertainment
    """
    db.add_transaction("2026-01-15", 5000.00, "Salary", "Income", "Monthly salary")
    db.add_transaction("2026-01-16", 1200.00, "Housing", "Expense", "Rent")
    db.add_transaction("2026-01-17", 150.00, "Food", "Expense", "Groceries")
    db.add_transaction("2026-01-20", 200.00, "Entertainment", "Expense", "Concert tickets")


@pytest.fixture
def sample_accounts():
    """
    Adds a set of example accounts to the test database.

    After this fixture runs, the database will contain:
      - Chase Checking:  $3,500
      - Ally Savings:    $15,000
      - Fidelity 401k:   $45,000
      (Total net worth: $63,500)
    """
    db.add_or_update_account("Chase Checking", "Checking", 3500.00)
    db.add_or_update_account("Ally Savings", "Savings", 15000.00)
    db.add_or_update_account("Fidelity 401k", "401k", 45000.00)
