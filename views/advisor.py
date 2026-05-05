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


def _build_finance_context(total_income: float, total_expense: float,
                           net_balance: float, net_worth: float) -> str:
    """Build the context prompt that gives the AI your financial summary."""
    return f"""
    You are an expert, helpful personal finance assistant.
    Here is the user's current financial context:
    - Total Logged Income: ${total_income:,.2f}
    - Total Logged Expenses: ${total_expense:,.2f}
    - Net Balance (Income - Expense): ${net_balance:,.2f}
    - Total Net Worth (Sum of Accounts): ${net_worth:,.2f}

    Please use this context to provide personalized, specific, and actionable advice.
    Keep your answers concise, encouraging, and formatted with markdown.
    """


def render_advisor():
    """Render the AI Financial Advisor page."""

    st.header("🧠 AI Financial Advisor")

    # --- API key setup (session-only, never saved to disk) ---
    if "gemini_api_key" not in st.session_state:
        st.session_state.gemini_api_key = ""

    api_key = st.session_state.gemini_api_key
    if not api_key:
        entered_key = st.text_input("Enter your Gemini API Key to use the Assistant:", type="password")
        if entered_key:
            st.session_state.gemini_api_key = entered_key
            api_key = entered_key
            st.success("API Key saved for this session!")
            st.rerun()
        else:
            st.warning("Please provide a Gemini API Key to unlock personalized AI advice.")

    # --- Load financial data ---
    df_trans = db.get_all_transactions()
    net_worth = db.get_net_worth()
    total_income = df_trans[df_trans['type'] == 'Income']['amount'].sum() if not df_trans.empty else 0
    total_expense = df_trans[df_trans['type'] == 'Expense']['amount'].sum() if not df_trans.empty else 0
    net_balance = total_income - total_expense

    st.markdown("---")
    tab1, tab2 = st.tabs(["📊 Calculators & Rules", "💬 Chat with AI"])

    # --- Tab 1: Calculators ---
    with tab1:
        # 50/30/20 rule
        st.subheader("The 50/30/20 Rule")
        st.write("A popular rule of thumb for budgeting your income:")

        income_input = st.number_input("Enter your Monthly Net Income for projection ($):",
                                       min_value=1.0, value=total_income if total_income > 0 else 4000.0, step=100.0)

        c1, c2, c3 = st.columns(3)
        c1.metric("Needs (50%)", f"${income_input * 0.5:,.2f}")
        c1.caption("Housing, groceries, utilities, minimum debt payments.")
        c2.metric("Wants (30%)", f"${income_input * 0.3:,.2f}")
        c2.caption("Entertainment, dining out, hobbies.")
        c3.metric("Savings & Debt (20%)", f"${income_input * 0.2:,.2f}")
        c3.caption("Investments, emergency fund, extra debt payments.")

        st.markdown("---")

        # Compound interest visualiser
        st.subheader("📈 Compound Interest Visualizer")
        st.write("See how your investments could grow over time.")

        c1, c2, c3, c4 = st.columns(4)
        principal = c1.number_input("Starting Amount ($)", value=1000)
        monthly_contrib = c2.number_input("Monthly Contribution ($)", value=200)
        years = c3.slider("Years to Grow", min_value=1, max_value=40, value=10)
        rate = c4.number_input("Annual Return (%)", min_value=0.0, max_value=30.0, value=7.0, step=0.5) / 100.0

        # Calculate growth curve
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

    # --- Tab 2: AI Chat ---
    with tab2:
        st.subheader("Personalized Q&A")
        st.write("Ask questions and get advice based on your current tracking data.")

        finance_context = _build_finance_context(total_income, total_expense, net_balance, net_worth)

        with st.expander("View Data sent to AI", expanded=False):
            st.text(finance_context)

        # Chat history (persists for the browser session)
        if "messages" not in st.session_state:
            st.session_state.messages = [{
                "role": "assistant",
                "content": "Hello! I am your AI financial advisor. How can I help you "
                           "optimize your finances today based on your current data?"
            }]

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Ask a finance question..."):
            if not api_key:
                st.error("Please enter a Gemini API Key at the top of the page first.")
            else:
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
                        st.error(f"Error generating response: {str(e)}")
