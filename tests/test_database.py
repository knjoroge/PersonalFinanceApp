"""
test_database.py — Automated tests for all database operations.

These tests verify that every function in database.py works correctly.
They cover:
  - Database initialisation (creating tables)
  - Adding, updating, deleting, and retrieving transactions
  - Input validation (rejecting bad data like negative amounts)
  - Adding, updating, and deleting accounts
  - Net worth calculation
  - Budget creation, updates, and deletion
  - CSV import and export (including error handling)
  - Database backup and restore

Each test runs against a temporary database (set up in conftest.py)
so your real data is never touched.
"""

import pytest
import pandas as pd
import database as db


class TestInitDB:
    """Tests for database initialisation (creating tables on first run)."""

    def test_tables_created(self):
        """After init, both the transactions and accounts tables should exist."""
        df_trans = db.get_all_transactions()
        df_accts = db.get_all_accounts()
        assert isinstance(df_trans, pd.DataFrame)
        assert isinstance(df_accts, pd.DataFrame)

    def test_idempotent_init(self):
        """Calling init_db multiple times should be safe and not duplicate data."""
        db.init_db()
        db.init_db()
        df = db.get_all_transactions()
        assert df.empty


class TestTransactions:
    """Tests for adding, retrieving, editing, and deleting transactions."""

    def test_add_and_retrieve(self):
        """Adding a transaction should make it appear when we fetch all transactions."""
        db.add_transaction("2026-03-01", 100.0, "Salary", "Income", "Test")
        df = db.get_all_transactions()
        assert len(df) == 1
        assert df.iloc[0]["amount"] == 100.0
        assert df.iloc[0]["category"] == "Salary"

    def test_add_multiple_transactions(self, sample_transactions):
        """The sample data fixture should create exactly 4 transactions."""
        df = db.get_all_transactions()
        assert len(df) == 4

    def test_delete_transaction(self, sample_transactions):
        """Deleting a transaction should reduce the count by one."""
        df = db.get_all_transactions()
        initial_count = len(df)
        first_id = df.iloc[0]["id"]

        db.delete_transaction(first_id)
        df_after = db.get_all_transactions()
        assert len(df_after) == initial_count - 1

    def test_delete_nonexistent_transaction(self):
        """Trying to delete a transaction that doesn't exist should not cause an error."""
        db.delete_transaction(99999)  # Should be a no-op

    def test_update_transaction(self, sample_transactions):
        """Updating a transaction should change its stored values."""
        df = db.get_all_transactions()
        first_id = df.iloc[0]["id"]

        db.update_transaction(first_id, "2026-02-01", 9999.99, "Bonus", "Income", "Updated")
        df_after = db.get_all_transactions()
        updated = df_after[df_after["id"] == first_id].iloc[0]
        assert updated["amount"] == 9999.99
        assert updated["category"] == "Bonus"
        assert updated["description"] == "Updated"

    def test_transactions_ordered_by_date_desc(self, sample_transactions):
        """Transactions should come back sorted with the newest first."""
        df = db.get_all_transactions()
        dates = list(df["date"])
        assert dates == sorted(dates, reverse=True)

    def test_reject_invalid_date_format(self):
        """A date not in YYYY-MM-DD format should be rejected with a clear error."""
        with pytest.raises(ValueError, match="Date must be in YYYY-MM-DD format"):
            db.add_transaction("banana", 50.0, "Food", "Expense", "Bad")

    def test_reject_negative_amount(self):
        """A negative amount should be rejected with a clear error."""
        with pytest.raises(ValueError, match="Amount must be positive"):
            db.add_transaction("2026-01-01", -50.0, "Food", "Expense", "Bad")

    def test_reject_zero_amount(self):
        """A zero amount should be rejected with a clear error."""
        with pytest.raises(ValueError, match="Amount must be positive"):
            db.add_transaction("2026-01-01", 0, "Food", "Expense", "Bad")

    def test_reject_invalid_type(self):
        """A type other than 'Income' or 'Expense' should be rejected."""
        with pytest.raises(ValueError, match="Type must be"):
            db.add_transaction("2026-01-01", 50.0, "Food", "Credit", "Bad")

    def test_reject_empty_category(self):
        """An empty category should be rejected with a clear error."""
        with pytest.raises(ValueError, match="Category cannot be empty"):
            db.add_transaction("2026-01-01", 50.0, "", "Expense", "Bad")

    def test_whitespace_category_stripped(self):
        """Extra spaces around a category name should be trimmed automatically."""
        db.add_transaction("2026-01-01", 50.0, "  Food  ", "Expense", "Test")
        df = db.get_all_transactions()
        assert df.iloc[0]["category"] == "Food"


class TestAccounts:
    """Tests for adding, updating, and deleting financial accounts."""

    def test_add_new_account(self):
        """Adding a new account should store it with the correct balance."""
        db.add_or_update_account("Test Account", "Checking", 1000.0)
        df = db.get_all_accounts()
        assert len(df) == 1
        assert df.iloc[0]["balance"] == 1000.0

    def test_update_existing_account(self):
        """Updating an existing account should change the balance, not create a duplicate."""
        db.add_or_update_account("My Savings", "Savings", 5000.0)
        db.add_or_update_account("My Savings", "Savings", 7500.0)
        df = db.get_all_accounts()
        assert len(df) == 1  # Should NOT create a duplicate
        assert df.iloc[0]["balance"] == 7500.0

    def test_update_changes_timestamp(self):
        """Updating an account should refresh its 'last updated' timestamp."""
        db.add_or_update_account("My Savings", "Savings", 5000.0)
        df1 = db.get_all_accounts()
        ts1 = df1.iloc[0]["last_updated"]

        db.add_or_update_account("My Savings", "Savings", 6000.0)
        df2 = db.get_all_accounts()
        ts2 = df2.iloc[0]["last_updated"]
        assert ts2 >= ts1

    def test_delete_account(self, sample_accounts):
        """Deleting an account should reduce the total count by one."""
        df = db.get_all_accounts()
        first_id = df.iloc[0]["id"]
        db.delete_account(first_id)
        assert len(db.get_all_accounts()) == len(df) - 1

    def test_net_worth_calculation(self, sample_accounts):
        """Net worth should equal the sum of all account balances."""
        net_worth = db.get_net_worth()
        assert net_worth == 3500.0 + 15000.0 + 45000.0

    def test_net_worth_empty_db(self):
        """Net worth should be $0 when there are no accounts."""
        assert db.get_net_worth() == 0.0

    def test_reject_empty_account_name(self):
        """An empty account name should be rejected."""
        with pytest.raises(ValueError, match="Account name cannot be empty"):
            db.add_or_update_account("", "Checking", 100.0)

    def test_reject_whitespace_account_name(self):
        """A whitespace-only account name should be rejected."""
        with pytest.raises(ValueError, match="Account name cannot be empty"):
            db.add_or_update_account("   ", "Checking", 100.0)


class TestBudgets:
    """Tests for setting, updating, and deleting monthly category budgets."""

    def test_set_budget(self):
        """Setting a budget should store the category and limit."""
        db.set_budget("Food", 500.0)
        df = db.get_all_budgets()
        assert len(df) == 1
        assert df.iloc[0]["category"] == "Food"
        assert df.iloc[0]["monthly_limit"] == 500.0

    def test_update_budget(self):
        """Setting a budget for the same category again should update (not duplicate) it."""
        db.set_budget("Food", 500.0)
        db.set_budget("Food", 750.0)
        df = db.get_all_budgets()
        assert len(df) == 1
        assert df.iloc[0]["monthly_limit"] == 750.0

    def test_delete_budget(self):
        """Deleting a budget should remove it completely."""
        db.set_budget("Food", 500.0)
        df = db.get_all_budgets()
        db.delete_budget(df.iloc[0]["id"])
        assert len(db.get_all_budgets()) == 0

    def test_reject_zero_budget(self):
        """A zero budget limit should be rejected."""
        with pytest.raises(ValueError, match="Budget limit must be positive"):
            db.set_budget("Food", 0)

    def test_multiple_budgets(self):
        """You should be able to set budgets for multiple categories."""
        db.set_budget("Food", 500.0)
        db.set_budget("Housing", 1500.0)
        db.set_budget("Entertainment", 200.0)
        df = db.get_all_budgets()
        assert len(df) == 3


class TestCSVImportExport:
    """Tests for importing transactions from CSV files and exporting them."""

    def test_export_empty(self):
        """Exporting when there are no transactions should return None."""
        result = db.export_transactions_csv()
        assert result is None

    def test_export_with_data(self, sample_transactions):
        """Exporting should produce a CSV string containing all transaction data."""
        csv = db.export_transactions_csv()
        assert csv is not None
        assert "Salary" in csv
        assert "Housing" in csv

    def test_roundtrip_import_export(self):
        """Exporting then re-importing should recreate the same transactions."""
        db.add_transaction("2026-06-01", 100.0, "Salary", "Income", "Test")
        db.add_transaction("2026-06-02", 50.0, "Food", "Expense", "Lunch")
        csv = db.export_transactions_csv()

        # Clear all transactions
        df = db.get_all_transactions()
        for _, row in df.iterrows():
            db.delete_transaction(row["id"])
        assert len(db.get_all_transactions()) == 0

        # Re-import from the CSV
        imported, errors = db.import_transactions_csv(csv)
        assert imported == 2
        assert errors is None

    def test_import_missing_columns(self):
        """Importing a CSV with missing required columns should fail with a clear message."""
        csv = "name,value\nfoo,bar\n"
        imported, errors = db.import_transactions_csv(csv)
        assert imported == 0
        assert "Missing required columns" in errors

    def test_import_invalid_type(self):
        """Importing a row with an invalid type (not Income/Expense) should be reported."""
        csv = "date,amount,category,type,description\n2026-01-01,100,Food,Debit,bad\n"
        imported, errors = db.import_transactions_csv(csv)
        assert imported == 0
        assert "Type must be" in errors

    def test_import_negative_amount(self):
        """Importing a row with a negative amount should be reported as an error."""
        csv = "date,amount,category,type,description\n2026-01-01,-100,Food,Expense,bad\n"
        imported, errors = db.import_transactions_csv(csv)
        assert imported == 0
        assert "Amount must be positive" in errors


class TestDatabaseBackupRestore:
    """Tests for backing up and restoring the entire database file."""

    def test_export_database(self, sample_transactions):
        """Exporting the database should return non-empty bytes."""
        data = db.export_database()
        assert isinstance(data, bytes)
        assert len(data) > 0

    def test_restore_database(self, sample_transactions):
        """Restoring a backup should bring the database back to its previous state."""
        # Export current state (4 transactions from sample data)
        backup = db.export_database()

        # Add more data so the database now has 5 transactions
        db.add_transaction("2026-12-01", 999.0, "Bonus", "Income", "Year-end")
        assert len(db.get_all_transactions()) == 5

        # Restore from backup — should go back to 4 transactions
        success, msg = db.import_database(backup)
        assert success
        assert len(db.get_all_transactions()) == 4

    def test_restore_invalid_file(self):
        """Restoring from a file that isn't a valid database should fail gracefully."""
        success, msg = db.import_database(b"not a database")
        assert not success
