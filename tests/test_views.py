"""Tests for view-layer helpers (pure-data logic, no Streamlit rendering)."""

import datetime
import pandas as pd

from views._shared import signed_money
from views.transactions import _apply_filters


def _df():
    """Minimal transactions frame with string dates, as get_all_transactions returns."""
    return pd.DataFrame({
        "id": [1, 2, 3],
        "date": ["2026-01-05", "2026-02-10", "2026-03-15"],
        "type": ["Income", "Expense", "Expense"],
        "category": ["Salary", "Food", "Food"],
        "amount": [3000.0, 50.0, 75.0],
        "description": ["Pay", "Lunch", "Dinner"],
    })


class TestSignedMoney:

    def test_income_gets_plus(self):
        assert signed_money(75, "Income").startswith("+")

    def test_expense_gets_minus(self):
        assert signed_money(75, "Expense").startswith("-")

    def test_magnitude_is_absolute(self):
        # Sign comes from the type, not the stored value.
        assert signed_money(-75, "Expense") == signed_money(75, "Expense")


class TestApplyFiltersDateRange:

    def test_no_dates_returns_all(self):
        assert len(_apply_filters(_df(), "All", "All", "")) == 3

    def test_date_range_narrows(self):
        start = datetime.date(2026, 2, 1)
        end = datetime.date(2026, 2, 28)
        out = _apply_filters(_df(), "All", "All", "", start, end)
        assert len(out) == 1 and out.iloc[0]["description"] == "Lunch"

    def test_date_range_inclusive_of_bounds(self):
        start = datetime.date(2026, 1, 5)
        end = datetime.date(2026, 3, 15)
        assert len(_apply_filters(_df(), "All", "All", "", start, end)) == 3

    def test_date_combines_with_type_filter(self):
        start = datetime.date(2026, 1, 1)
        end = datetime.date(2026, 12, 31)
        out = _apply_filters(_df(), "Expense", "All", "", start, end)
        assert len(out) == 2 and set(out["type"]) == {"Expense"}
