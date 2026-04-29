"""
accounts.py — The page for tracking account balances and net worth.

This view lets you:
  - Add or update balances for your bank accounts, retirement funds, etc.
  - See your total net worth (the sum of all account balances)
  - Delete accounts you no longer want to track
  - Download a full backup of your database, or restore from a previous backup
"""

import streamlit as st
import pandas as pd
import database as db
import os


def render_accounts():
    """Renders the Net Worth & Accounts page."""

    st.header("🏦 Net Worth & Accounts")

    st.markdown("""
    Keep track of your total net worth. Enter the current total balance for any of your accounts below. 
    Updating an account will simply override its previous balance.
    """)

    # --- Add or Update an Account ---
    with st.form("manage_account_form"):
        st.subheader("Update an Account Balance")

        col1, col2 = st.columns(2)
        with col1:
            a_name = st.text_input("Account Name (e.g. 'Fidelity 401k')")
            a_type = st.selectbox(
                "Account Type",
                ["Checking", "Savings", "401k", "Pension", "Shares/Brokerage",
                 "Real Estate", "Other Assets"]
            )
        with col2:
            a_balance = st.number_input("Current Balance ($)", min_value=0.00, format="%.2f")

        st.info("If this is a new account, it will be added. If the Account Name already exists, its balance will be updated.")

        submitted = st.form_submit_button("Save Balance Update", use_container_width=True)

        if submitted:
            if not a_name.strip():
                st.error("Account name cannot be empty.")
            else:
                db.add_or_update_account(a_name, a_type, a_balance)
                st.toast(f"Successfully updated '{a_name}' balance!", icon="✅")
                st.rerun()

    st.markdown("---")

    # --- View Current Accounts ---
    st.subheader("Current Asset Breakdown")

    net_worth = db.get_net_worth()
    st.metric("Total Tracked Net Worth", f"${net_worth:,.2f}")

    df = db.get_all_accounts()

    if not df.empty:
        # Show all accounts in a table
        st.dataframe(
            df[['name', 'type', 'balance', 'last_updated']],
            use_container_width=True,
            hide_index=True
        )

        # Option to delete an account
        st.markdown("### Delete Account")
        del_col1, del_col2 = st.columns([3, 1])
        with del_col1:
            # Build a dropdown mapping display labels to database IDs
            account_options = {f"{row['name']} ({row['type']})": row['id']
                               for _, row in df.iterrows()}
            account_label = st.selectbox("Select Account", list(account_options.keys()))
        with del_col2:
            st.markdown("<br>", unsafe_allow_html=True)  # Visual spacing
            if st.button("Delete Selected", type="primary"):
                acc_id = account_options[account_label]
                db.delete_account(acc_id)
                st.toast("Account deleted.", icon="🗑️")
                st.rerun()

    else:
        st.info("You haven't added any accounts yet. Track your 401k, savings, and investments above!")

    # --- Database Backup & Restore ---
    st.markdown("---")
    st.subheader("💾 Database Backup & Restore")

    backup_col, restore_col = st.columns(2)

    # Download a copy of the entire database
    with backup_col:
        st.markdown("#### Download Backup")
        st.caption("Download your entire database file for safekeeping.")
        if os.path.exists(db.DB_PATH):
            db_bytes = db.export_database()
            st.download_button(
                label="⬇️ Download Database Backup",
                data=db_bytes,
                file_name="finance_backup.db",
                mime="application/octet-stream",
                use_container_width=True
            )
        else:
            st.info("No database file found.")

    # Upload and restore from a previous backup
    with restore_col:
        st.markdown("#### Restore from Backup")
        st.caption("Upload a previously downloaded backup to restore your data.")
        uploaded_db = st.file_uploader(
            "Upload .db file",
            type=["db"],
            help="Upload a finance.db backup file to restore your data."
        )
        if uploaded_db is not None:
            if st.button("🔄 Restore Database", type="primary", use_container_width=True):
                success, message = db.import_database(uploaded_db.getvalue())
                if success:
                    st.toast(message, icon="✅")
                    st.rerun()
                else:
                    st.error(message)
