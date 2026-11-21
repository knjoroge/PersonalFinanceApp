"""
dashboard.py — The main financial overview page.

Shows key totals, spending limits, charts, and recent transactions.
Everything can be filtered by time period using the sidebar.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import database as db
from datetime import datetime, timedelta

from database import EXPENSE_CATEGORIES
from views._shared import confirm_delete_dialog, signed_money, sample_data_button

MONTHLY_GOAL_KEY = "monthly_expense_goal"


def _current_month_rows(df_trans: pd.DataFrame) -> pd.DataFrame:
    """Return only the transactions dated within the current calendar month.

    Used by the spending limits, which are always
    scoped to "this month" regardless of the dashboard's selected time filter.
    Expects df_trans['date'] to already be datetime.
    """
    today = pd.Timestamp.today()
    return df_trans[df_trans['date'].dt.to_period('M') == today.to_period('M')]


def _open_delete_budget_dialog(budget_id, category, monthly_limit):
    """Open the "are you sure?" pop-up before removing a category budget."""
    body = f"Remove the spending limit for **{category}** ({db.format_money(monthly_limit, 0)} a month)?"
    caption = "Only the limit is removed. Your transactions in this category stay."
    confirm_delete_dialog(
        title="Remove spending limit?",
        body=body,
        caption=caption,
        confirm_label="Remove",
        on_confirm=lambda: (db.delete_budget(budget_id), st.toast("Limit removed.", icon="🗑️")),
        key_suffix=f"bud_{budget_id}",
    )


def _render_filters(df_trans: pd.DataFrame) -> pd.DataFrame:
    """Render the sidebar time-period controls and return only the rows that match.

    Supports preset ranges (This Month, Last Month, Last 90 Days, All Time) and
    a custom date picker.
    """
    st.sidebar.markdown("### 📅 Show me")
    filter_option = st.sidebar.selectbox(
        "Time period",
        ("This Month", "Last Month", "Last 90 Days", "All Time", "Custom Range")
    )

    today = datetime.today()
    # Earliest date in the data, used as the default "All Time" start.
    earliest = df_trans['date'].min()
    start_date = earliest.date() if pd.notnull(earliest) else today.date()
    end_date = today.date()

    if filter_option == "This Month":
        start_date = today.replace(day=1).date()
    elif filter_option == "Last Month":
        first_of_month = today.replace(day=1)
        last_of_prev = first_of_month - timedelta(days=1)
        start_date = last_of_prev.replace(day=1).date()
        end_date = last_of_prev.date()
    elif filter_option == "Last 90 Days":
        start_date = (today - timedelta(days=90)).date()
    elif filter_option == "Custom Range":
        date_range = st.sidebar.date_input("Select Date Range", [start_date, end_date])
        if len(date_range) == 2:
            start_date, end_date = date_range
            if start_date > end_date:
                st.sidebar.warning("Start date is after end date — swapping them.")
                start_date, end_date = end_date, start_date
        else:
            st.sidebar.warning("Please select both a start and end date.")

    mask = (df_trans['date'].dt.date >= start_date) & (df_trans['date'].dt.date <= end_date)
    return df_trans.loc[mask], filter_option


def _last_month_rows(df_trans: pd.DataFrame) -> pd.DataFrame:
    """Return only the transactions from last calendar month."""
    last_month = (pd.Timestamp.today().to_period('M') - 1)
    return df_trans[df_trans['date'].dt.to_period('M') == last_month]


def _mom_deltas(df_trans: pd.DataFrame) -> dict:
    """Build "vs last month" change strings for the headline numbers.

    Returns formatted strings like "+$120.00" (and "+3.2 pts" for savings rate).
    """
    this_s = db.summarize(_current_month_rows(df_trans))
    last_s = db.summarize(_last_month_rows(df_trans))

    def money_delta(key):
        diff = this_s[key] - last_s[key]
        return f"{'+' if diff >= 0 else '-'}{db.format_money(abs(diff))}"

    sr_diff = this_s['savings_rate'] - last_s['savings_rate']
    return {
        'income': money_delta('income'),
        'expense': money_delta('expense'),
        'net': money_delta('net'),
        'savings_rate': f"{sr_diff:+.1f}%",
    }


def _render_metrics(filtered_df: pd.DataFrame, net_worth: float, deltas: dict = None) -> None:
    """Render the row of five headline numbers (income, expenses, net, savings, net worth).

    Safe to call with an empty dataframe — numbers fall back to zero.
    When `deltas` is given, each metric shows a "vs last month" change
    (expenses use inverse colour because spending more is bad).
    """
    s = db.summarize(filtered_df)
    total_income = s['income']
    total_expense = s['expense']
    net_balance = s['net']
    savings_rate = s['savings_rate']
    d = deltas or {}

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Money in", db.format_money(total_income), delta=d.get('income'),
              help="Everything you earned in this period.")
    m2.metric("Money out", db.format_money(total_expense),
              delta=d.get('expense'), delta_color="inverse",
              help="Everything you spent in this period.")
    m3.metric("Left over", db.format_money(net_balance), delta=d.get('net'),
              help="Money in minus money out.")
    m4.metric("Saved", f"{savings_rate:.1f}%", delta=d.get('savings_rate'),
              help="How much of the money that came in you kept.")
    m5.metric("Net worth", db.format_money(net_worth),
              help="What you own minus what you owe, from the Net Worth & Accounts page.")

    if deltas:
        st.caption("The small numbers show the change compared with last month.")

    st.markdown("<br>", unsafe_allow_html=True)


def _limit_bar(label: str, spent: float, limit: float) -> None:
    """One green/yellow/red progress bar: how much of a monthly limit is used."""
    progress = min(spent / limit, 1.0) if limit > 0 else 0
    status = "🟢" if progress < 0.8 else "🟡" if progress < 1.0 else "🔴"
    st.markdown(f"**{status} {label}**")
    st.progress(progress)
    left = limit - spent
    note = f"{db.format_money(left, 0)} left" if left >= 0 else f"{db.format_money(-left, 0)} over"
    st.caption(f"Spent {db.format_money(spent, 0)} of {db.format_money(limit, 0)} · {note}")


def _render_spending_limits(df_trans: pd.DataFrame, budgets_df: pd.DataFrame) -> None:
    """Show and manage monthly spending limits, all in one place.

    Two kinds, both for the CURRENT calendar month (never the sidebar filter,
    or "All Time" would compare years of spending against a one-month limit):
      * one limit for all spending together (stored in preferences), and
      * optional limits for single categories, like Food (the budgets table).
    """
    this_month = _current_month_rows(df_trans) if not df_trans.empty else df_trans
    expenses = this_month[this_month['type'] == 'Expense'] if not this_month.empty else this_month
    spent_total = float(expenses['amount'].sum()) if not expenses.empty else 0.0
    spent_by_cat = expenses.groupby('category')['amount'].sum() if not expenses.empty else pd.Series(dtype=float)

    stored = db.get_preference(MONTHLY_GOAL_KEY)
    overall_limit = float(stored) if stored else None

    month_name = pd.Timestamp.today().strftime('%B')
    st.markdown(f"### 🎯 Spending limits for {month_name}")

    if overall_limit is None and budgets_df.empty:
        st.caption("Set a limit for how much you want to spend each month, and the app "
                   "will show how close you are. Open **Set spending limits** below to start.")
    else:
        over = [r['category'] for _, r in budgets_df.iterrows()
                if r['monthly_limit'] > 0 and spent_by_cat.get(r['category'], 0.0) > r['monthly_limit']]
        if overall_limit and spent_total > overall_limit:
            over.insert(0, "your overall limit")
        if over:
            st.error(f"🔴 You've gone over: **{', '.join(over)}**")

        bars = []
        if overall_limit:
            bars.append(("All spending", spent_total, overall_limit))
        bars += [(r['category'], spent_by_cat.get(r['category'], 0.0), r['monthly_limit'])
                 for _, r in budgets_df.iterrows()]
        cols = st.columns(min(len(bars), 4))
        for idx, (label, spent, limit) in enumerate(bars):
            with cols[idx % len(cols)]:
                _limit_bar(label, spent, limit)

    with st.expander("✏️ Set spending limits", expanded=False):
        st.markdown("**For all your spending**")
        o1, o2 = st.columns([3, 1])
        with o1:
            new_overall = st.number_input(
                f"Most I want to spend in a month, in total ({db.get_currency()})",
                min_value=0.0, value=overall_limit or 0.0, step=100.0,
                help="Leave at 0 if you don't want an overall limit.",
            )
        with o2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Save", key="save_overall_limit", use_container_width=True):
                if new_overall > 0:
                    db.set_preference(MONTHLY_GOAL_KEY, new_overall)
                    st.toast("Overall limit saved.", icon="✅")
                else:
                    db.delete_preference(MONTHLY_GOAL_KEY)
                    st.toast("Overall limit removed.", icon="🗑️")
                st.rerun()

        st.markdown("**For one category** (optional), for example, Food")
        with st.form("budget_form"):
            b_col1, b_col2 = st.columns(2)
            with b_col1:
                budget_cat = st.selectbox("Category", EXPENSE_CATEGORIES)
            with b_col2:
                budget_limit = st.number_input(
                    f"Most I want to spend on it in a month ({db.get_currency()})",
                    min_value=1.0, value=500.0, step=50.0,
                )
            if st.form_submit_button("Save category limit", use_container_width=True):
                db.set_budget(budget_cat, budget_limit)
                st.toast(f"Limit saved for {budget_cat}.", icon="✅")
                st.rerun()

        if not budgets_df.empty:
            budget_options = {
                f"{r['category']} ({db.format_money(r['monthly_limit'], 0)} a month)": r['id']
                for _, r in budgets_df.iterrows()
            }
            r1, r2 = st.columns([3, 1])
            with r1:
                del_budget = st.selectbox("Remove a category limit", list(budget_options.keys()))
            with r2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Remove", key="del_budget_btn", use_container_width=True):
                    sel_id = budget_options[del_budget]
                    sel = budgets_df[budgets_df['id'] == sel_id].iloc[0]
                    _open_delete_budget_dialog(int(sel_id), sel['category'], float(sel['monthly_limit']))


def _render_charts(filtered_df: pd.DataFrame) -> None:
    """Render the two side-by-side charts: expense pie + income-vs-expense over time.

    Both charts display amounts in the user's chosen currency on hover, and the
    legend sits at the top so it doesn't get cropped on narrow screens.
    """
    col1, col2 = st.columns(2)
    sym = db.get_currency()

    with col1:
        st.subheader("What you spent on")
        df_expenses = filtered_df[filtered_df['type'] == 'Expense']
        if not df_expenses.empty:
            grouped = df_expenses.groupby('category')['amount'].sum().reset_index()
            fig = px.pie(grouped, values='amount', names='category', hole=0.4,
                         color_discrete_sequence=px.colors.sequential.Plasma)
            fig.update_traces(
                hovertemplate=f"<b>%{{label}}</b><br>{sym}%{{value:,.2f}} (%{{percent}})<extra></extra>"
            )
            fig.update_layout(
                margin=dict(t=20, b=0, l=0, r=0),
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No spending in this period.")

    with col2:
        st.subheader("Money in vs money out")
        trend_df = filtered_df.groupby([filtered_df['date'].dt.normalize(), 'type'])['amount'].sum().reset_index()
        if not trend_df.empty:
            fig = px.bar(trend_df, x='date', y='amount', color='type', barmode='group',
                         color_discrete_map={"Income": "#10B981", "Expense": "#EF4444"})
            fig.update_traces(
                hovertemplate=f"<b>%{{x|%b %d, %Y}}</b><br>%{{fullData.name}}: {sym}%{{y:,.2f}}<extra></extra>"
            )
            fig.update_layout(
                margin=dict(t=20, b=0, l=0, r=0),
                yaxis_title=None, xaxis_title=None,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nothing to show for this period yet.")


def _render_top_merchants(filtered_df: pd.DataFrame) -> None:
    """Show the user's top 5 spending merchants (grouped by description) in range.

    Pure "where does my money actually go" view — complements the category
    pie which only shows broad buckets. Skipped if there are no expenses or
    no descriptions in the period.
    """
    df_expenses = filtered_df[filtered_df['type'] == 'Expense'].copy()
    df_expenses = df_expenses[df_expenses['description'].fillna("").str.strip() != ""]
    if df_expenses.empty:
        return

    top = (df_expenses.groupby('description')['amount']
           .sum().sort_values(ascending=False).head(5).reset_index())
    top.columns = ['Paid to', 'Total spent']
    top['Total spent'] = top['Total spent'].map(lambda v: db.format_money(v))

    st.subheader("🏆 Where most of your money went")
    st.dataframe(top, use_container_width=True, hide_index=True)


def _render_recent_transactions(filtered_df: pd.DataFrame) -> None:
    """Render the small preview table of the most recent transactions in range (up to 10)."""
    st.subheader("Latest transactions")
    display = filtered_df.copy()
    display['date'] = display['date'].dt.strftime('%d %b %Y')
    display['amount'] = display.apply(lambda r: signed_money(r['amount'], r['type']), axis=1)
    display = display.head(10)[['date', 'type', 'category', 'amount', 'description']]
    display.columns = ['Date', 'Type', 'Category', 'Amount', 'Description']
    st.dataframe(display, use_container_width=True, hide_index=True)


def render_dashboard():
    """Top-level entry point for the Dashboard page."""
    st.title("📊 Dashboard")
    st.markdown("---")

    df_trans = db.get_all_transactions()
    net_worth = db.get_net_worth()

    # Empty state: same metric layout but with zeros, plus a helpful nudge
    # and a one-click "Load demo data" button so brand-new users can see what
    # every part of the dashboard is supposed to look like.
    if df_trans.empty:
        _render_metrics(df_trans, net_worth)
        st.info("Welcome! Add your first transaction on the **Transactions** page "
                "and this page will fill in with your totals and charts.")
        sample_data_button(key="sample_from_dashboard")
        return

    df_trans['date'] = pd.to_datetime(df_trans['date'])
    filtered_df, filter_option = _render_filters(df_trans)

    # "vs last month" deltas only make sense when the view is scoped to this month.
    deltas = _mom_deltas(df_trans) if filter_option == "This Month" else None
    _render_metrics(filtered_df, net_worth, deltas)

    _render_spending_limits(df_trans, db.get_all_budgets())

    st.markdown("<br>", unsafe_allow_html=True)

    if filtered_df.empty:
        st.info("No transactions found in this date range.")
        return

    _render_charts(filtered_df)
    _render_top_merchants(filtered_df)
    _render_recent_transactions(filtered_df)
