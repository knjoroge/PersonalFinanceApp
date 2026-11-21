"""
accounts.py — Track account balances and net worth.

Add or update bank accounts, retirement funds, investments and debts.
"""

import streamlit as st
import pandas as pd
import database as db
from database import ACCOUNT_TYPES, LIABILITY_TYPES
from views._shared import confirm_delete_dialog, sample_data_button


def _open_delete_account_dialog(account_id, name, account_type, balance):
    """Open the "are you sure?" pop-up before permanently deleting an account."""
    body = f"Delete account **{name}** ({account_type}) with balance **{db.format_money(balance)}**?"
    caption = ("This only removes the account record — your transactions are not affected. "
               "This cannot be undone.")
    confirm_delete_dialog(
        title="Delete Account?",
        body=body,
        caption=caption,
        on_confirm=lambda: (db.delete_account(account_id), st.toast("Account deleted.", icon="🗑️")),
        key_suffix=f"acct_{account_id}",
    )


def render_accounts():
    """Top-level entry point for the Net Worth & Accounts page."""

    st.header("🏦 Net Worth & Accounts")
    st.markdown(
        "Add what you **own** (savings, investments, property) and what you **owe** "
        "(credit cards, mortgages, loans). Your **net worth** is what you own minus what you owe. "
        "Once a month or so, update each account with its latest balance."
    )

    # --- Add or update an account ---
    st.subheader("Update an Account Balance")
    df = db.get_all_accounts()

    # Pick an existing account (so there's no retyping its exact name each
    # month) or add a new one. This sits outside the form so choosing an
    # account instantly pre-fills its type and current balance below.
    new_label = "➕ Add a new account"
    existing = {r["name"]: r for _, r in df.iterrows()} if not df.empty else {}
    choice = st.selectbox("Which account?", [new_label] + list(existing.keys()))
    current = existing.get(choice)

    with st.form("manage_account_form"):
        col1, col2 = st.columns(2)
        with col1:
            if current is None:
                a_name = st.text_input("Account Name (e.g. 'Fidelity 401k')")
            else:
                a_name = choice
                st.text_input("Account Name", value=choice, disabled=True)
            type_idx = 0
            if current is not None and current["type"] in ACCOUNT_TYPES:
                type_idx = ACCOUNT_TYPES.index(current["type"])
            a_type = st.selectbox(
                "Account Type", ACCOUNT_TYPES, index=type_idx, key=f"acct_type_{choice}",
                help="Credit Card, Mortgage, Loan and Other Liabilities count as money you owe. "
                     "Everything else counts as money you own.",
            )
        with col2:
            a_balance = st.number_input(
                f"Current balance ({db.get_currency()})",
                min_value=0.00, format="%.2f", key=f"acct_bal_{choice}",
                value=abs(float(current["balance"])) if current is not None else 0.00,
                help="Enter a positive number, even for debts. "
                     "The account type decides whether it's owned or owed.",
            )

        button_label = "Add Account" if current is None else "Save New Balance"
        if st.form_submit_button(button_label, use_container_width=True):
            if not a_name.strip():
                st.error("Please give the account a name.")
            else:
                # Liabilities are stored as negative balances so net worth = assets - liabilities.
                signed_balance = -a_balance if a_type in LIABILITY_TYPES else a_balance
                db.add_or_update_account(a_name, a_type, signed_balance)
                st.toast(f"Saved '{a_name.strip()}'!", icon="✅")
                st.rerun()

    st.markdown("---")

    # --- View accounts and pick one to delete ---
    st.subheader("Your accounts")

    # Split into assets (positive balances) and liabilities (negative) so the
    # net-worth number is broken down into "what you own" vs "what you owe".
    # Liabilities are shown as a positive magnitude under their own label.
    assets = float(df[df['balance'] > 0]['balance'].sum()) if not df.empty else 0.0
    liabilities = abs(float(df[df['balance'] < 0]['balance'].sum())) if not df.empty else 0.0
    net_worth = assets - liabilities

    a1, a2, a3 = st.columns(3)
    a1.metric("What you own", db.format_money(assets))
    a2.metric("What you owe", db.format_money(liabilities))
    a3.metric("Net worth", db.format_money(net_worth), help="What you own minus what you owe.")

    if not df.empty:
        table = df[['name', 'type', 'balance', 'last_updated']].copy()
        table['balance'] = table['balance'].map(db.format_money)
        table['last_updated'] = pd.to_datetime(table['last_updated']).dt.strftime('%d %b %Y')
        table.columns = ['Account', 'Type', 'Balance', 'Last updated']
        st.dataframe(table, use_container_width=True, hide_index=True)

        st.markdown("### Delete an account")
        d1, d2 = st.columns([3, 1])
        with d1:
            options = {f"{r['name']} ({r['type']})": r['id'] for _, r in df.iterrows()}
            label = st.selectbox("Which account?", list(options.keys()), key="delete_account_choice")
        with d2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Delete", type="primary"):
                sel_id = options[label]
                sel = df[df['id'] == sel_id].iloc[0]
                _open_delete_account_dialog(int(sel_id), sel['name'], sel['type'], float(sel['balance']))
    else:
        st.info("You haven't added any accounts yet. Add your first one above.")
        if db.get_all_transactions().empty:
            sample_data_button(key="sample_from_accounts")
