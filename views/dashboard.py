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


def _render_budget_tracker(filtered_df: pd.DataFrame, budgets_df: pd.DataFrame) -> None:
    """Show colour-coded progress bars for each category budget."""
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
            st.caption(f"${spent:,.0f} / ${limit:,.0f} ({progress*100:.0f}%)")

    st.markdown("<br>", unsafe_allow_html=True)


def render_dashboard():
    """Render the full financial dashboard page."""

    st.title("📊 Financial Dashboard")
    st.markdown("---")

    df_trans = db.get_all_transactions()
    net_worth = db.get_net_worth()

    if not df_trans.empty:
        df_trans['date'] = pd.to_datetime(df_trans['date'])

        # --- Sidebar: time period filter ---
        st.sidebar.markdown("### Dashboard Filters")
        filter_option = st.sidebar.selectbox(
            "Time Period",
            ("All Time", "This Month", "Last Month", "Last 90 Days", "Custom Range")
        )

        today = datetime.today()
        start_date = df_trans['date'].min().date()
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
            else:
                st.sidebar.warning("Please select both a start and end date.")

        mask = (df_trans['date'].dt.date >= start_date) & (df_trans['date'].dt.date <= end_date)
        filtered_df = df_trans.loc[mask]

        # --- Key metrics ---
        total_income = filtered_df[filtered_df['type'] == 'Income']['amount'].sum()
        total_expense = filtered_df[filtered_df['type'] == 'Expense']['amount'].sum()
        net_balance = total_income - total_expense
        savings_rate = ((total_income - total_expense) / total_income * 100) if total_income > 0 else 0

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total Income", f"${total_income:,.2f}")
        m2.metric("Total Expenses", f"${total_expense:,.2f}", delta=f"-${total_expense:,.2f}", delta_color="inverse")
        m3.metric("Net Period Balance", f"${net_balance:,.2f}")
        m4.metric("Savings Rate", f"{savings_rate:.1f}%")
        m5.metric("Total Net Worth", f"${net_worth:,.2f}")

        st.markdown("<br>", unsafe_allow_html=True)

        # --- Budget progress ---
        budgets_df = db.get_all_budgets()
        if not budgets_df.empty:
            _render_budget_tracker(filtered_df, budgets_df)

        # --- Monthly expense goal ---
        with st.expander("🎯 Monthly Expense Goal", expanded=False):
            goal_amount = st.number_input("Set your monthly expense goal ($):", min_value=1.0, value=2000.0, step=100.0)
            progress = min(total_expense / goal_amount, 1.0) if goal_amount > 0 else 0
            icon = "🟢" if progress < 0.8 else "🟡" if progress < 1.0 else "🔴"
            st.progress(progress)
            st.caption(f"{icon} You have spent **${total_expense:,.2f}** of your **${goal_amount:,.2f}** goal ({progress*100:.1f}%).")

        # --- Manage category budgets ---
        with st.expander("📝 Manage Category Budgets", expanded=False):
            with st.form("budget_form"):
                b_col1, b_col2 = st.columns(2)
                with b_col1:
                    expense_categories = ["Housing", "Food", "Transportation", "Utilities", "Insurance",
                                          "Healthcare", "Savings", "Debt", "Entertainment", "Other"]
                    budget_cat = st.selectbox("Category", expense_categories)
                with b_col2:
                    budget_limit = st.number_input("Monthly Budget ($)", min_value=1.0, value=500.0, step=50.0)

                if st.form_submit_button("Set Budget", use_container_width=True):
                    db.set_budget(budget_cat, budget_limit)
                    st.toast(f"Budget set for {budget_cat}!", icon="✅")
                    st.rerun()

            if not budgets_df.empty:
                st.dataframe(budgets_df[['category', 'monthly_limit']], use_container_width=True, hide_index=True)
                budget_options = {f"{r['category']} (${r['monthly_limit']:,.0f})": r['id'] for _, r in budgets_df.iterrows()}
                del_budget = st.selectbox("Remove Budget", list(budget_options.keys()))
                if st.button("Remove", key="del_budget_btn"):
                    db.delete_budget(budget_options[del_budget])
                    st.toast("Budget removed.", icon="🗑️")
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        # --- Charts ---
        if not filtered_df.empty:
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Expenses by Category")
                df_expenses = filtered_df[filtered_df['type'] == 'Expense']
                if not df_expenses.empty:
                    grouped = df_expenses.groupby('category')['amount'].sum().reset_index()
                    fig = px.pie(grouped, values='amount', names='category', hole=0.4,
                                 color_discrete_sequence=px.colors.sequential.Plasma)
                    fig.update_layout(margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No expense data in this period.")

            with col2:
                st.subheader("Income vs Expenses Over Time")
                trend_df = filtered_df.groupby([filtered_df['date'].dt.date, 'type'])['amount'].sum().reset_index()
                if not trend_df.empty:
                    fig = px.scatter(trend_df, x='date', y='amount', color='type',
                                    color_discrete_map={"Income": "#10B981", "Expense": "#EF4444"},
                                    trendline="lowess", trendline_options=dict(frac=0.3))
                    fig.add_traces(
                        px.bar(trend_df, x='date', y='amount', color='type', barmode='group',
                               color_discrete_map={"Income": "#10B981", "Expense": "#EF4444"}, opacity=0.5).data
                    )
                    fig.update_layout(margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No trend data available.")

            # Recent transactions preview
            st.subheader("Recent Transactions (Filtered)")
            display = filtered_df.copy()
            display['date'] = display['date'].dt.strftime('%Y-%m-%d')
            st.dataframe(display.head(10)[['date', 'type', 'category', 'amount', 'description']],
                         use_container_width=True, hide_index=True)
        else:
            st.info("No transactions found in this date range.")
    else:
        # Empty database placeholder
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Income", "$0.00")
        m2.metric("Total Expenses", "$0.00")
        m3.metric("Net Balance", "$0.00")
        m4.metric("Total Net Worth", f"${net_worth:,.2f}")
        st.info("Add some transactions in the 'Transactions' tab to see your dashboard come to life!")
