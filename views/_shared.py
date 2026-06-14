"""
_shared.py — Small UI helpers reused across multiple views.

Holds:
  * confirm_delete_dialog — one shared confirmation pop-up used by the
    transactions, accounts, and budgets delete flows so each one doesn't
    have to define its own near-identical @st.dialog block.
  * render_currency_selector — the sidebar drop-down that lets the user
    switch the display currency ($/£/€). Called once from app.py so it
    appears on every page.
"""

from typing import Callable
import streamlit as st

import database as db


def signed_money(amount: float, t_type: str) -> str:
    """Format an amount with a leading +/- so income and expenses read apart at a glance.

    Income shows as "+$75.00", Expense as "-$75.00". Uses the same currency
    formatting as everywhere else via db.format_money().
    """
    sign = "-" if t_type == "Expense" else "+"
    return f"{sign}{db.format_money(abs(amount))}"


def confirm_delete_dialog(title: str, body: str, on_confirm: Callable[[], None],
                          key_suffix: str, caption: str = "This cannot be undone.",
                          confirm_label: str = "Delete") -> None:
    """Open a two-button confirmation pop-up (Cancel / Delete).

    Parameters
    ----------
    title : str
        Heading shown at the top of the pop-up (e.g. "Delete Transaction?").
    body : str
        Warning message shown inside the pop-up (markdown supported).
    on_confirm : Callable
        Function to run when the user clicks the confirm button.
    key_suffix : str
        A unique-ish string (often the row ID) so Streamlit can tell the
        Cancel/Confirm buttons apart from any other buttons on the page.
    caption : str
        Small grey text under the warning. Defaults to "This cannot be undone."
    confirm_label : str
        Text on the confirm button. Defaults to "Delete".
    """

    @st.dialog(title)
    def _dialog() -> None:
        st.warning(body)
        st.caption(caption)
        c1, c2 = st.columns(2)
        if c1.button("Cancel", use_container_width=True, key=f"cancel_{key_suffix}"):
            st.rerun()
        if c2.button(confirm_label, type="primary", use_container_width=True,
                     key=f"confirm_{key_suffix}"):
            on_confirm()
            st.rerun()

    _dialog()


def render_currency_selector() -> None:
    """Draw the "Display Currency" drop-down in the sidebar.

    The selection is saved to the database so it persists between sessions.
    Changing the currency triggers a rerun, which re-renders every page with
    the new symbol via db.format_money().
    """
    current = db.get_currency()
    options = db.SUPPORTED_CURRENCIES
    idx = options.index(current) if current in options else 0

    st.sidebar.markdown("### 💱 Display Currency")
    choice = st.sidebar.selectbox(
        "Currency symbol",
        options,
        index=idx,
        key="currency_selector",
        label_visibility="collapsed",
        help="Switches the symbol shown next to amounts everywhere in the app. "
             "Does NOT convert numbers — your stored values stay the same.",
    )
    if choice != current:
        db.set_currency(choice)
        st.rerun()
