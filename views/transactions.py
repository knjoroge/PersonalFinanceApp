"""
transactions.py — The page for logging and managing income and expenses.

This view lets you:
  - Add new income or expense entries with a date, amount, category, and description
  - Import transactions in bulk from a CSV (spreadsheet) file
  - Export all your transactions as a downloadable CSV
  - Browse, filter, edit, and delete your transaction history
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import database as db

# Pre-defined category lists used in dropdown menus
INCOME_CATEGORIES = ["Salary", "Bonus", "Investment", "Side Hustle", "Other"]
EXPENSE_CATEGORIES = ["Housing", "Food", "Transportation", "Utilities", "Insurance",
                       "Healthcare", "Savings", "Debt", "Entertainment", "Other"]


@st.dialog("Edit Transaction")
def edit_transaction_dialog(transaction_id, current_date, current_amount,
                            current_category, current_type, current_desc):
    """
    Opens a pop-up dialog for editing an existing transaction.

    The user sees the current values pre-filled and can change any of them.
    Clicking "Save Changes" updates the transaction in the database.
    """
    st.write(f"Editing Transaction #{transaction_id}")

    col1, col2 = st.columns(2)
    with col1:
        new_date = st.date_input("Date", datetime.strptime(current_date, "%Y-%m-%d"),
                                 key=f"edit_date_{transaction_id}")
        new_type = st.selectbox("Type", ["Income", "Expense"],
                                index=0 if current_type == "Income" else 1,
                                key=f"edit_type_{transaction_id}")
        new_amount = st.number_input("Amount ($)", min_value=0.01,
                                     value=float(current_amount), format="%.2f",
                                     key=f"edit_amt_{transaction_id}")

    with col2:
        # Show the right category list based on Income vs Expense
        categories = INCOME_CATEGORIES if new_type == "Income" else EXPENSE_CATEGORIES
        cat_index = categories.index(current_category) if current_category in categories else 0
        new_category = st.selectbox("Category", categories, index=cat_index,
                                    key=f"edit_cat_{transaction_id}")
        new_desc = st.text_input("Description (Optional)",
                                 value=current_desc if current_desc else "",
                                 key=f"edit_desc_{transaction_id}")

    if st.button("Save Changes"):
        db.update_transaction(transaction_id, new_date.strftime("%Y-%m-%d"),
                              new_amount, new_category, new_type, new_desc)
        st.toast("Transaction updated!", icon="✏️")
        st.rerun()


def render_transactions():
    """Renders the full Transactions page: add form, CSV tools, and history list."""

    st.header("💸 Transactions")

    # --- Add New Transaction ---
    with st.expander("➕ Add New Transaction", expanded=False):
        with st.form("add_transaction_form"):
            col1, col2 = st.columns(2)

            with col1:
                t_date = st.date_input("Date", datetime.today())
                t_type = st.selectbox("Type", ["Income", "Expense"])
                t_amount = st.number_input("Amount ($)", min_value=0.01, format="%.2f")

            with col2:
                # Show all categories since the form can't dynamically update
                all_categories = EXPENSE_CATEGORIES + [c for c in INCOME_CATEGORIES
                                                       if c not in EXPENSE_CATEGORIES]
                t_category = st.selectbox("Category", all_categories)
                t_desc = st.text_input("Description (Optional)")

            submitted = st.form_submit_button("Save Transaction", use_container_width=True)

            if submitted:
                db.add_transaction(t_date.strftime("%Y-%m-%d"), t_amount,
                                   t_category, t_type, t_desc)
                st.toast("Successfully added transaction!", icon="✅")
                st.rerun()

    # --- CSV Import / Export ---
    with st.expander("📁 Import / Export CSV", expanded=False):
        col_imp, col_exp = st.columns(2)

        # Export: download your transactions as a spreadsheet
        with col_exp:
            st.markdown("#### Export Transactions")
            csv_data = db.export_transactions_csv()
            if csv_data:
                st.download_button(
                    label="⬇️ Download CSV",
                    data=csv_data,
                    file_name=f"transactions_{datetime.today().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.info("No transactions to export.")

        # Import: upload a CSV from your bank or another source
        with col_imp:
            st.markdown("#### Import Transactions")
            uploaded_file = st.file_uploader(
                "Upload a CSV file",
                type=["csv"],
                help="CSV must have columns: date, amount, category, type. Optional: description"
            )
            if uploaded_file is not None:
                if st.button("📥 Import", use_container_width=True):
                    content = uploaded_file.getvalue().decode("utf-8")
                    imported, errors = db.import_transactions_csv(content)
                    if imported > 0:
                        st.toast(f"Successfully imported {imported} transactions!", icon="✅")
                    if errors:
                        st.warning(f"Some rows had issues: {errors}")
                    if imported > 0:
                        st.rerun()

    st.markdown("---")

    # --- Transaction History with Filtering and Pagination ---
    st.subheader("Recent Activity")
    df = db.get_all_transactions()

    if not df.empty:
        # Filter controls: narrow down by type and/or category
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            type_filter = st.selectbox("Filter by Type", ["All", "Income", "Expense"],
                                       key="trans_type_filter")
        with filter_col2:
            category_filter = st.selectbox(
                "Filter by Category",
                ["All"] + sorted(df["category"].unique().tolist()),
                key="trans_cat_filter"
            )

        filtered_df = df.copy()
        if type_filter != "All":
            filtered_df = filtered_df[filtered_df["type"] == type_filter]
        if category_filter != "All":
            filtered_df = filtered_df[filtered_df["category"] == category_filter]

        # Pagination: show 15 transactions per page
        ITEMS_PER_PAGE = 15
        total_items = len(filtered_df)
        total_pages = max(1, (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

        page_num = st.number_input(
            f"Page (1–{total_pages})",
            min_value=1, max_value=total_pages, value=1,
            key="trans_page"
        )

        start_idx = (page_num - 1) * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        page_df = filtered_df.iloc[start_idx:end_idx]

        st.caption(f"Showing {start_idx + 1}–{min(end_idx, total_items)} of {total_items} transactions")

        # Display each transaction as a row with edit and delete buttons
        for _, row in page_df.iterrows():
            with st.container():
                cols = st.columns([1.5, 1, 1.5, 1, 2, 0.5, 0.5])

                with cols[0]: st.write(row['date'])
                with cols[1]: st.markdown(f"**{'🟢' if row['type'] == 'Income' else '🔴'}**")
                with cols[2]: st.write(row['category'])
                with cols[3]: st.write(f"${row['amount']:,.2f}")
                with cols[4]: st.caption(row['description'] if pd.notnull(row['description']) else "")
                with cols[5]:
                    if st.button("✏️", key=f"edit_{row['id']}", help="Edit"):
                        edit_transaction_dialog(row['id'], row['date'], row['amount'],
                                                row['category'], row['type'], row['description'])
                with cols[6]:
                    if st.button("🗑️", key=f"del_{row['id']}", help="Delete"):
                        db.delete_transaction(row['id'])
                        st.toast("Transaction deleted.", icon="🗑️")
                        st.rerun()
                st.divider()
    else:
        st.info("No transactions logged yet. Add your first one above!")
