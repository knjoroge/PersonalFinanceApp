"""
dashboard.py — The main financial overview page.

Shows key stats, budget progress, charts, and recent transactions.
Everything can be filtered by time period using the sidebar.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import database as db
from datetime import datetime, timedelta

from database import EXPENSE_CATEGORIES
from views._shared import confirm_delete_dialog

MONTHLY_GOAL_KEY = "monthly_expense_goal"
DEFAULT_MONTHLY_GOAL = 2000.0


def _open_delete_budget_dialog(budget_id, category, monthly_limit):
    """Open the "are you sure?" pop-up before removing a category budget."""
    body = f"Remove the budget for **{category}** ({db.format_money(monthly_limit, 0)}/month)?"
    caption = ("This only removes the budget — your transactions in this category stay. "
               "This cannot be undone.")
    confirm_delete_dialog(
        title="Remove Budget?",
        body=body,
        caption=caption,
        confirm_label="Remove",
        on_confirm=lambda: (db.delete_budget(budget_id), st.toast("Budget removed.", icon="🗑️")),
        key_suffix=f"bud_{budget_id}",
    )


def _render_filters(df_trans: pd.DataFrame) -> pd.DataFrame:
    """Render the sidebar time-period controls and return only the rows that match.

    Supports preset ranges (This Month, Last Month, Last 90 Days, All Time) and
    a custom date picker.
    """
    st.sidebar.markdown("### Dashboard Filters")
    filter_option = st.sidebar.selectbox(
        "Time Period",
        ("All Time", "This Month", "Last Month", "Last 90 Days", "Custom Range")
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
    return df_trans.loc[mask]


def _render_metrics(filtered_df: pd.DataFrame, net_worth: float) -> None:
    """Render the row of five headline numbers (income, expenses, net, savings, net worth).

    Safe to call with an empty dataframe — all per-period numbers fall back to zero.
    """
    s = db.summarize(filtered_df)
    total_income = s['income']
    total_expense = s['expense']
    net_balance = s['net']
    savings_rate = s['savings_rate']

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Income", db.format_money(total_income))
    m2.metric("Total Expenses", db.format_money(total_expense),
              delta=f"-{db.format_money(total_expense)}" if total_expense > 0 else None,
              delta_color="inverse")
    m3.metric("Net Period Balance", db.format_money(net_balance))
    m4.metric("Savings Rate", f"{savings_rate:.1f}%")
    m5.metric("Total Net Worth", db.format_money(net_worth))

    st.markdown("<br>", unsafe_allow_html=True)


def _render_budget_tracker(filtered_df: pd.DataFrame, budgets_df: pd.DataFrame) -> None:
    """Show colour-coded progress bars for each category budget (green/yellow/red)."""
    st.markdown("### 🎯 Category Budget Tracker")

    df_expenses = filtered_df[filtered_df['type'] == 'Expense']
    expense_by_cat = df_expenses.groupby('category')['amount'].sum() if not df_expenses.empty else pd.Series(dtype=float)

    budget_cols = st.columns(min(len(budgets_df), 4))
    for idx, (_, row) in enumerate(budgets_df.iterrows()):
        col = budget_cols[idx % len(budget_cols)]
        cat, limit = row['category'], row['monthly_limit']
        spent = expense_by_cat.get(cat, 0.0)
        progress = min(spent / limit, 1.0) if limit > 0 else 0

        with col:
            status = "🟢" if progress < 0.8 else "🟡" if progress < 1.0 else "🔴"
            st.markdown(f"**{status} {cat}**")
            st.progress(progress)
            st.caption(f"{db.format_money(spent, 0)} / {db.format_money(limit, 0)} ({progress*100:.0f}%)")

    st.markdown("<br>", unsafe_allow_html=True)


def _render_monthly_goal(df_trans: pd.DataFrame) -> None:
    """Render the "Monthly Expense Goal" expander.

    Always scoped to the current calendar month. The chosen goal amount is
    saved to the preferences table so it persists between sessions.
    """
    today = pd.Timestamp.today()
    this_month = df_trans[df_trans['date'].dt.to_period('M') == today.to_period('M')]
    month_expense = this_month[this_month['type'] == 'Expense']['amount'].sum()

    stored = db.get_preference(MONTHLY_GOAL_KEY)
    saved_goal = float(stored) if stored else DEFAULT_MONTHLY_GOAL

    with st.expander(f"🎯 Monthly Expense Goal ({today.strftime('%B %Y')})", expanded=False):
        g1, g2 = st.columns([4, 1])
        with g1:
            goal_amount = st.number_input(
                f"Set your monthly expense goal ({db.get_currency()}):",
                min_value=1.0, value=saved_goal, step=100.0,
                key="monthly_goal_input",
            )
        with g2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Reset", help=f"Reset to default ({db.format_money(DEFAULT_MONTHLY_GOAL, 0)})"):
                db.set_preference(MONTHLY_GOAL_KEY, DEFAULT_MONTHLY_GOAL)
                st.rerun()

        if goal_amount != saved_goal:
            db.set_preference(MONTHLY_GOAL_KEY, goal_amount)

        progress = min(month_expense / goal_amount, 1.0) if goal_amount > 0 else 0
        icon = "🟢" if progress < 0.8 else "🟡" if progress < 1.0 else "🔴"
        st.progress(progress)
        st.caption(
            f"{icon} You have spent **{db.format_money(month_expense)}** of your "
            f"**{db.format_money(goal_amount)}** goal ({progress*100:.1f}%)."
        )


def _render_manage_budgets(budgets_df: pd.DataFrame) -> None:
    """Render the expander for setting and removing category budgets."""
    with st.expander("📝 Manage Category Budgets", expanded=False):
        with st.form("budget_form"):
            b_col1, b_col2 = st.columns(2)
            with b_col1:
                budget_cat = st.selectbox("Category", EXPENSE_CATEGORIES)
            with b_col2:
                budget_limit = st.number_input(
                    f"Monthly Budget ({db.get_currency()})",
                    min_value=1.0, value=500.0, step=50.0,
                )

            if st.form_submit_button("Set Budget", use_container_width=True):
                db.set_budget(budget_cat, budget_limit)
                st.toast(f"Budget set for {budget_cat}!", icon="✅")
                st.rerun()

        if not budgets_df.empty:
            st.dataframe(budgets_df[['category', 'monthly_limit']], use_container_width=True, hide_index=True)
            budget_options = {
                f"{r['category']} ({db.format_money(r['monthly_limit'], 0)})": r['id']
                for _, r in budgets_df.iterrows()
            }
            del_budget = st.selectbox("Remove Budget", list(budget_options.keys()))
            if st.button("Remove", key="del_budget_btn"):
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
        st.subheader("Expenses by Category")
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
            st.info("No expense data in this period.")

    with col2:
        st.subheader("Income vs Expenses Over Time")
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
            st.info("No trend data available.")


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
    top.columns = ['Merchant', 'Total spent']
    top['Total spent'] = top['Total spent'].map(lambda v: db.format_money(v))

    st.subheader("🏆 Top Merchants (Filtered)")
    st.dataframe(top, use_container_width=True, hide_index=True)


def _render_recent_transactions(filtered_df: pd.DataFrame) -> None:
    """Render the small preview table of the most recent transactions in range (up to 10)."""
    st.subheader("Recent Transactions (Filtered)")
    display = filtered_df.copy()
    display['date'] = display['date'].dt.strftime('%Y-%m-%d')
    display['amount'] = display['amount'].map(lambda v: db.format_money(v))
    st.dataframe(display.head(10)[['date', 'type', 'category', 'amount', 'description']],
                 use_container_width=True, hide_index=True)


def render_dashboard():
    """Top-level entry point for the Dashboard page."""
    st.title("📊 Financial Dashboard")
    st.markdown("---")

    df_trans = db.get_all_transactions()
    net_worth = db.get_net_worth()

    # Empty state: same metric layout but with zeros, plus a helpful nudge
    # and a one-click "Load demo data" button so brand-new users can see what
    # every part of the dashboard is supposed to look like.
    if df_trans.empty:
        _render_metrics(df_trans, net_worth)
        st.info(
            "Add some transactions in the 'Transactions' tab to see your dashboard come to life — "
            "or click below to load a month of sample data so you can explore first."
        )
        if st.button("✨ Load demo data", use_container_width=False):
            count = db.load_demo_data()
            if count:
                st.toast(f"Loaded {count} sample transactions + 3 accounts.", icon="✨")
                st.rerun()
        return

    df_trans['date'] = pd.to_datetime(df_trans['date'])
    filtered_df = _render_filters(df_trans)

    _render_metrics(filtered_df, net_worth)

    budgets_df = db.get_all_budgets()
    if not budgets_df.empty:
        _render_budget_tracker(filtered_df, budgets_df)

    _render_monthly_goal(df_trans)
    _render_manage_budgets(budgets_df)

    st.markdown("<br>", unsafe_allow_html=True)

    if filtered_df.empty:
        st.info("No transactions found in this date range.")
        return

    _render_charts(filtered_df)
    _render_top_merchants(filtered_df)
    _render_recent_transactions(filtered_df)
