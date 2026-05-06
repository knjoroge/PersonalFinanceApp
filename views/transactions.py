"""
transactions.py — Log and manage your income and expenses.

Add entries manually, import from CSV, export as backup,
and browse/filter/edit/delete your full transaction history.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import database as db

INCOME_CATEGORIES = ["Salary", "Bonus", "Investment", "Side Hustle", "Other"]
EXPENSE_CATEGORIES = ["Housing", "Food", "Transportation", "Utilities", "Insurance",
                       "Healthcare", "Savings", "Debt", "Entertainment", "Other"]
ALL_CATEGORIES = EXPENSE_CATEGORIES + [c for c in INCOME_CATEGORIES if c not in EXPENSE_CATEGORIES]


@st.dialog("Edit Transaction")
def edit_transaction_dialog(tid, cur_date, cur_amount, cur_category, cur_type, cur_desc):
    """Pop-up form for editing an existing transaction."""
    st.write(f"Editing Transaction #{tid}")

    col1, col2 = st.columns(2)
    with col1:
        new_date = st.date_input("Date", datetime.strptime(cur_date, "%Y-%m-%d"), key=f"edit_date_{tid}")
        new_type = st.selectbox("Type", ["Income", "Expense"],
                                index=0 if cur_type == "Income" else 1, key=f"edit_type_{tid}")
        new_amount = st.number_input("Amount ($)", min_value=0.01, value=float(cur_amount),
                                     format="%.2f", key=f"edit_amt_{tid}")

    with col2:
        cats = INCOME_CATEGORIES if new_type == "Income" else EXPENSE_CATEGORIES
        cat_idx = cats.index(cur_category) if cur_category in cats else 0
        new_category = st.selectbox("Category", cats, index=cat_idx, key=f"edit_cat_{tid}")
        new_desc = st.text_input("Description (Optional)", value=cur_desc or "", key=f"edit_desc_{tid}")

    if st.button("Save Changes"):
        db.update_transaction(tid, new_date.strftime("%Y-%m-%d"), new_amount, new_category, new_type, new_desc)
        st.toast("Transaction updated!", icon="✏️")
        st.rerun()


def render_transactions():
    """Render the full Transactions page."""

    st.header("💸 Transactions")

    # --- Add new transaction ---
    with st.expander("➕ Add New Transaction", expanded=False):
        with st.form("add_transaction_form"):
            col1, col2 = st.columns(2)
            with col1:
                t_date = st.date_input("Date", datetime.today())
                t_type = st.selectbox("Type", ["Income", "Expense"])
                t_amount = st.number_input("Amount ($)", min_value=0.01, format="%.2f")
            with col2:
                t_category = st.selectbox("Category", ALL_CATEGORIES)
                t_desc = st.text_input("Description (Optional)")

            if st.form_submit_button("Save Transaction", use_container_width=True):
                db.add_transaction(t_date.strftime("%Y-%m-%d"), t_amount, t_category, t_type, t_desc)
                st.toast("Successfully added transaction!", icon="✅")
                st.rerun()

    # --- CSV import / export ---
    with st.expander("📁 Import / Export CSV", expanded=False):
        col_imp, col_exp = st.columns(2)

        with col_exp:
            st.markdown("#### Export Transactions")
            csv_data = db.export_transactions_csv()
            if csv_data:
                st.download_button("⬇️ Download CSV", data=csv_data,
                                   file_name=f"transactions_{datetime.today().strftime('%Y%m%d')}.csv",
                                   mime="text/csv", use_container_width=True)
            else:
                st.info("No transactions to export.")

        with col_imp:
            st.markdown("#### Import Transactions")
            uploaded = st.file_uploader("Upload a CSV file", type=["csv"],
                                        help="Upload your bank's CSV export. Most formats (Chase, Monzo, NatWest, DCU, etc.) are automatically supported!")
            if uploaded is not None and st.button("📥 Import", use_container_width=True):
                content = uploaded.getvalue().decode("utf-8")
                imported, errors = db.import_transactions_csv(content)
                if imported > 0:
                    st.toast(f"Successfully imported {imported} transactions!", icon="✅")
                if errors:
                    st.warning(f"Some rows had issues: {errors}")
                if imported > 0:
                    st.rerun()

    st.markdown("---")

    # --- Transaction history ---
    st.subheader("Recent Activity")
    df = db.get_all_transactions()

    if not df.empty:
        f1, f2 = st.columns(2)
        with f1:
            type_filter = st.selectbox("Filter by Type", ["All", "Income", "Expense"], key="trans_type_filter")
        with f2:
            category_filter = st.selectbox("Filter by Category",
                                           ["All"] + sorted(df["category"].unique().tolist()), key="trans_cat_filter")

        filtered = df.copy()
        if type_filter != "All":
            filtered = filtered[filtered["type"] == type_filter]
        if category_filter != "All":
            filtered = filtered[filtered["category"] == category_filter]

        # Pagination — 15 per page
        per_page = 15
        total = len(filtered)
        pages = max(1, (total + per_page - 1) // per_page)
        page = st.number_input(f"Page (1–{pages})", min_value=1, max_value=pages, value=1, key="trans_page")

        start = (page - 1) * per_page
        end = start + per_page
        st.caption(f"Showing {start + 1}–{min(end, total)} of {total} transactions")

        for _, row in filtered.iloc[start:end].iterrows():
            cols = st.columns([1.5, 1, 1.5, 1, 2, 0.5, 0.5])
            cols[0].write(row['date'])
            cols[1].markdown(f"**{'🟢' if row['type'] == 'Income' else '🔴'}**")
            cols[2].write(row['category'])
            cols[3].write(f"${row['amount']:,.2f}")
            cols[4].caption(row['description'] if pd.notnull(row['description']) else "")
            if cols[5].button("✏️", key=f"edit_{row['id']}", help="Edit"):
                edit_transaction_dialog(row['id'], row['date'], row['amount'],
                                        row['category'], row['type'], row['description'])
            if cols[6].button("🗑️", key=f"del_{row['id']}", help="Delete"):
                db.delete_transaction(row['id'])
                st.toast("Transaction deleted.", icon="🗑️")
                st.rerun()
            st.divider()
    else:
        st.info("No transactions logged yet. Add your first one above!")
