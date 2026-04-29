"""
app.py — Main entry point for the Personal Finance Manager.

This is the file you run to start the app. It sets up the browser page,
creates the database if it doesn't exist yet, and builds the sidebar
navigation so you can switch between the different screens (Dashboard,
Transactions, Net Worth & Accounts, and AI Advisor).
"""

import streamlit as st
from database import init_db

# --- Page Setup ---
# This must be the very first Streamlit command in the script.
# It sets the browser tab title, icon, and layout options.
st.set_page_config(
    page_title="Personal Finance Manager",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Make sure the database tables exist before anything else runs.
# If the database file doesn't exist yet, this creates it automatically.
init_db()


def main():
    """
    Builds the sidebar menu and loads the selected page.

    The sidebar lets the user pick which view to see. Based on their
    selection, the matching view module is loaded and displayed.
    """

    # --- Sidebar ---
    st.sidebar.title("💰 Finance Manager")
    st.sidebar.markdown("---")

    # Let the user choose which page to view
    page = st.sidebar.radio(
        "Navigate",
        ["Dashboard", "Transactions", "Net Worth & Accounts", "AI Advisor"]
    )

    st.sidebar.markdown("---")
    st.sidebar.info(
        "Track your wealth, control your expenses, and get personalized advice."
    )

    # --- Load the Selected Page ---
    # Each page lives in its own file inside the "views" folder.
    # We import them here (instead of at the top) so we only load the
    # code for the page the user actually wants to see.
    if page == "Dashboard":
        from views.dashboard import render_dashboard
        render_dashboard()
    elif page == "Transactions":
        from views.transactions import render_transactions
        render_transactions()
    elif page == "Net Worth & Accounts":
        from views.accounts import render_accounts
        render_accounts()
    elif page == "AI Advisor":
        from views.advisor import render_advisor
        render_advisor()


if __name__ == "__main__":
    main()
