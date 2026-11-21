"""Smoke tests: open every page of the real app and check nothing crashes.

Uses Streamlit's built-in AppTest, which runs app.py the same way the
browser would, but without needing a browser.
"""

import os
import pytest
from streamlit.testing.v1 import AppTest

import database as db

APP = os.path.join(os.path.dirname(__file__), "..", "app.py")
PAGES = ["Dashboard", "Transactions", "Net Worth & Accounts", "AI Advisor"]


def open_page(page: str) -> AppTest:
    """Start the app, click a page in the sidebar, and return the result."""
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.sidebar.radio[0].set_value(page).run()
    return at


@pytest.mark.parametrize("page", PAGES)
def test_page_opens_with_no_data(page):
    at = open_page(page)
    assert not at.exception


@pytest.mark.parametrize("page", PAGES)
def test_page_opens_with_demo_data(page):
    db.load_demo_data()
    at = open_page(page)
    assert not at.exception


def test_update_existing_account_from_picker():
    """Picking an existing account pre-fills it, and saving updates (not duplicates) it."""
    db.add_or_update_account("Amex Card", "Credit Card", -300.0)
    at = open_page("Net Worth & Accounts")

    picker = next(s for s in at.selectbox if s.label == "Which account?")
    picker.set_value("Amex Card").run()

    balance = next(n for n in at.number_input if n.label.startswith("Current balance"))
    assert balance.value == 300.0  # shown as a positive number
    balance.set_value(250.0)
    next(b for b in at.button if b.label == "Save New Balance").click().run()

    accounts = db.get_all_accounts()
    assert len(accounts) == 1
    assert accounts.iloc[0]["balance"] == -250.0  # still stored as a debt
