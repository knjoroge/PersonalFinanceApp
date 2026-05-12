"""
_shared.py — Small UI helpers reused across multiple views.

Right now this is just the confirm-delete dialog factory: every page that
deletes something (transactions, accounts, budgets) used to define its own
near-identical confirmation pop-up. The factory below replaces all of them.
"""

from typing import Callable
import streamlit as st


def confirm_delete_dialog(title: str, body: str, on_confirm: Callable[[], None],
                          key_suffix: str, caption: str = "This cannot be undone.",
                          confirm_label: str = "Delete") -> None:
    """Open a two-button confirmation pop-up (Cancel / Delete).

    Parameters
    ----------
    title : str
        Heading shown at the top of the pop-up (e.g. "Delete Transaction?").
    body : str
        The warning message shown inside the pop-up (supports markdown).
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
