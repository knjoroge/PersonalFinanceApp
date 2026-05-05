"""Shared test setup — fixtures for temporary databases and sample data."""

import pytest
import sys
import os

# Let tests import from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import database as db


@pytest.fixture(autouse=True)
def use_temp_database(tmp_path, monkeypatch):
    """Redirect all DB operations to a fresh temp file so real data is never touched."""
    test_db = str(tmp_path / "test_finance.db")
    monkeypatch.setattr(db, "DB_PATH", test_db)
    db.init_db()
    yield test_db


@pytest.fixture
def sample_transactions():
    """Pre-fill the DB: $5k salary, $1.2k rent, $150 groceries, $200 entertainment."""
    db.add_transaction("2026-01-15", 5000.00, "Salary", "Income", "Monthly salary")
    db.add_transaction("2026-01-16", 1200.00, "Housing", "Expense", "Rent")
    db.add_transaction("2026-01-17", 150.00, "Food", "Expense", "Groceries")
    db.add_transaction("2026-01-20", 200.00, "Entertainment", "Expense", "Concert tickets")


@pytest.fixture
def sample_accounts():
    """Pre-fill the DB: Chase $3.5k, Ally $15k, Fidelity 401k $45k (total $63.5k)."""
    db.add_or_update_account("Chase Checking", "Checking", 3500.00)
    db.add_or_update_account("Ally Savings", "Savings", 15000.00)
    db.add_or_update_account("Fidelity 401k", "401k", 45000.00)
