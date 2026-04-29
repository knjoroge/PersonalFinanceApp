"""
dashboard.py — The main financial dashboard view.

This page gives you a bird's-eye view of your finances. It shows:
  - Key numbers: total income, expenses, net balance, savings rate, net worth
  - Budget progress bars for each spending category
  - Charts: spending by category (pie) and income vs expenses over time
  - A quick table of your most recent transactions

You can filter everything by time period using the sidebar controls.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import database as db
from datetime import datetime, timedelta


def render_dashboard():
    """Renders the full financial dashboard page."""

    st.title("📊 Financial Dashboard")
    st.markdown("---")

    # Load all transactions and net worth from the database
    df_trans = db.get_all_transactions()
    net_worth = db.get_net_worth()

    if not df_trans.empty:
        # Convert date strings to proper date objects for filtering and charting
        df_trans['date'] = pd.to_datetime(df_trans['date'])

        # --- Sidebar: Time Period Filter ---
        st.sidebar.markdown("### Dashboard Filters")

        filter_option = st.sidebar.selectbox(
            "Time Period",
            ("All Time", "This Month", "Last Month", "Last 90 Days", "Custom Range")
        )

        today = datetime.today()
        start_date = df_trans['date'].min().date()
        end_date = today.date()

        # Adjust the date range based on the user's selection
        if filter_option == "This Month":
            start_date = today.replace(day=1).date()
        elif filter_option == "Last Month":
            first_of_this_month = today.replace(day=1)
            last_of_last_month = first_of_this_month - timedelta(days=1)
            start_date = last_of_last_month.replace(day=1).date()
            end_date = last_of_last_month.date()
        elif filter_option == "Last 90 Days":
            start_date = (today - timedelta(days=90)).date()
        elif filter_option == "Custom Range":
            date_range = st.sidebar.date_input("Select Date Range", [start_date, end_date])
            if len(date_range) == 2:
                start_date, end_date = date_range
            else:
                st.sidebar.warning("Please select both a start and end date.")

        # Keep only transactions within the chosen date range
        mask = (df_trans['date'].dt.date >= start_date) & (df_trans['date'].dt.date <= end_date)
        filtered_df = df_trans.loc[mask]

        # --- Calculate Key Financial Metrics ---
        total_income = filtered_df[filtered_df['type'] == 'Income']['amount'].sum()
        total_expense = filtered_df[filtered_df['type'] == 'Expense']['amount'].sum()
        net_balance = total_income - total_expense
        # Savings rate = what percentage of income you kept (didn't spend)
        savings_rate = ((total_income - total_expense) / total_income * 100) if total_income > 0 else 0

        # --- Display the Key Numbers at the Top ---
        m1, m2, m3, m4, m5 = st.columns(5)
        with m1:
            st.metric(label="Total Income", value=f"${total_income:,.2f}")
        with m2:
            st.metric(label="Total Expenses", value=f"${total_expense:,.2f}", delta=f"-${total_expense:,.2f}", delta_color="inverse")
        with m3:
            st.metric(label="Net Period Balance", value=f"${net_balance:,.2f}")
        with m4:
            st.metric(label="Savings Rate", value=f"{savings_rate:.1f}%")
        with m5:
            st.metric(label="Total Net Worth", value=f"${net_worth:,.2f}")

        st.markdown("<br>", unsafe_allow_html=True)

        # --- Budget Progress Bars ---
        # Show how much you've spent vs. your budget for each category
        # Colour key: 🟢 under 80%, 🟡 80–99%, 🔴 at or over budget
        budgets_df = db.get_all_budgets()
        if not budgets_df.empty:
            st.markdown("### 🎯 Category Budget Tracker")

            df_expenses = filtered_df[filtered_df['type'] == 'Expense']
            expense_by_cat = df_expenses.groupby('category')['amount'].sum() if not df_expenses.empty else pd.Series(dtype=float)

            budget_cols = st.columns(min(len(budgets_df), 4))
            for idx, (_, budget_row) in enumerate(budgets_df.iterrows()):
                col = budget_cols[idx % len(budget_cols)]
                cat = budget_row['category']
                limit = budget_row['monthly_limit']
                spent = expense_by_cat.get(cat, 0.0)
                progress = min(spent / limit, 1.0) if limit > 0 else 0

                with col:
                    status = "🟢" if progress < 0.8 else "🟡" if progress < 1.0 else "🔴"
                    st.markdown(f"**{status} {cat}**")
                    st.progress(progress)
                    st.caption(f"${spent:,.0f} / ${limit:,.0f} ({progress*100:.0f}%)")

            st.markdown("<br>", unsafe_allow_html=True)

        # --- Monthly Expense Goal ---
        with st.expander("🎯 Monthly Expense Goal", expanded=False):
            goal_amount = st.number_input("Set your monthly expense goal ($):", min_value=1.0, value=2000.0, step=100.0)

            progress = min(total_expense / goal_amount, 1.0) if goal_amount > 0 else 0
            progress_color = "🟢" if progress < 0.8 else "🟡" if progress < 1.0 else "🔴"

            st.progress(progress)
            st.caption(f"{progress_color} You have spent **${total_expense:,.2f}** of your **${goal_amount:,.2f}** goal ({progress*100:.1f}%).")

        # --- Manage Category Budgets ---
        with st.expander("📝 Manage Category Budgets", expanded=False):
            with st.form("budget_form"):
                b_col1, b_col2 = st.columns(2)
                with b_col1:
                    expense_categories = ["Housing", "Food", "Transportation", "Utilities", "Insurance", "Healthcare", "Savings", "Debt", "Entertainment", "Other"]
                    budget_cat = st.selectbox("Category", expense_categories)
                with b_col2:
                    budget_limit = st.number_input("Monthly Budget ($)", min_value=1.0, value=500.0, step=50.0)

                if st.form_submit_button("Set Budget", use_container_width=True):
                    db.set_budget(budget_cat, budget_limit)
                    st.toast(f"Budget set for {budget_cat}!", icon="✅")
                    st.rerun()

            # Show existing budgets with option to remove
            if not budgets_df.empty:
                st.dataframe(budgets_df[['category', 'monthly_limit']], use_container_width=True, hide_index=True)

                budget_options = {f"{row['category']} (${row['monthly_limit']:,.0f})": row['id'] for _, row in budgets_df.iterrows()}
                del_budget = st.selectbox("Remove Budget", list(budget_options.keys()))
                if st.button("Remove", key="del_budget_btn"):
                    db.delete_budget(budget_options[del_budget])
                    st.toast("Budget removed.", icon="🗑️")
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        # --- Charts Section ---
        if not filtered_df.empty:
            col1, col2 = st.columns(2)

            # Pie chart: breakdown of expenses by category
            with col1:
                st.subheader("Expenses by Category")
                df_expenses = filtered_df[filtered_df['type'] == 'Expense']
                if not df_expenses.empty:
                    expense_grouped = df_expenses.groupby('category')['amount'].sum().reset_index()
                    fig_pie = px.pie(
                        expense_grouped,
                        values='amount',
                        names='category',
                        hole=0.4,
                        color_discrete_sequence=px.colors.sequential.Plasma
                    )
                    fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.info("No expense data in this period.")

            # Bar + trendline chart: income vs expenses over time
            with col2:
                st.subheader("Income vs Expenses Over Time")
                trend_df = filtered_df.groupby([filtered_df['date'].dt.date, 'type'])['amount'].sum().reset_index()
                if not trend_df.empty:
                    fig_bar = px.scatter(
                        trend_df, x='date', y='amount', color='type',
                        color_discrete_map={"Income": "#10B981", "Expense": "#EF4444"},
                        trendline="lowess",
                        trendline_options=dict(frac=0.3)
                    )
                    # Add semi-transparent bars behind the trendlines
                    fig_bar.add_traces(
                        px.bar(
                            trend_df, x='date', y='amount', color='type', barmode='group',
                            color_discrete_map={"Income": "#10B981", "Expense": "#EF4444"},
                            opacity=0.5
                        ).data
                    )
                    fig_bar.update_layout(margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig_bar, use_container_width=True)
                else:
                    st.info("No trend data available.")

            # Quick preview of the most recent transactions
            st.subheader("Recent Transactions (Filtered)")
            display_cols = ['date', 'type', 'category', 'amount', 'description']
            recent_display = filtered_df.copy()
            recent_display['date'] = recent_display['date'].dt.strftime('%Y-%m-%d')
            st.dataframe(recent_display.head(10)[display_cols], use_container_width=True, hide_index=True)

        else:
            st.info("No transactions found in this date range.")
    else:
        # Database is empty — show placeholder metrics and a helpful hint
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Income", "$0.00")
        m2.metric("Total Expenses", "$0.00")
        m3.metric("Net Balance", "$0.00")
        m4.metric("Total Net Worth", f"${net_worth:,.2f}")
        st.info("Add some transactions in the 'Transactions' tab to see your dashboard come to life!")
