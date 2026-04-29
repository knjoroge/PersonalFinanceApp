"""
advisor.py — The AI Financial Advisor page.

This view provides two tools:
  1. Calculators & Rules — a 50/30/20 budgeting breakdown and a compound
     interest visualiser that shows how investments grow over time.
  2. Chat with AI — a conversational assistant (powered by Google Gemini)
     that can answer personal finance questions using your actual data.

The AI features require a free Google Gemini API key, which the user
enters on this page. The key is stored only for the current session
and is never saved to disk.
"""

import streamlit as st
import pandas as pd
import database as db
from google import genai
from google.genai import types


def render_advisor():
    """Renders the AI Financial Advisor page with calculators and chat."""

    st.header("🧠 AI Financial Advisor")

    # --- API Key Setup ---
    # The Gemini API key is kept in the browser session only.
    # It's needed for the AI chat but NOT for the calculators.
    if "gemini_api_key" not in st.session_state:
        st.session_state.gemini_api_key = ""

    api_key = st.session_state.gemini_api_key
    if not api_key:
        entered_key = st.text_input(
            "Enter your Gemini API Key to use the Assistant:", type="password"
        )
        if entered_key:
            st.session_state.gemini_api_key = entered_key
            api_key = entered_key
            st.success("API Key saved for this session!")
            st.rerun()
        else:
            st.warning("Please provide a Gemini API Key to unlock personalized AI advice.")

    # --- Load Your Financial Data ---
    df_trans = db.get_all_transactions()
    net_worth = db.get_net_worth()

    total_income = 0
    total_expense = 0
    if not df_trans.empty:
        total_income = df_trans[df_trans['type'] == 'Income']['amount'].sum()
        total_expense = df_trans[df_trans['type'] == 'Expense']['amount'].sum()

    net_balance = total_income - total_expense

    st.markdown("---")

    tab1, tab2 = st.tabs(["📊 Calculators & Rules", "💬 Chat with AI"])

    # =================================================================
    #  TAB 1: CALCULATORS
    # =================================================================
    with tab1:

        # --- 50/30/20 Rule ---
        # A well-known budgeting guideline:
        #   50% of income → Needs (rent, food, bills)
        #   30% of income → Wants (entertainment, hobbies)
        #   20% of income → Savings & debt repayment
        st.subheader("The 50/30/20 Rule")
        st.write("A popular rule of thumb for budgeting your income:")

        income_input = st.number_input(
            "Enter your Monthly Net Income for projection ($):",
            min_value=1.0,
            value=total_income if total_income > 0 else 4000.0,
            step=100.0
        )

        col_n, col_w, col_s = st.columns(3)
        with col_n:
            st.metric("Needs (50%)", f"${(income_input * 0.5):,.2f}")
            st.caption("Housing, groceries, utilities, minimum debt payments.")
        with col_w:
            st.metric("Wants (30%)", f"${(income_input * 0.3):,.2f}")
            st.caption("Entertainment, dining out, hobbies.")
        with col_s:
            st.metric("Savings & Debt (20%)", f"${(income_input * 0.2):,.2f}")
            st.caption("Investments, emergency fund, extra debt payments.")

        st.markdown("---")

        # --- Compound Interest Visualiser ---
        # Shows how an investment grows over time with monthly contributions
        # and a fixed annual return rate, compounded monthly.
        st.subheader("📈 Compound Interest Visualizer")
        st.write("See how your investments could grow over time.")

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            principal = st.number_input("Starting Amount ($)", value=1000)
        with c2:
            monthly_contrib = st.number_input("Monthly Contribution ($)", value=200)
        with c3:
            years = st.slider("Years to Grow", min_value=1, max_value=40, value=10)
        with c4:
            rate = st.number_input("Annual Return (%)", min_value=0.0,
                                   max_value=30.0, value=7.0, step=0.5) / 100.0

        # Calculate the growth curve year by year
        amounts = []
        current = principal
        for year in range(1, years + 1):
            for _ in range(12):  # 12 months per year
                current += monthly_contrib
                current *= (1 + (rate / 12))  # Monthly compounding
            amounts.append({"Year": year, "Future Value": round(current, 2)})

        df_growth = pd.DataFrame(amounts)
        st.line_chart(df_growth.set_index("Year"))

        # Show summary numbers below the chart
        total_contributed = principal + (monthly_contrib * 12 * years)
        total_interest = amounts[-1]['Future Value'] - total_contributed

        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric(f"Projected Value ({years}yr)", f"${amounts[-1]['Future Value']:,.2f}")
        with m2:
            st.metric("Total Contributed", f"${total_contributed:,.2f}")
        with m3:
            st.metric("Interest Earned", f"${total_interest:,.2f}")

    # =================================================================
    #  TAB 2: AI CHAT
    # =================================================================
    with tab2:
        st.subheader("Personalized Q&A")
        st.write("Ask questions and get advice based on your current tracking data.")

        # Build a context prompt that gives the AI your financial summary.
        # This is sent along with every message so the AI can give
        # personalised answers based on your actual numbers.
        finance_context = f"""
        You are an expert, helpful personal finance assistant. 
        Here is the user's current financial context:
        - Total Logged Income: ${total_income:,.2f}
        - Total Logged Expenses: ${total_expense:,.2f}
        - Net Balance (Income - Expense): ${net_balance:,.2f}
        - Total Net Worth (Sum of Accounts): ${net_worth:,.2f}
        
        Please use this context to provide personalized, specific, and actionable advice. 
        Keep your answers concise, encouraging, and formatted with markdown.
        """

        # Let the user see exactly what data is being shared with the AI
        with st.expander("View Data sent to AI", expanded=False):
            st.text(finance_context)

        # --- Chat History ---
        # Messages are stored in the session so the conversation persists
        # as long as the browser tab is open.
        if "messages" not in st.session_state:
            st.session_state.messages = []
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Hello! I am your AI financial advisor. How can I help you "
                           "optimize your finances today based on your current data?"
            })

        # Display all previous messages in the chat
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Handle new user input
        if prompt := st.chat_input("Ask a finance question..."):
            if not api_key:
                st.error("Please enter a Gemini API Key at the top of the page first.")
            else:
                # Add the user's message to the chat history
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                # Generate the AI's response
                with st.chat_message("assistant"):
                    message_placeholder = st.empty()
                    try:
                        client = genai.Client(api_key=api_key)

                        # Build the full conversation history for the AI,
                        # starting with the financial context
                        contents = [
                            types.Content(role="user",
                                          parts=[types.Part.from_text(text=finance_context)])
                        ]
                        for msg in st.session_state.messages:
                            contents.append(
                                types.Content(
                                    role=msg["role"] if msg["role"] == "user" else "model",
                                    parts=[types.Part.from_text(text=msg["content"])]
                                )
                            )

                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=contents,
                            config=types.GenerateContentConfig(temperature=0.7)
                        )

                        full_response = response.text
                        message_placeholder.markdown(full_response)
                        st.session_state.messages.append({
                            "role": "assistant", "content": full_response
                        })

                    except Exception as e:
                        st.error(f"Error generating response: {str(e)}")
