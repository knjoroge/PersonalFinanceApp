"""
backup.py — Save a copy of all your data, or bring back a copy you saved.
"""

import os
import streamlit as st
import database as db


def render_backup():
    """Top-level entry point for the Backup page."""
    st.header("💾 Backup")
    st.markdown(
        "All your data lives in one file on this computer. "
        "The app already saves a copy every day for the last 7 days, "
        "but it's smart to also keep your own copy somewhere safe, "
        "like a USB stick or your cloud storage."
    )

    save_col, restore_col = st.columns(2)

    with save_col:
        st.markdown("#### Save a copy")
        st.caption("Downloads one file with all your transactions, accounts and settings.")
        if os.path.exists(db.DB_PATH):
            st.download_button("⬇️ Download my data", data=db.export_database(),
                               file_name="finance_backup.db", mime="application/octet-stream",
                               use_container_width=True)
        else:
            st.info("There's nothing to save yet.")

    with restore_col:
        st.markdown("#### Bring back a saved copy")
        st.caption("Replaces what's in the app now with a copy you saved before. "
                   "Your current data is kept as finance.db.bak, just in case.")
        uploaded_db = st.file_uploader("Choose your saved file (ends in .db)", type=["db"])
        if uploaded_db is not None and st.button("🔄 Bring back this copy", type="primary",
                                                 use_container_width=True):
            success, message = db.import_database(uploaded_db.getvalue())
            if success:
                st.toast(message, icon="✅")
                st.rerun()
            else:
                st.error(message)
