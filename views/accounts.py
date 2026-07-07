"""
accounts.py — Track account balances, net worth, and database backups.

Add or update bank accounts, retirement funds, and investments.
Download or restore database backups from this page.
"""

import streamlit as st
import database as db
from database import ACCOUNT_TYPES
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
    with st.form("manage_account_form"):
        st.subheader("Update an Account Balance")
        col1, col2 = st.columns(2)
        with col1:
            a_name = st.text_input("Account Name (e.g. 'Fidelity 401k')")
            a_type = st.selectbox("Account Type", ACCOUNT_TYPES)
        with col2:
            a_kind = st.radio(
                "Is this something you own or owe?",
                ["I own it (asset)", "I owe it (liability)"],
                help="Assets are savings, investments, property. "
                     "Liabilities are credit cards, loans, mortgages.",
            )
            a_balance = st.number_input(
                f"Amount ({db.get_currency()})",
                min_value=0.00, value=0.00, format="%.2f",
                help="Just enter the amount as a positive number — "
                     "the choice above handles owned vs owed.",
            )

        st.info("If this is a new account, it will be added. If the name already exists (case-insensitive), its balance will be updated.")

        if st.form_submit_button("Save Balance Update", use_container_width=True):
            if not a_name.strip():
                st.error("Account name cannot be empty.")
            else:
                # Liabilities are stored as negative balances so net worth = assets - liabilities.
                signed_balance = -a_balance if a_kind.startswith("I owe") else a_balance
                db.add_or_update_account(a_name, a_type, signed_balance)
                st.toast(f"Successfully updated '{a_name}' balance!", icon="✅")
                st.rerun()

    st.markdown("---")

    # --- View accounts and pick one to delete ---
    st.subheader("Current Asset Breakdown")
    df = db.get_all_accounts()

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
