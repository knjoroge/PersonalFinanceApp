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
from views._shared import confirm_delete_dialog, signed_money, sample_data_button


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


@st.dialog("Change transaction")
def edit_transaction_dialog(tid, cur_date, cur_amount, cur_category, cur_type, cur_desc):
    """Pop-up form for editing an existing transaction.

    The Type selector sits outside the form so changing it instantly
    refreshes the matching Category list (Income vs Expense categories).
    """
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

        if st.form_submit_button("Save changes"):
            db.update_transaction(tid, new_date.strftime("%Y-%m-%d"), new_amount,
                                  new_category, new_type, new_desc)
            st.toast("Changes saved!", icon="✏️")
            st.rerun()


# Shown in the column dropdowns when the file doesn't have that kind of column.
_NOT_IN_FILE = "(not in my file)"

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
    # Open by default: adding a transaction is the main thing people do here.
    with st.expander("➕ Add a transaction",
                     expanded=st.session_state.get("add_form_open", True)):
        # --- One-click prefill buttons ---
        st.caption("Shortcuts: click one to fill in the form, then change anything before saving.")
        cols = st.columns(len(_QUICK_ADD_PRESETS))
        for col, (label, p_type, p_cat, p_amt, p_desc) in zip(cols, _QUICK_ADD_PRESETS):
            if col.button(label, use_container_width=True, key=f"quick_{label}"):
                # Stash the preset in session state; the form below reads it on next rerun.
                st.session_state["_prefill"] = {
                    "type": p_type, "category": p_cat, "amount": p_amt, "desc": p_desc,
                }
                st.session_state["add_form_open"] = True
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
                    value=float(prefill["amount"]) if prefill.get("amount") else None,
                    placeholder="0.00",
                )
            with col2:
                t_category = st.selectbox("Category", cats, index=cat_idx)
                t_desc = st.text_input("Description (Optional)", value=prefill.get("desc", ""))

            if st.form_submit_button("Save", use_container_width=True):
                if not t_amount:
                    st.error("Please enter an amount.")
                else:
                    db.add_transaction(t_date.strftime("%Y-%m-%d"), t_amount, t_category, t_type, t_desc)
                    st.toast("Saved!", icon="✅")
                    st.session_state.pop("_prefill", None)  # clear so it doesn't stick
                    st.session_state["add_form_open"] = True  # keep open to add the next one
                    st.rerun()


def _show_import_result(imported: int, skipped: int, errors) -> None:
    """Render the "X imported, Y skipped, Z errors" feedback after an import.

    Pulled out so both the one-click path and the manual-mapping path can
    share the same toast/info/warning behaviour.
    """
    if imported > 0:
        st.toast(f"Imported {imported} transactions!", icon="✅")
    if skipped > 0:
        st.info(f"Skipped {skipped} transaction(s) you'd already imported before.")

    if errors:
        error_lines = [e.strip() for e in errors.split(";") if e.strip()]
        st.warning(f"⚠️ {len(error_lines)} line(s) in the file couldn't be read, so they were left out.")
        with st.expander("Show which ones"):
            for line in error_lines:
                st.markdown(f"- {line}")

    if imported == 0 and skipped == 0 and not errors:
        st.info("Nothing new in this file. Everything in it is already in the app.")

    if imported > 0:
        st.rerun()


def _ask_date_order(content, date_column, key: str) -> bool:
    """Return True if the file's dates are day-first (31/12), False if month-first (12/31).

    Usually the file itself settles it (a date like 31/12 can only be day-first),
    so nothing is shown. Only if every date could be read either way do we ask,
    using a real date from the user's file as the example.
    """
    dayfirst, example = db.guess_date_order_for_column(content, date_column)
    if dayfirst is not None:
        return dayfirst

    options = ["Day first, like 31/12/2026 (UK and most countries)",
               "Month first, like 12/31/2026 (US)"]
    question = "How are the dates written in your file?"
    if example:
        try:
            d1 = pd.to_datetime(example, dayfirst=True)
            d2 = pd.to_datetime(example, dayfirst=False)
            options = [f"{d1.day} {d1:%B %Y} (day first, UK style)",
                       f"{d2:%B} {d2.day}, {d2.year} (month first, US style)"]
            question = f"Your file has dates like **{example}**. Which date is that?"
        except (ValueError, TypeError):
            pass
    # Best first guess: US users usually pick "$".
    default = 1 if db.get_currency() == "$" else 0
    choice = st.radio(question, options, index=default, key=key)
    return choice == options[0]


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
        "We don't recognise this bank's file yet. "
        "Tell us which column is which below, then click **Import**."
    )

    # --- Saved presets (recall a previously-named mapping) ---
    presets = db.list_csv_mapping_presets()
    preset_choice = "(none)"
    if presets:
        preset_choice = st.selectbox(
            "Use a bank layout you saved before?",
            ["(none)"] + presets,
        )
    preset_data = db.get_csv_mapping_preset(preset_choice) if preset_choice != "(none)" else None

    st.markdown("**Here are the first 5 lines of your file:**")
    st.dataframe(analysis['preview'], use_container_width=True, hide_index=True)

    available = [_NOT_IN_FILE] + analysis['columns']
    auto = analysis['autodetected']
    # If the user chose a preset, its mapping wins over auto-detect.
    starting = {**auto, **(preset_data["mapping"] if preset_data else {})}

    def _idx(col):
        # Pick the pre-selected option in the dropdown.
        return available.index(col) if col in available else 0

    st.markdown("**Which column is which?**")
    m1, m2 = st.columns(2)
    with m1:
        map_date = st.selectbox("Date", available, index=_idx(starting.get('date')))
        map_amount = st.selectbox(
            "Amount", available, index=_idx(starting.get('amount')),
            help="Pick this if your bank puts money in and money out in one column, "
                 "with a minus sign for spending.",
        )
        map_debit = st.selectbox(
            "Money out (only if your bank uses two separate columns)",
            available, index=_idx(starting.get('debit')),
        )
        map_credit = st.selectbox(
            "Money in (only if your bank uses two separate columns)",
            available, index=_idx(starting.get('credit')),
        )
    with m2:
        map_desc = st.selectbox("Description (optional)", available, index=_idx(starting.get('desc')))
        map_cat = st.selectbox("Category (optional)", available, index=_idx(starting.get('cat')))
        map_type = st.selectbox(
            "Says \"Income\" or \"Expense\" (optional)",
            available, index=_idx(starting.get('type')),
        )

    if preset_data:
        dayfirst = preset_data["dayfirst"]
    else:
        dayfirst = _ask_date_order(content, None if map_date == _NOT_IN_FILE else map_date, key="map_dayfirst")

    # --- Remember this layout for next time ---
    with st.expander("💾 Remember this layout for next month", expanded=False):
        preset_name = st.text_input(
            "Give it a name, for example your bank's name",
            help="Next time you import from this bank, pick this name at the top and everything fills in.",
        )

    c1, c2 = st.columns([3, 1])

    # Build the mapping dict from the dropdown choices.
    def _val(x):
        # Turn "(not in my file)" back into a real None so the importer treats it as missing.
        return None if x == _NOT_IN_FILE else x
    mapping = {
        'date':   _val(map_date),
        'amount': _val(map_amount),
        'debit':  _val(map_debit),
        'credit': _val(map_credit),
        'desc':   _val(map_desc),
        'cat':    _val(map_cat),
        'type':   _val(map_type),
    }
    if c1.button("✅ Import", type="primary", use_container_width=True):
        if preset_name.strip():
            db.save_csv_mapping_preset(preset_name.strip(), mapping, dayfirst=dayfirst)
            st.toast(f"Saved the '{preset_name.strip()}' layout.", icon="💾")
        imported, skipped, errors = db.import_transactions_csv(
            content, column_mapping=mapping, dayfirst=dayfirst,
        )
        _show_import_result(imported, skipped, errors)
    # Quick delete for unwanted presets.
    if preset_data and c2.button("🗑️ Forget this layout", use_container_width=True):
        db.delete_csv_mapping_preset(preset_choice)
        st.toast(f"Forgot the '{preset_choice}' layout.", icon="🗑️")
        st.rerun()


def _render_csv_section() -> None:
    """Render the CSV Import / Export controls (side-by-side download and upload).

    Import flow:
      1. User picks a file.
      2. We call analyze_csv to see if auto-detect can recognise it.
      3. If yes → big "Import" button (one click — fast path for known banks).
      4. If no → render the column-mapping form so the user can guide us.
    """
    with st.expander("📁 Import from your bank, or download your transactions", expanded=False):
        col_imp, col_exp = st.columns(2)

        with col_exp:
            st.markdown("#### Download your transactions")
            st.caption("Saves a spreadsheet file (CSV) you can open in Excel or Google Sheets.")
            csv_data = db.export_transactions_csv()
            if csv_data:
                st.download_button("⬇️ Download", data=csv_data,
                                   file_name=f"transactions_{datetime.today().strftime('%Y%m%d')}.csv",
                                   mime="text/csv", use_container_width=True)
            else:
                st.info("Nothing to download yet.")

        with col_imp:
            st.markdown("#### Import from your bank")
            st.caption("On your bank's website, download a statement as a **CSV** file, then choose it here. "
                       "Transactions you've already imported are skipped, so it's safe to import again.")
            uploaded = st.file_uploader("Choose your bank file", type=["csv"])
            if uploaded is None:
                return

            content = uploaded.getvalue()  # raw bytes; the database module handles encodings
            analysis = db.analyze_csv(content)

            if analysis['error']:
                st.error(analysis['error'])
                return

            if not analysis['missing']:
                # All required fields recognised — show the simple one-click path.
                st.success("✅ We recognise this file. It's ready to import.")
                with st.expander("Peek at the first 5 lines"):
                    st.dataframe(analysis['preview'], use_container_width=True, hide_index=True)
                dayfirst = _ask_date_order(content, analysis['autodetected'].get('date'), key="auto_dayfirst")
                if st.button("📥 Import", use_container_width=True):
                    imported, skipped, errors = db.import_transactions_csv(content, dayfirst=dayfirst)
                    _show_import_result(imported, skipped, errors)
            else:
                # Auto-detect couldn't find one or more required fields — fall back to manual map.
                _render_mapping_ui(content, analysis)


def _apply_filters(df: pd.DataFrame, type_filter: str, category_filter: str,
                   search: str, start_date=None, end_date=None) -> pd.DataFrame:
    """Apply the date / type / category / search filters to a transactions dataframe.

    Search is multi-field: it matches the description, category, type, AND
    amount (formatted as a string) so a query like "amazon" finds Amazon rows
    and "50" finds any $50 transaction.
    """
    filtered = df.copy()
    if start_date and end_date:
        dates = pd.to_datetime(filtered["date"]).dt.date
        filtered = filtered[(dates >= start_date) & (dates <= end_date)]
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
    st.subheader("Your transactions")

    # Default date range spans all transactions; users can narrow it.
    all_dates = pd.to_datetime(df["date"])
    min_date, max_date = all_dates.min().date(), all_dates.max().date()

    st.markdown("Find a transaction:")
    f1, f2, f3, f4 = st.columns([1, 1, 2, 2])
    with f1:
        type_filter = st.selectbox("Type", ["All", "Income", "Expense"], key="trans_type_filter")
    with f2:
        category_filter = st.selectbox(
            "Category", ["All"] + sorted(df["category"].unique().tolist()), key="trans_cat_filter"
        )
    with f3:
        date_range = st.date_input(
            "Date range",
            value=(min_date, max_date),
            min_value=min_date, max_value=max_date,
            key="trans_date_range",
        )
    with f4:
        search = st.text_input(
            "Search",
            placeholder="e.g. amazon, food, 50",
            key="trans_search",
            help="Matches description, category, type, or amount.",
        )

    # st.date_input returns a single date mid-edit; only filter once both ends are picked.
    start_date, end_date = (date_range if isinstance(date_range, (list, tuple))
                            and len(date_range) == 2 else (min_date, max_date))
    date_active = (start_date, end_date) != (min_date, max_date)

    # One-click reset for every filter. Only shown when a filter is active
    # so it doesn't clutter the default view.
    if type_filter != "All" or category_filter != "All" or search or date_active:
        if st.button("✖ Show everything again"):
            for k in ("trans_type_filter", "trans_cat_filter", "trans_search", "trans_date_range"):
                st.session_state.pop(k, None)
            st.rerun()

    filtered = _apply_filters(df, type_filter, category_filter, search, start_date, end_date)

    # Export-filtered-view button sits above the table so users can grab a
    # subset (e.g. "all Amazon Expenses last month") in one click.
    if not filtered.empty:
        st.download_button(
            "⬇️ Download the transactions shown",
            data=filtered.to_csv(index=False),
            file_name=f"transactions_filtered_{datetime.today().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

    if filtered.empty:
        st.info("No transactions match. Try a different search or date range.")
        return

    # Totals for the current filter so users don't have to add it up by hand.
    totals = db.summarize(filtered)
    st.caption(
        f"Showing **{len(filtered)}** transaction(s): "
        f"money in {db.format_money(totals['income'])}, "
        f"money out {db.format_money(totals['expense'])}, "
        f"left over {db.format_money(totals['net'])}."
    )
    st.caption("☑️ Tick the box at the start of a row to change or delete it. "
               "Tick several to delete them or change their category all at once.")

    display = filtered[["date", "type", "category", "amount", "description"]].copy()
    display["date"] = pd.to_datetime(display["date"]).dt.strftime("%d %b %Y")
    display["amount"] = display.apply(lambda r: signed_money(r["amount"], r["type"]), axis=1)
    display.columns = ["Date", "Type", "Category", "Amount", "Description"]

    selection = st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row",
        key="trans_table",
    )

    selected_rows = selection.selection.rows if selection and selection.selection else []
    if not selected_rows:
        return

    selected_ids = [int(filtered.iloc[i]["id"]) for i in selected_rows]
    a1, a2, a3, _ = st.columns([1, 1, 1, 3])
    # Edit only makes sense for exactly one row.
    if len(selected_rows) == 1 and a1.button("✏️ Change", use_container_width=True):
        row = filtered.iloc[selected_rows[0]]
        edit_transaction_dialog(row["id"], row["date"], row["amount"],
                                row["category"], row["type"], row["description"])
    if len(selected_rows) == 1 and a2.button("🗑️ Delete", use_container_width=True):
        row = filtered.iloc[selected_rows[0]]
        _open_delete_transaction_dialog(row["id"], row["date"], row["category"], row["amount"], row["type"])
    if len(selected_rows) > 1 and a3.button(f"🗑️ Delete {len(selected_rows)}", use_container_width=True):
        _open_bulk_delete_dialog(selected_ids)
    if len(selected_rows) > 1:
        _render_bulk_category(filtered.iloc[selected_rows], selected_ids)


def _render_bulk_category(selected: pd.DataFrame, selected_ids: list) -> None:
    """Change the category of several selected transactions in one go."""
    types = selected["type"].unique().tolist()
    if len(types) != 1:
        st.caption("To change the category of several transactions at once, "
                   "tick only money in (Income) or only money out (Expense), not both.")
        return
    cats = INCOME_CATEGORIES if types[0] == "Income" else EXPENSE_CATEGORIES
    c1, c2 = st.columns([2, 1])
    with c1:
        new_cat = st.selectbox(f"New category for the {len(selected_ids)} ticked transactions",
                               cats, key="bulk_category")
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Change category", use_container_width=True, key="bulk_category_btn"):
            db.set_category(selected_ids, new_cat)
            st.toast(f"Moved {len(selected_ids)} transactions to {new_cat}.", icon="🏷️")
            st.rerun()


def render_transactions():
    """Top-level entry point for the Transactions page."""
    st.header("💸 Transactions")

    _render_add_form()
    _render_csv_section()

    st.markdown("---")

    df = db.get_all_transactions()
    if df.empty:
        st.info("No transactions yet. Add your first one above, or import a file from your bank.")
        sample_data_button(key="sample_from_transactions")
        return

    _render_history(df)
