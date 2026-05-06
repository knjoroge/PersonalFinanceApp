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


class TestBankCSVFormats:
    """Test that the smart importer handles real-world bank CSV formats."""

    def test_chase(self):
        """Chase: Date, Description, Amount (negative = expense), Type, Balance."""
        csv = (
            "Date,Description,Amount,Type,Balance\n"
            "01/15/2026,STARBUCKS STORE,-4.95,Sale,1234.56\n"
            "01/14/2026,PAYROLL DEPOSIT,3500.00,Credit,1239.51\n"
        )
        imported, errors = db.import_transactions_csv(csv)
        assert imported == 2
        assert errors is None
        df = db.get_all_transactions()
        starbucks = df[df["description"] == "STARBUCKS STORE"].iloc[0]
        assert starbucks["type"] == "Expense"
        assert starbucks["amount"] == 4.95
        payroll = df[df["description"] == "PAYROLL DEPOSIT"].iloc[0]
        assert payroll["type"] == "Income"
        assert payroll["amount"] == 3500.00

    def test_monzo(self):
        """Monzo: Date, Time, Type, Name, Category, Amount, Currency, etc."""
        csv = (
            "Date,Time,Type,Name,Emoji,Category,Amount,Currency,Notes and #tags\n"
            "15/01/2026,10:30:00,Card payment,Tesco,,Groceries,-22.50,GBP,Weekly shop\n"
            "14/01/2026,09:00:00,Faster payment,EMPLOYER,,Income,2800.00,GBP,Salary Jan\n"
        )
        imported, errors = db.import_transactions_csv(csv)
        assert imported == 2
        assert errors is None
        df = db.get_all_transactions()
        tesco = df[df["description"] == "Tesco"].iloc[0]
        assert tesco["type"] == "Expense"
        assert tesco["amount"] == 22.50
        assert tesco["category"] == "Groceries"

    def test_natwest(self):
        """NatWest: Date, Narrative, Debit, Credit, Balance."""
        csv = (
            "Date,Narrative,Debit,Credit,Balance\n"
            "15/01/2026,AMAZON PURCHASE,45.99,,1200.00\n"
            "14/01/2026,SALARY,,3000.00,1245.99\n"
        )
        imported, errors = db.import_transactions_csv(csv)
        assert imported == 2
        assert errors is None
        df = db.get_all_transactions()
        amazon = df[df["description"] == "AMAZON PURCHASE"].iloc[0]
        assert amazon["type"] == "Expense"
        assert amazon["amount"] == 45.99
        salary = df[df["description"] == "SALARY"].iloc[0]
        assert salary["type"] == "Income"
        assert salary["amount"] == 3000.00

    def test_barclays(self):
        """Barclays variant: Date, Description, Money Out, Money In, Balance."""
        csv = (
            "Date,Description,Money Out,Money In,Balance\n"
            "15/01/2026,NETFLIX,15.99,,500.00\n"
            "14/01/2026,BANK TRANSFER,,200.00,515.99\n"
        )
        imported, errors = db.import_transactions_csv(csv)
        assert imported == 2
        df = db.get_all_transactions()
        netflix = df[df["description"] == "NETFLIX"].iloc[0]
        assert netflix["type"] == "Expense"
        assert netflix["amount"] == 15.99

    def test_wells_fargo_no_header(self):
        """Wells Fargo: no header row — columns are Date, Amount, *, *, Description."""
        csv = (
            "01/15/2026,-85.50,,1234,COSTCO WHOLESALE\n"
            "01/14/2026,1500.00,,0,PAYCHECK DIRECT DEP\n"
        )
        imported, errors = db.import_transactions_csv(csv)
        assert imported == 2
        assert errors is None
        df = db.get_all_transactions()
        costco = df[df["description"] == "COSTCO WHOLESALE"].iloc[0]
        assert costco["type"] == "Expense"
        assert costco["amount"] == 85.50

    def test_revolut(self):
        """Revolut: Completed Date, Description, Amount, Currency, Category."""
        csv = (
            "Completed Date,Description,Amount,Currency,Category\n"
            "2026-01-15,Uber Eats,-18.40,GBP,Restaurants\n"
            "2026-01-14,Salary,4200.00,GBP,Income\n"
        )
        imported, errors = db.import_transactions_csv(csv)
        assert imported == 2
        assert errors is None
        df = db.get_all_transactions()
        uber = df[df["description"] == "Uber Eats"].iloc[0]
        assert uber["type"] == "Expense"
        assert uber["amount"] == 18.40
        assert uber["category"] == "Restaurants"

    def test_bank_of_america(self):
        """Bank of America: Date, Description, Amount."""
        csv = (
            "Date,Description,Amount\n"
            "01/20/2026,WHOLE FOODS MARKET,-67.23\n"
            "01/19/2026,VENMO PAYMENT,150.00\n"
        )
        imported, errors = db.import_transactions_csv(csv)
        assert imported == 2
        df = db.get_all_transactions()
        whole_foods = df[df["description"] == "WHOLE FOODS MARKET"].iloc[0]
        assert whole_foods["type"] == "Expense"
        assert whole_foods["amount"] == 67.23
