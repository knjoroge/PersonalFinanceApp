"""Automated tests for all database operations in database.py."""

import pytest
import pandas as pd
import database as db


class TestInitDB:

    def test_tables_created(self):
        """Both transactions and accounts tables should exist after init."""
        assert isinstance(db.get_all_transactions(), pd.DataFrame)
        assert isinstance(db.get_all_accounts(), pd.DataFrame)

    def test_idempotent_init(self):
        """Calling init_db twice should be safe and not duplicate data."""
        db.init_db()
        db.init_db()
        assert db.get_all_transactions().empty


class TestTransactions:

    def test_add_and_retrieve(self):
        """A new transaction should appear when fetched."""
        db.add_transaction("2026-03-01", 100.0, "Salary", "Income", "Test")
        df = db.get_all_transactions()
        assert len(df) == 1
        assert df.iloc[0]["amount"] == 100.0
        assert df.iloc[0]["category"] == "Salary"

    def test_add_multiple(self, sample_transactions):
        """Sample fixture should create exactly 4 transactions."""
        assert len(db.get_all_transactions()) == 4

    def test_delete(self, sample_transactions):
        """Deleting a transaction should reduce the count by one."""
        df = db.get_all_transactions()
        db.delete_transaction(df.iloc[0]["id"])
        assert len(db.get_all_transactions()) == len(df) - 1

    def test_delete_nonexistent(self):
        """Deleting a missing ID should be a silent no-op."""
        db.delete_transaction(99999)

    def test_update(self, sample_transactions):
        """Updating a transaction should change its stored values."""
        df = db.get_all_transactions()
        first_id = df.iloc[0]["id"]
        db.update_transaction(first_id, "2026-02-01", 9999.99, "Bonus", "Income", "Updated")
        updated = db.get_all_transactions()
        row = updated[updated["id"] == first_id].iloc[0]
        assert row["amount"] == 9999.99
        assert row["category"] == "Bonus"
        assert row["description"] == "Updated"

    def test_ordered_by_date_desc(self, sample_transactions):
        """Transactions should come back newest first."""
        dates = list(db.get_all_transactions()["date"])
        assert dates == sorted(dates, reverse=True)

    def test_reject_invalid_date(self):
        """Bad date format should raise ValueError."""
        with pytest.raises(ValueError, match="Date must be in YYYY-MM-DD format"):
            db.add_transaction("banana", 50.0, "Food", "Expense", "Bad")

    def test_reject_negative_amount(self):
        """Negative amount should raise ValueError."""
        with pytest.raises(ValueError, match="Amount must be positive"):
            db.add_transaction("2026-01-01", -50.0, "Food", "Expense", "Bad")

    def test_reject_zero_amount(self):
        """Zero amount should raise ValueError."""
        with pytest.raises(ValueError, match="Amount must be positive"):
            db.add_transaction("2026-01-01", 0, "Food", "Expense", "Bad")

    def test_reject_invalid_type(self):
        """Invalid type should raise ValueError."""
        with pytest.raises(ValueError, match="Type must be"):
            db.add_transaction("2026-01-01", 50.0, "Food", "Credit", "Bad")

    def test_reject_empty_category(self):
        """Empty category should raise ValueError."""
        with pytest.raises(ValueError, match="Category cannot be empty"):
            db.add_transaction("2026-01-01", 50.0, "", "Expense", "Bad")

    def test_whitespace_category_stripped(self):
        """Extra spaces around a category should be trimmed."""
        db.add_transaction("2026-01-01", 50.0, "  Food  ", "Expense", "Test")
        assert db.get_all_transactions().iloc[0]["category"] == "Food"


class TestAccounts:

    def test_add_new(self):
        """Adding a new account should store the correct balance."""
        db.add_or_update_account("Test Account", "Checking", 1000.0)
        df = db.get_all_accounts()
        assert len(df) == 1
        assert df.iloc[0]["balance"] == 1000.0

    def test_update_existing(self):
        """Updating should change balance without creating a duplicate."""
        db.add_or_update_account("My Savings", "Savings", 5000.0)
        db.add_or_update_account("My Savings", "Savings", 7500.0)
        df = db.get_all_accounts()
        assert len(df) == 1
        assert df.iloc[0]["balance"] == 7500.0

    def test_update_changes_timestamp(self):
        """Updating an account should refresh its timestamp."""
        db.add_or_update_account("My Savings", "Savings", 5000.0)
        ts1 = db.get_all_accounts().iloc[0]["last_updated"]
        db.add_or_update_account("My Savings", "Savings", 6000.0)
        ts2 = db.get_all_accounts().iloc[0]["last_updated"]
        assert ts2 >= ts1

    def test_delete(self, sample_accounts):
        """Deleting an account should reduce the count by one."""
        df = db.get_all_accounts()
        db.delete_account(df.iloc[0]["id"])
        assert len(db.get_all_accounts()) == len(df) - 1

    def test_net_worth(self, sample_accounts):
        """Net worth should equal the sum of all balances."""
        assert db.get_net_worth() == 3500.0 + 15000.0 + 45000.0

    def test_net_worth_empty(self):
        """Net worth should be $0 with no accounts."""
        assert db.get_net_worth() == 0.0

    def test_reject_empty_name(self):
        """Empty account name should raise ValueError."""
        with pytest.raises(ValueError, match="Account name cannot be empty"):
            db.add_or_update_account("", "Checking", 100.0)

    def test_reject_whitespace_name(self):
        """Whitespace-only name should raise ValueError."""
        with pytest.raises(ValueError, match="Account name cannot be empty"):
            db.add_or_update_account("   ", "Checking", 100.0)


class TestBudgets:

    def test_set(self):
        """Setting a budget should store category and limit."""
        db.set_budget("Food", 500.0)
        df = db.get_all_budgets()
        assert len(df) == 1
        assert df.iloc[0]["category"] == "Food"
        assert df.iloc[0]["monthly_limit"] == 500.0

    def test_update(self):
        """Setting the same category again should update, not duplicate."""
        db.set_budget("Food", 500.0)
        db.set_budget("Food", 750.0)
        df = db.get_all_budgets()
        assert len(df) == 1
        assert df.iloc[0]["monthly_limit"] == 750.0

    def test_delete(self):
        """Deleting a budget should remove it completely."""
        db.set_budget("Food", 500.0)
        db.delete_budget(db.get_all_budgets().iloc[0]["id"])
        assert len(db.get_all_budgets()) == 0

    def test_reject_zero(self):
        """Zero budget limit should raise ValueError."""
        with pytest.raises(ValueError, match="Budget limit must be positive"):
            db.set_budget("Food", 0)

    def test_multiple(self):
        """Multiple budgets for different categories should all be stored."""
        db.set_budget("Food", 500.0)
        db.set_budget("Housing", 1500.0)
        db.set_budget("Entertainment", 200.0)
        assert len(db.get_all_budgets()) == 3


class TestCSVImportExport:

    def test_export_empty(self):
        """Exporting with no data should return None."""
        assert db.export_transactions_csv() is None

    def test_export_with_data(self, sample_transactions):
        """Export should produce CSV containing the transaction data."""
        csv = db.export_transactions_csv()
        assert csv is not None
        assert "Salary" in csv and "Housing" in csv

    def test_roundtrip(self):
        """Export then re-import should recreate the same transactions."""
        db.add_transaction("2026-06-01", 100.0, "Salary", "Income", "Test")
        db.add_transaction("2026-06-02", 50.0, "Food", "Expense", "Lunch")
        csv = db.export_transactions_csv()

        for _, row in db.get_all_transactions().iterrows():
            db.delete_transaction(row["id"])
        assert len(db.get_all_transactions()) == 0

        imported, errors = db.import_transactions_csv(csv)
        assert imported == 2
        assert errors is None

    def test_import_missing_columns(self):
        """CSV with missing columns should fail with a clear message."""
        imported, errors = db.import_transactions_csv("name,value\nfoo,bar\n")
        assert imported == 0
        assert "Missing a date column" in errors

    def test_import_invalid_type(self):
        """When the type column has an unrecognised value, amount sign decides Income vs Expense."""
        csv = "date,amount,category,type,description\n2026-01-01,100,Food,Debit,bad\n"
        imported, errors = db.import_transactions_csv(csv)
        assert imported == 1
        df = db.get_all_transactions()
        assert df.iloc[0]["type"] == "Income"  # positive amount → Income

    def test_import_negative_amount(self):
        """CSV row with negative amount should be smartly converted to Expense."""
        csv = "date,amount,category,type,description\n2026-01-01,-100,Food,Expense,bad\n"
        imported, errors = db.import_transactions_csv(csv)
        assert imported == 1
        df = db.get_all_transactions()
        assert df.iloc[0]["amount"] == 100.0
        assert df.iloc[0]["type"] == "Expense"


class TestDatabaseBackupRestore:

    def test_export(self, sample_transactions):
        """Exporting should return non-empty bytes."""
        data = db.export_database()
        assert isinstance(data, bytes) and len(data) > 0

    def test_restore(self, sample_transactions):
        """Restoring a backup should bring the DB back to its previous state."""
        backup = db.export_database()
        db.add_transaction("2026-12-01", 999.0, "Bonus", "Income", "Year-end")
        assert len(db.get_all_transactions()) == 5

        success, msg = db.import_database(backup)
        assert success
        assert len(db.get_all_transactions()) == 4

    def test_restore_invalid(self):
        """Restoring garbage data should fail gracefully."""
        success, msg = db.import_database(b"not a database")
        assert not success
