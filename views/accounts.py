"""
accounts.py — Track account balances, net worth, and database backups.

Add or update bank accounts, retirement funds, and investments.
Download or restore database backups from this page.
"""

import streamlit as st
import database as db
from database import ACCOUNT_TYPES, LIABILITY_TYPES
from views._shared import confirm_delete_dialog
import os


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
        "Track assets (savings, investments, property) and liabilities "
        "(credit cards, mortgages, loans) to get a true net-worth picture. "
        "Updating an account simply overrides its previous balance."
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
    st.subheader("Current Asset Breakdown")

    # Split into assets (positive balances) and liabilities (negative) so the
    # net-worth number is broken down into "what you own" vs "what you owe".
    # Liabilities are shown as a positive magnitude under their own label.
    assets = float(df[df['balance'] > 0]['balance'].sum()) if not df.empty else 0.0
    liabilities = abs(float(df[df['balance'] < 0]['balance'].sum())) if not df.empty else 0.0
    net_worth = assets - liabilities

    a1, a2, a3 = st.columns(3)
    a1.metric("Total Assets", db.format_money(assets))
    a2.metric("Total Liabilities", db.format_money(liabilities))
    a3.metric("Net Worth", db.format_money(net_worth))

    if not df.empty:
        st.dataframe(df[['name', 'type', 'balance', 'last_updated']], use_container_width=True, hide_index=True)

        st.markdown("### Delete Account")
        d1, d2 = st.columns([3, 1])
        with d1:
            options = {f"{r['name']} ({r['type']})": r['id'] for _, r in df.iterrows()}
            label = st.selectbox("Select Account", list(options.keys()))
        with d2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Delete Selected", type="primary"):
                sel_id = options[label]
                sel = df[df['id'] == sel_id].iloc[0]
                _open_delete_account_dialog(int(sel_id), sel['name'], sel['type'], float(sel['balance']))
    else:
        st.info("You haven't added any accounts yet. Track your 401k, savings, and investments above!")
        if st.button("✨ Load demo data", key="demo_from_accounts"):
            count = db.load_demo_data()
            if count:
                st.toast(f"Loaded {count} sample transactions + 3 accounts.", icon="✨")
                st.rerun()

    # --- Database backup & restore ---
    st.markdown("---")
    st.subheader("💾 Database Backup & Restore")

    backup_col, restore_col = st.columns(2)

    with backup_col:
        st.markdown("#### Download Backup")
        st.caption("Download your entire database file for safekeeping.")
        if os.path.exists(db.DB_PATH):
            st.download_button("⬇️ Download Database Backup", data=db.export_database(),
                               file_name="finance_backup.db", mime="application/octet-stream",
                               use_container_width=True)
        else:
            st.info("No database file found.")

    with restore_col:
        st.markdown("#### Restore from Backup")
        st.caption("Upload a previously downloaded backup to restore your data. "
                   "Your current data is saved as finance.db.bak before being replaced.")
        uploaded_db = st.file_uploader("Upload .db file", type=["db"],
                                       help="Upload a finance.db backup file to restore your data.")
        if uploaded_db is not None and st.button("🔄 Restore Database", type="primary", use_container_width=True):
            success, message = db.import_database(uploaded_db.getvalue())
            if success:
                st.toast(message, icon="✅")
                st.rerun()
            else:
                st.error(message)
