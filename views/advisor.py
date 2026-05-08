"""
advisor.py — AI Financial Advisor page.

Two tools in one:
  1. Calculators — 50/30/20 budget breakdown + compound interest visualiser
  2. AI Chat — conversational assistant powered by Google Gemini
"""

import streamlit as st
import pandas as pd
import database as db
from google import genai
from google.genai import types


def _top_expense_categories(df_trans: pd.DataFrame, n: int = 3) -> list:
    """Return the top n expense categories by total amount, as (name, total) tuples."""
    if df_trans.empty:
        return []
    expenses = df_trans[df_trans['type'] == 'Expense']
    if expenses.empty:
        return []
    grouped = expenses.groupby('category')['amount'].sum().sort_values(ascending=False)
    return list(grouped.head(n).items())


def _build_finance_context(total_income: float, total_expense: float,
                           net_balance: float, net_worth: float,
                           top_categories: list) -> str:
    """Build the context prompt that gives the AI your financial summary."""
    savings_rate = (net_balance / total_income * 100) if total_income > 0 else 0.0
    if top_categories:
        top_lines = "\n    ".join(f"- {cat}: ${amt:,.2f}" for cat, amt in top_categories)
        top_section = f"Top spending categories:\n    {top_lines}"
    else:
        top_section = "Top spending categories: (no expenses logged yet)"

    return f"""
    You are an expert, helpful personal finance assistant.
    Here is the user's current financial context:
    - Total Logged Income: ${total_income:,.2f}
    - Total Logged Expenses: ${total_expense:,.2f}
    - Net Balance (Income - Expense): ${net_balance:,.2f}
    - Savings Rate: {savings_rate:.1f}%
    - Total Net Worth (Sum of Accounts): ${net_worth:,.2f}
    {top_section}

    Please use this context to provide personalized, specific, and actionable advice.
    Keep your answers concise, encouraging, and formatted with markdown.
    """


def _render_api_key_sidebar() -> str:
    """Show Gemini API key input in the sidebar; return the active key (or '')."""
    if "gemini_api_key" not in st.session_state:
        st.session_state.gemini_api_key = ""

    st.sidebar.markdown("### 🔑 Gemini API Key")
    if st.session_state.gemini_api_key:
        st.sidebar.success("Key set for this session.")
        if st.sidebar.button("Clear Key", use_container_width=True):
            st.session_state.gemini_api_key = ""
            st.rerun()
    else:
        entered = st.sidebar.text_input(
            "Enter key to enable AI chat",
            type="password",
            help="Stored only for this browser session — never written to disk."
        )
        if entered:
            st.session_state.gemini_api_key = entered
            st.rerun()

    return st.session_state.gemini_api_key


def _avg_monthly_income(df_trans: pd.DataFrame) -> float:
    """Average monthly income across the months the user has data for."""
    if df_trans.empty:
        return 0.0
    income_df = df_trans[df_trans['type'] == 'Income']
    if income_df.empty:
        return 0.0
    months_active = income_df['date'].dt.to_period('M').nunique()
    return income_df['amount'].sum() / months_active if months_active else 0.0


def _render_calculators_tab(df_trans: pd.DataFrame) -> None:
    """50/30/20 rule + compound interest visualiser."""
    st.subheader("The 50/30/20 Rule")
    st.write("A popular rule of thumb for budgeting your income:")

    avg_income = _avg_monthly_income(df_trans)
    default_income = avg_income if avg_income > 0 else 4000.0
    help_txt = (f"Pre-filled with your average monthly income (${avg_income:,.2f}). Edit if needed."
                if avg_income > 0 else
                "Add some income transactions to auto-fill this from your data.")

    income_input = st.number_input(
        "Monthly Net Income for projection ($):",
        min_value=1.0, value=default_income, step=100.0, help=help_txt,
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Needs (50%)", f"${income_input * 0.5:,.2f}")
    c1.caption("Housing, groceries, utilities, minimum debt payments.")
    c2.metric("Wants (30%)", f"${income_input * 0.3:,.2f}")
    c2.caption("Entertainment, dining out, hobbies.")
    c3.metric("Savings & Debt (20%)", f"${income_input * 0.2:,.2f}")
    c3.caption("Investments, emergency fund, extra debt payments.")

    st.markdown("---")

    st.subheader("📈 Compound Interest Visualizer")
    st.write("See how your investments could grow over time.")

    c1, c2, c3, c4 = st.columns(4)
    principal = c1.number_input("Starting Amount ($)", min_value=0, value=1000, step=100)
    monthly_contrib = c2.number_input("Monthly Contribution ($)", min_value=0, value=200, step=50)
    years = c3.slider("Years to Grow", min_value=1, max_value=40, value=10)
    rate = c4.number_input("Annual Return (%)", min_value=0.0, max_value=30.0, value=7.0, step=0.5) / 100.0

    amounts, current = [], principal
    for year in range(1, years + 1):
        for _ in range(12):
            current += monthly_contrib
            current *= (1 + rate / 12)
        amounts.append({"Year": year, "Future Value": round(current, 2)})

    df_growth = pd.DataFrame(amounts)
    st.line_chart(df_growth.set_index("Year"))

    total_contributed = principal + (monthly_contrib * 12 * years)
    total_interest = amounts[-1]['Future Value'] - total_contributed

    m1, m2, m3 = st.columns(3)
    m1.metric(f"Projected Value ({years}yr)", f"${amounts[-1]['Future Value']:,.2f}")
    m2.metric("Total Contributed", f"${total_contributed:,.2f}")
    m3.metric("Interest Earned", f"${total_interest:,.2f}")


def _render_chat_tab(api_key: str, finance_context: str) -> None:
    """Conversational Gemini chat anchored to the user's financial context."""
    st.subheader("Personalized Q&A")
    st.write("Ask questions and get advice based on your current tracking data.")

    with st.expander("View Data sent to AI", expanded=False):
        st.text(finance_context)

    if "messages" not in st.session_state:
        st.session_state.messages = [{
            "role": "assistant",
            "content": "Hello! I am your AI financial advisor. How can I help you "
                       "optimize your finances today based on your current data?"
        }]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("Ask a finance question...")
    if not prompt:
        return

    if not api_key:
        st.error("Please enter a Gemini API Key in the sidebar first.")
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        try:
            client = genai.Client(api_key=api_key)
            contents = [types.Content(role="user", parts=[types.Part.from_text(text=finance_context)])]
            contents += [
                types.Content(role=m["role"] if m["role"] == "user" else "model",
                              parts=[types.Part.from_text(text=m["content"])])
                for m in st.session_state.messages
            ]

            response = client.models.generate_content(
                model='gemini-2.5-flash', contents=contents,
                config=types.GenerateContentConfig(temperature=0.7)
            )

            placeholder.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            # Roll back the unanswered user message so history stays balanced.
            st.session_state.messages.pop()
            st.error(f"Error generating response: {str(e)}")


def render_advisor():
    """Render the AI Financial Advisor page."""
    st.header("🧠 AI Financial Advisor")

    api_key = _render_api_key_sidebar()

    df_trans = db.get_all_transactions()
    if not df_trans.empty:
        df_trans['date'] = pd.to_datetime(df_trans['date'])
    net_worth = db.get_net_worth()
    total_income = df_trans[df_trans['type'] == 'Income']['amount'].sum() if not df_trans.empty else 0
    total_expense = df_trans[df_trans['type'] == 'Expense']['amount'].sum() if not df_trans.empty else 0
    net_balance = total_income - total_expense

    top_categories = _top_expense_categories(df_trans)
    finance_context = _build_finance_context(
        total_income, total_expense, net_balance, net_worth, top_categories
    )

    st.markdown("---")
    tab1, tab2 = st.tabs(["📊 Calculators & Rules", "💬 Chat with AI"])
    with tab1:
        _render_calculators_tab(df_trans)
    with tab2:
        _render_chat_tab(api_key, finance_context)
