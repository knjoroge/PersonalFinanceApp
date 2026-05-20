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
from views._shared import confirm_delete_dialog


def _open_delete_transaction_dialog(tid, t_date, t_category, t_amount, t_type):
    """Open the "are you sure?" pop-up before permanently deleting a transaction."""
    body = (f"Delete this **{t_type.lower()}** of **{db.format_money(t_amount)}** "
            f"({t_category}) on **{t_date}**?")
    confirm_delete_dialog(
        title="Delete Transaction?",
        body=body,
        on_confirm=lambda: (db.delete_transaction(tid), st.toast("Transaction deleted.", icon="🗑️")),
        key_suffix=f"trans_{tid}",
    )


@st.dialog("Edit Transaction")
def edit_transaction_dialog(tid, cur_date, cur_amount, cur_category, cur_type, cur_desc):
    """Pop-up form for editing an existing transaction.

    The Type selector sits outside the form so changing it instantly
    refreshes the matching Category list (Income vs Expense categories).
    """
    st.write(f"Editing Transaction #{tid}")

    # Type lives outside the form so the category list reacts to it live.
    new_type = st.radio(
        "Type", ["Income", "Expense"],
        horizontal=True,
        index=0 if cur_type == "Income" else 1,
        key=f"edit_type_{tid}",
    )
    cats = INCOME_CATEGORIES if new_type == "Income" else EXPENSE_CATEGORIES
    cat_idx = cats.index(cur_category) if cur_category in cats else 0

    with st.form(f"edit_form_{tid}"):
        col1, col2 = st.columns(2)
        with col1:
            new_date = st.date_input("Date", datetime.strptime(cur_date, "%Y-%m-%d"), key=f"edit_date_{tid}")
            new_amount = st.number_input(
                f"Amount ({db.get_currency()})",
                min_value=0.01, value=float(cur_amount),
                format="%.2f", key=f"edit_amt_{tid}",
            )
        with col2:
            new_category = st.selectbox("Category", cats, index=cat_idx, key=f"edit_cat_{tid}")
            new_desc = st.text_input("Description (Optional)", value=cur_desc or "", key=f"edit_desc_{tid}")

        if st.form_submit_button("Save Changes"):
            db.update_transaction(tid, new_date.strftime("%Y-%m-%d"), new_amount,
                                  new_category, new_type, new_desc)
            st.toast("Transaction updated!", icon="✏️")
            st.rerun()


# Quick-add presets — one-click prefills for transactions the user enters often.
# Each tuple is (label, type, category, amount, default description).
_QUICK_ADD_PRESETS = [
    ("💰 Salary",       "Income",  "Salary",         3000.00, "Monthly salary"),
    ("🏠 Rent",         "Expense", "Housing",        1200.00, "Rent payment"),
    ("☕ Coffee",       "Expense", "Food",              5.00, "Coffee"),
    ("🛒 Groceries",    "Expense", "Food",             75.00, "Groceries"),
    ("⛽ Fuel",         "Expense", "Transportation",   45.00, "Gas / fuel"),
]


def _render_add_form() -> None:
    """Render the "Add New Transaction" form.

    Includes a row of one-click "quick-add" buttons that pre-fill the form
    with common transactions (rent, salary, coffee, etc.) so the user can
    just click and tweak instead of typing every field.

    The Type radio is outside the form so the Category list re-filters live
    when the user flips between Income and Expense.
    """
    with st.expander("➕ Add New Transaction", expanded=False):
        # --- One-click prefill buttons ---
        st.caption("Quick-add common transactions:")
        cols = st.columns(len(_QUICK_ADD_PRESETS))
        for col, (label, p_type, p_cat, p_amt, p_desc) in zip(cols, _QUICK_ADD_PRESETS):
            if col.button(label, use_container_width=True, key=f"quick_{label}"):
                # Stash the preset in session state; the form below reads it on next rerun.
                st.session_state["_prefill"] = {
                    "type": p_type, "category": p_cat, "amount": p_amt, "desc": p_desc,
                }
                st.rerun()

        prefill = st.session_state.get("_prefill", {})
        default_type = prefill.get("type", "Income")
        t_type = st.radio(
            "Type", ["Income", "Expense"],
            horizontal=True, key="add_type",
            index=0 if default_type == "Income" else 1,
        )
        cats = INCOME_CATEGORIES if t_type == "Income" else EXPENSE_CATEGORIES
        cat_idx = cats.index(prefill["category"]) if prefill.get("category") in cats else 0

        with st.form("add_transaction_form"):
            col1, col2 = st.columns(2)
            with col1:
                t_date = st.date_input("Date", datetime.today())
                t_amount = st.number_input(
                    f"Amount ({db.get_currency()})",
                    min_value=0.01, format="%.2f",
                    value=float(prefill.get("amount", 0.01)),
                )
            with col2:
                t_category = st.selectbox("Category", cats, index=cat_idx)
                t_desc = st.text_input("Description (Optional)", value=prefill.get("desc", ""))

            if st.form_submit_button("Save Transaction", use_container_width=True):
                db.add_transaction(t_date.strftime("%Y-%m-%d"), t_amount, t_category, t_type, t_desc)
                st.toast("Successfully added transaction!", icon="✅")
                st.session_state.pop("_prefill", None)  # clear so it doesn't stick
                st.rerun()


def _show_import_result(imported: int, skipped: int, errors) -> None:
    """Render the "X imported, Y skipped, Z errors" feedback after an import.

    Pulled out so both the one-click path and the manual-mapping path can
    share the same toast/info/warning behaviour.
    """
    if imported > 0:
        st.toast(f"Successfully imported {imported} transactions!", icon="✅")
    if skipped > 0:
        st.info(f"Skipped {skipped} duplicate row(s) that already exist in your data.")

    if errors:
        error_lines = [e.strip() for e in errors.split(";") if e.strip()]
        st.warning(f"⚠️ {len(error_lines)} row(s) couldn't be imported.")
        with st.expander("Show details"):
            for line in error_lines:
                st.markdown(f"- {line}")

    if imported == 0 and skipped == 0 and not errors:
        st.info("No new transactions were found in this file.")

    if imported > 0:
        st.rerun()


def _render_mapping_ui(content: str, analysis: dict) -> None:
    """Show the manual column-mapping form for CSVs whose layout we couldn't auto-detect.

    Lets the user:
      * preview the first 5 rows of their file,
      * pick a saved preset (or reapply one),
      * pick which column means "Date", "Amount", "Description", etc.,
      * pick the date format (DD-first / MM-first),
      * save the mapping under a name for one-click re-use next month,
    then commit the import with the chosen mapping.
    """
    st.warning(
        "We couldn't automatically figure out this file's layout. "
        "Tell us which columns mean what, then click **Confirm Import**."
    )

    # --- Saved presets (recall a previously-named mapping) ---
    presets = db.list_csv_mapping_presets()
    preset_choice = "(start fresh)"
    if presets:
        preset_choice = st.selectbox(
            "Saved mapping preset",
            ["(start fresh)"] + presets,
            help="Reapply a mapping you saved from a previous import.",
        )
    preset_data = db.get_csv_mapping_preset(preset_choice) if preset_choice != "(start fresh)" else None

    st.markdown("**Preview** (first 5 rows of your file)")
    st.dataframe(analysis['preview'], use_container_width=True, hide_index=True)

    available = ["(none)"] + analysis['columns']
    auto = analysis['autodetected']
    # If the user chose a preset, its mapping wins over auto-detect.
    starting = {**auto, **(preset_data["mapping"] if preset_data else {})}

    def _idx(col):
        # Pick the pre-selected option in the dropdown.
        return available.index(col) if col in available else 0

    st.markdown("**Map your columns**")
    m1, m2 = st.columns(2)
    with m1:
        map_date = st.selectbox("Date column", available, index=_idx(starting.get('date')))
        map_amount = st.selectbox(
            "Amount column (single column with +/- values)",
            available, index=_idx(starting.get('amount')),
        )
        map_debit = st.selectbox(
            "Debit / Money Out (optional — use only if no single Amount column)",
            available, index=_idx(starting.get('debit')),
        )
        map_credit = st.selectbox(
            "Credit / Money In (optional — use only if no single Amount column)",
            available, index=_idx(starting.get('credit')),
        )
    with m2:
        map_desc = st.selectbox("Description column (optional)", available, index=_idx(starting.get('desc')))
        map_cat = st.selectbox("Category column (optional)", available, index=_idx(starting.get('cat')))
        map_type = st.selectbox(
            "Type column (optional — \"Income\" / \"Expense\")",
            available, index=_idx(starting.get('type')),
        )

    default_dayfirst = preset_data["dayfirst"] if preset_data else True
    date_mode = st.radio(
        "Date format",
        ["DD-first (UK: 31/12/2026)", "MM-first (US: 12/31/2026)"],
        index=0 if default_dayfirst else 1,
        horizontal=True,
        help="If your dates look wrong after import (e.g. swapped day/month), switch this and re-import.",
    )
    dayfirst = date_mode.startswith("DD-first")

    # --- Save this mapping as a named preset for next time ---
    with st.expander("💾 Save this mapping for next time", expanded=False):
        preset_name = st.text_input(
            "Preset name (e.g. 'MyBank')",
            help="Saves under this name so you can pick it from the dropdown above when importing the next statement.",
        )

    c1, c2 = st.columns([3, 1])
    # Build the mapping dict from the dropdown choices.
    def _val(x):
        # Turn "(none)" back into a real None so the importer treats it as missing.
        return None if x == "(none)" else x
    mapping = {
        'date':   _val(map_date),
        'amount': _val(map_amount),
        'debit':  _val(map_debit),
        'credit': _val(map_credit),
        'desc':   _val(map_desc),
        'cat':    _val(map_cat),
        'type':   _val(map_type),
    }
    if c1.button("✅ Confirm Import", type="primary", use_container_width=True):
        if preset_name.strip():
            db.save_csv_mapping_preset(preset_name.strip(), mapping, dayfirst=dayfirst)
            st.toast(f"Saved preset '{preset_name.strip()}'.", icon="💾")
        imported, skipped, errors = db.import_transactions_csv(
            content, column_mapping=mapping, dayfirst=dayfirst,
        )
        _show_import_result(imported, skipped, errors)
    # Quick delete for unwanted presets.
    if preset_data and c2.button("🗑️ Delete preset", use_container_width=True):
        db.delete_csv_mapping_preset(preset_choice)
        st.toast(f"Removed preset '{preset_choice}'.", icon="🗑️")
        st.rerun()


def _render_csv_section() -> None:
    """Render the CSV Import / Export controls (side-by-side download and upload).

    Import flow:
      1. User picks a file.
      2. We call analyze_csv to see if auto-detect can recognise it.
      3. If yes → big "Import" button (one click — fast path for known banks).
      4. If no → render the column-mapping form so the user can guide us.
    """
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
                help="Upload your bank's CSV export. Common formats (Chase, Monzo, NatWest, DCU, etc.) "
                     "import in one click. Unknown formats will prompt for column mapping. "
                     "Duplicates are skipped automatically."
            )
            if uploaded is None:
                return

            content = uploaded.getvalue().decode("utf-8")
            analysis = db.analyze_csv(content)

            if analysis['error']:
                st.error(analysis['error'])
                return

            if not analysis['missing']:
                # All required fields recognised — show the simple one-click path.
                st.success("✅ Format recognised automatically.")
                with st.expander("Preview (first 5 rows)"):
                    st.dataframe(analysis['preview'], use_container_width=True, hide_index=True)
                if st.button("📥 Import", use_container_width=True):
                    imported, skipped, errors = db.import_transactions_csv(content)
                    _show_import_result(imported, skipped, errors)
            else:
                # Auto-detect couldn't find one or more required fields — fall back to manual map.
                _render_mapping_ui(content, analysis)


def _apply_filters(df: pd.DataFrame, type_filter: str, category_filter: str,
                   search: str) -> pd.DataFrame:
    """Apply the type / category / search filters to a transactions dataframe.

    Search is multi-field: it matches the description, category, type, AND
    amount (formatted as a string) so a query like "amazon" finds Amazon rows
    and "50" finds any $50 transaction.
    """
    filtered = df.copy()
    if type_filter != "All":
        filtered = filtered[filtered["type"] == type_filter]
    if category_filter != "All":
        filtered = filtered[filtered["category"] == category_filter]
    if search:
        q = search.strip().lower()
        haystack = (
            filtered["description"].fillna("").astype(str).str.lower() + " " +
            filtered["category"].fillna("").astype(str).str.lower() + " " +
            filtered["type"].fillna("").astype(str).str.lower() + " " +
            filtered["amount"].map(lambda v: f"{v:.2f}")
        )
        filtered = filtered[haystack.str.contains(q, na=False)]
    return filtered


def _open_bulk_delete_dialog(ids: list) -> None:
    """Open a confirm pop-up before permanently deleting many transactions at once."""
    body = f"Delete **{len(ids)} selected transaction(s)**?"

    def _do_delete():
        for tid in ids:
            db.delete_transaction(int(tid))
        st.toast(f"Deleted {len(ids)} transaction(s).", icon="🗑️")

    confirm_delete_dialog(
        title="Delete Selected Transactions?",
        body=body,
        on_confirm=_do_delete,
        key_suffix=f"bulk_{len(ids)}",
    )


def _render_history(df: pd.DataFrame) -> None:
    """Render the filterable, searchable, multi-selectable transaction history.

    Features:
      * Type + Category dropdowns and a single search box that matches across
        description, category, type, and amount.
      * Single-row selection enables Edit + Delete on that row.
      * Multi-row selection enables Bulk Delete and "Export filtered as CSV".
    """
    st.subheader("Transaction History")

    f1, f2, f3 = st.columns([1, 1, 2])
    with f1:
        type_filter = st.selectbox("Type", ["All", "Income", "Expense"], key="trans_type_filter")
    with f2:
        category_filter = st.selectbox(
            "Category", ["All"] + sorted(df["category"].unique().tolist()), key="trans_cat_filter"
        )
    with f3:
        search = st.text_input(
            "Search anything",
            placeholder="e.g. amazon, food, 50, expense",
            key="trans_search",
            help="Matches description, category, type, or amount.",
        )

    filtered = _apply_filters(df, type_filter, category_filter, search)

    # Export-filtered-view button sits above the table so users can grab a
    # subset (e.g. "all Amazon Expenses last month") in one click.
    if not filtered.empty:
        st.download_button(
            "⬇️ Export filtered view (CSV)",
            data=filtered.to_csv(index=False),
            file_name=f"transactions_filtered_{datetime.today().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

    if filtered.empty:
        st.info("No transactions match your filters.")
        return

    st.caption(
        f"Showing **{len(filtered)}** transaction(s). "
        "Click rows to select — hold ⌘/Ctrl or shift to pick multiple for bulk delete."
    )

    display = filtered[["id", "date", "type", "category", "amount", "description"]].copy()
    display["amount"] = display["amount"].map(lambda v: db.format_money(v))

    selection = st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row",
        column_config={"id": st.column_config.NumberColumn("ID", width="small")},
        key="trans_table",
    )

    selected_rows = selection.selection.rows if selection and selection.selection else []
    if not selected_rows:
        return

    selected_ids = [int(filtered.iloc[i]["id"]) for i in selected_rows]
    a1, a2, a3, _ = st.columns([1, 1, 1, 3])
    # Edit only makes sense for exactly one row.
    if len(selected_rows) == 1 and a1.button("✏️ Edit selected", use_container_width=True):
        row = filtered.iloc[selected_rows[0]]
        edit_transaction_dialog(row["id"], row["date"], row["amount"],
                                row["category"], row["type"], row["description"])
    if len(selected_rows) == 1 and a2.button("🗑️ Delete", use_container_width=True):
        row = filtered.iloc[selected_rows[0]]
        _open_delete_transaction_dialog(row["id"], row["date"], row["category"], row["amount"], row["type"])
    if len(selected_rows) > 1 and a3.button(f"🗑️ Delete {len(selected_rows)} rows", use_container_width=True):
        _open_bulk_delete_dialog(selected_ids)


def render_transactions():
    """Top-level entry point for the Transactions page."""
    st.header("💸 Transactions")

    _render_add_form()
    _render_csv_section()

    st.markdown("---")

    df = db.get_all_transactions()
    if df.empty:
        st.info("No transactions logged yet. Add your first one above!")
        return

    _render_history(df)
