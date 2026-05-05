"""
accounts.py — Track account balances, net worth, and database backups.

Add or update bank accounts, retirement funds, and investments.
Download or restore database backups from this page.
"""

import streamlit as st
import database as db
import os


def render_accounts():
    """Render the Net Worth & Accounts page."""

    st.header("🏦 Net Worth & Accounts")
    st.markdown("Keep track of your total net worth. Updating an account simply overrides its previous balance.")

    # --- Add or update an account ---
    with st.form("manage_account_form"):
        st.subheader("Update an Account Balance")
        col1, col2 = st.columns(2)
        with col1:
            a_name = st.text_input("Account Name (e.g. 'Fidelity 401k')")
            a_type = st.selectbox("Account Type",
                                  ["Checking", "Savings", "401k", "Pension", "Shares/Brokerage",
                                   "Real Estate", "Other Assets"])
        with col2:
            a_balance = st.number_input("Current Balance ($)", min_value=0.00, format="%.2f")

        st.info("If this is a new account, it will be added. If the name already exists, its balance will be updated.")

        if st.form_submit_button("Save Balance Update", use_container_width=True):
            if not a_name.strip():
                st.error("Account name cannot be empty.")
            else:
                db.add_or_update_account(a_name, a_type, a_balance)
                st.toast(f"Successfully updated '{a_name}' balance!", icon="✅")
                st.rerun()

    st.markdown("---")

    # --- View accounts ---
    st.subheader("Current Asset Breakdown")
    net_worth = db.get_net_worth()
    st.metric("Total Tracked Net Worth", f"${net_worth:,.2f}")

    df = db.get_all_accounts()
    if not df.empty:
        st.dataframe(df[['name', 'type', 'balance', 'last_updated']], use_container_width=True, hide_index=True)

        # Delete an account
        st.markdown("### Delete Account")
        d1, d2 = st.columns([3, 1])
        with d1:
            options = {f"{r['name']} ({r['type']})": r['id'] for _, r in df.iterrows()}
            label = st.selectbox("Select Account", list(options.keys()))
        with d2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Delete Selected", type="primary"):
                db.delete_account(options[label])
                st.toast("Account deleted.", icon="🗑️")
                st.rerun()
    else:
        st.info("You haven't added any accounts yet. Track your 401k, savings, and investments above!")

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
        st.caption("Upload a previously downloaded backup to restore your data.")
        uploaded_db = st.file_uploader("Upload .db file", type=["db"],
                                       help="Upload a finance.db backup file to restore your data.")
        if uploaded_db is not None and st.button("🔄 Restore Database", type="primary", use_container_width=True):
            success, message = db.import_database(uploaded_db.getvalue())
            if success:
                st.toast(message, icon="✅")
                st.rerun()
            else:
                st.error(message)
