"""
transactions.py — Log and manage your income and expenses.

Add entries manually, import from CSV, export as backup,
and browse/filter/edit/delete your full transaction history.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import database as db
from database import INCOME_CATEGORIES, EXPENSE_CATEGORIES


@st.dialog("Delete Transaction?")
def delete_transaction_dialog(tid, t_date, t_category, t_amount, t_type):
    """Confirmation dialog before permanently deleting a transaction."""
    st.warning(
        f"Delete this **{t_type.lower()}** of **${t_amount:,.2f}** "
        f"({t_category}) on **{t_date}**?"
    )
    st.caption("This cannot be undone.")
    c1, c2 = st.columns(2)
    if c1.button("Cancel", use_container_width=True, key=f"cancel_del_{tid}"):
        st.rerun()
    if c2.button("Delete", type="primary", use_container_width=True, key=f"confirm_del_{tid}"):
        db.delete_transaction(tid)
        st.toast("Transaction deleted.", icon="🗑️")
        st.rerun()


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


def _render_add_form() -> None:
    """Add-new-transaction form. Type sits outside so changing it re-filters Category live."""
    with st.expander("➕ Add New Transaction", expanded=False):
        t_type = st.radio("Type", ["Income", "Expense"], horizontal=True, key="add_type")
        cats = INCOME_CATEGORIES if t_type == "Income" else EXPENSE_CATEGORIES

        with st.form("add_transaction_form"):
            col1, col2 = st.columns(2)
            with col1:
                t_date = st.date_input("Date", datetime.today())
                t_amount = st.number_input("Amount ($)", min_value=0.01, format="%.2f")
            with col2:
                t_category = st.selectbox("Category", cats)
                t_desc = st.text_input("Description (Optional)")

            if st.form_submit_button("Save Transaction", use_container_width=True):
                db.add_transaction(t_date.strftime("%Y-%m-%d"), t_amount, t_category, t_type, t_desc)
                st.toast("Successfully added transaction!", icon="✅")
                st.rerun()


def _render_csv_section() -> None:
    """Import / export controls."""
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
            uploaded = st.file_uploader(
                "Upload a CSV file", type=["csv"],
                help="Upload your bank's CSV export. Most formats (Chase, Monzo, NatWest, DCU, etc.) are automatically supported!"
            )
            if uploaded is not None and st.button("📥 Import", use_container_width=True):
                content = uploaded.getvalue().decode("utf-8")
                imported, errors = db.import_transactions_csv(content)

                if imported > 0:
                    st.toast(f"Successfully imported {imported} transactions!", icon="✅")

                if errors:
                    error_lines = [e.strip() for e in errors.split(";") if e.strip()]
                    st.warning(f"⚠️ {len(error_lines)} row(s) couldn't be imported.")
                    with st.expander("Show details"):
                        for line in error_lines:
                            st.markdown(f"- {line}")

                if imported > 0:
                    st.rerun()


def _render_history(df: pd.DataFrame) -> None:
    """Filterable, searchable, selectable transaction history."""
    st.subheader("Transaction History")

    f1, f2, f3 = st.columns([1, 1, 2])
    with f1:
        type_filter = st.selectbox("Type", ["All", "Income", "Expense"], key="trans_type_filter")
    with f2:
        category_filter = st.selectbox(
            "Category", ["All"] + sorted(df["category"].unique().tolist()), key="trans_cat_filter"
        )
    with f3:
        search = st.text_input("Search description", placeholder="e.g. dentist, amazon, uber", key="trans_search")

    filtered = df.copy()
    if type_filter != "All":
        filtered = filtered[filtered["type"] == type_filter]
    if category_filter != "All":
        filtered = filtered[filtered["category"] == category_filter]
    if search:
        mask = filtered["description"].fillna("").str.contains(search, case=False, na=False)
        filtered = filtered[mask]

    if filtered.empty:
        st.info("No transactions match your filters.")
        return

    st.caption(f"Showing **{len(filtered)}** transaction(s). Click a row to enable Edit / Delete.")

    display = filtered[["id", "date", "type", "category", "amount", "description"]].copy()
    display["amount"] = display["amount"].map(lambda v: f"${v:,.2f}")

    selection = st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={"id": st.column_config.NumberColumn("ID", width="small")},
        key="trans_table",
    )

    selected_rows = selection.selection.rows if selection and selection.selection else []
    if not selected_rows:
        return

    selected_idx = selected_rows[0]
    row = filtered.iloc[selected_idx]
    a1, a2, _ = st.columns([1, 1, 4])
    if a1.button("✏️ Edit selected", use_container_width=True):
        edit_transaction_dialog(row["id"], row["date"], row["amount"],
                                row["category"], row["type"], row["description"])
    if a2.button("🗑️ Delete selected", use_container_width=True):
        delete_transaction_dialog(row["id"], row["date"], row["category"], row["amount"], row["type"])


def render_transactions():
    """Render the full Transactions page."""
    st.header("💸 Transactions")

    _render_add_form()
    _render_csv_section()

    st.markdown("---")

    df = db.get_all_transactions()
    if df.empty:
        st.info("No transactions logged yet. Add your first one above!")
        return

    _render_history(df)
