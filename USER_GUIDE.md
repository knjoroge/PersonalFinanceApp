# 🚀 Getting Started with Personal Finance Manager

Welcome! This guide walks you through setting up your finances in a few minutes.

---

## ▶️ Opening the App

The easiest way, with no typing:

- **Mac:** double-click **`run.command`**
- **Windows:** double-click **`run.bat`**

You need **Python 3.11 or newer** installed first. Get it free from [python.org](https://www.python.org/downloads/). On Windows, tick **"Add python.exe to PATH"** while installing. If Python is missing or too old, the launcher tells you what to do.

The first time takes about a minute to set things up. After that, double-clicking opens the app in your web browser straight away. Keep the small black window open while you use the app. Closing it stops the app.

> 💡 **Just want to look around first?** On an empty app, click **✨ Show me with sample data**. It fills the app with made-up examples. When you're ready for your own, click **🧹 Remove sample data** at the top of any page. Anything you added yourself stays.

---

## 🏦 Step 1: Add Your Accounts

Tell the app about your bank accounts, savings, pensions, investments **and any debts**. Together they make up your **net worth**: what you own minus what you owe.

1. Click **Net Worth & Accounts** on the left.
2. Leave **Which account?** on **➕ Add a new account** and type a name (for example "Chase Checking", "Pension", or "Amex Card").
3. Pick the account type. This tells the app whether it's something you own or owe:
    - **You own it:** Checking, Savings, 401k, Pension, Shares/Brokerage, Real Estate, Other Assets.
    - **You owe it:** Credit Card, Mortgage, Loan, Other Liabilities.
4. Type the balance as a normal number (for example `4500`), even for debts.
5. Click **Add Account**.

Once a month or so, update each one: pick it from **Which account?**, type the new balance, and click **Save New Balance**.

The page shows **What you own**, **What you owe**, and your **Net worth**.

---

## 📝 Step 2: Add Your Transactions

A transaction is any money coming in (like your pay) or going out (like rent or shopping).

1. Click **Transactions** on the left.
2. Fill in the **➕ Add a transaction** form: whether it's Income or Expense, the date, the amount, a category, and a note if you like.
3. Click **Save**. The form stays open so you can add the next one.

> 💡 The **shortcut buttons** at the top of the form (Salary, Rent, Coffee and so on) fill the form in for you. Change anything you need, then click Save.

### 🔎 Finding and fixing transactions

Under the form you'll find all your transactions:
- Narrow them down by **Type**, **Category** or **Date range**, or type in the **Search** box (for example "amazon" or "50").
- Money in shows with a `+`, money out with a `-`. Totals for what's shown appear just above the list.
- Click **✖ Show everything again** to clear your search.
- **Tick the box** at the start of a row to change or delete it.
- **Tick several rows** to delete them together, or to give them all the same category at once. This is handy after importing from your bank.

### 📁 Import from Your Bank (the easy way)

You don't have to type everything in by hand:

1. Sign in to your bank's website.
2. Look for an option to **download** or **export** your transactions as a **CSV** file. It's often under "Statements" or "Account activity".
3. In the app, open **📁 Import from your bank, or download your transactions** on the Transactions page.
4. Choose the file and click **📥 Import**.

The app recognises most banks' files. Money out becomes Expenses and money in becomes Income. If the file has no categories, the app guesses them from the description (for example "TESCO" → Food, "Uber" → Transportation). Anything it can't guess becomes "Other". You can fix those quickly by ticking them and using **Change category**.

**Dates:** banks write dates differently (31/12 in the UK, 12/31 in the US). The app works it out from your file. If it can't tell, it shows you a date from your file and asks which one it is.

> 💡 **Importing the same statement twice is safe.** Transactions already in the app are skipped, so you won't get duplicates.

### 🛠️ If the app doesn't recognise your bank's file

You'll see a short form instead of the Import button:

1. The first 5 lines of your file are shown, so you can see what's in it.
2. For **Date** and **Amount**, pick the matching column from your file. Description and Category are optional.
3. If your bank uses **two columns**, one for money out and one for money in, leave Amount as *(not in my file)* and pick **Money out** and **Money in** instead.
4. Want to skip this next month? Open **💾 Remember this layout for next month** and give it a name, like your bank's name.
5. Click **✅ Import**.

---

## 💱 Switching Currency

On the left, under **💱 Display Currency**, pick **$**, **£** or **€**. Every amount in the app then shows with that symbol.

> **Heads up:** this only changes the symbol. It doesn't convert any amounts. Your $1,200 rent would show as £1,200.

Your choice is remembered next time.

---

## 🎯 Step 3: Set Spending Limits

Want to keep your spending in check? Set a limit for each month.

1. Click **Dashboard** on the left.
2. Open **✏️ Set spending limits**.
3. Set **one limit for all your spending**, a **limit for a single category** like Food, or both.

Coloured bars on the Dashboard show how you're doing this month:
- 🟢 Under 80% used: you're on track
- 🟡 80–100% used: getting close
- 🔴 Over 100%: you've gone over

Limits are always for the current month, whatever time period the Dashboard is showing.

---

## 📊 Step 4: Check Your Dashboard

Once you've added some transactions, the Dashboard shows:
- **Money in**, **Money out**, what's **Left over**, how much you **Saved**, and your **Net worth**. On "This Month", small numbers show the change compared with last month.
- A chart of **what you spent on**, and a chart of **money in vs money out**.
- **Where most of your money went**, and your latest transactions.

Use **📅 Show me** on the left to pick a time period, like "This Month" or "Last 90 Days".

---

## 🧠 Step 5: The AI Advisor

The AI Advisor page has two parts:

1. **📊 Planning tools:** the 50/30/20 rule for splitting up your monthly pay, and a tool showing **how savings can grow** over the years.
2. **💬 Chat with AI:** ask questions about your money and get answers from Google's Gemini AI.

### Turning on the AI chat

The chat needs a free **Gemini key** from Google:

1. In the left sidebar on the AI Advisor page, click **"Get a free key →"**.
2. Sign in with Google and click *Create API key*.
3. Copy the key and paste it into the **🔑 Key for AI chat** box in the sidebar. It will say **"AI chat is on."**

The key is only kept until you close the app. To skip pasting it every time, create a file called `.env` in the app folder containing `GEMINI_API_KEY=your-key-here`.

**🔒 What the AI sees:**
* **Not your individual transactions.** Only a short summary: your total money in and out, what's left over, how much you saved, your net worth, and your top 3 spending categories.
* Open **"See exactly what's shared with the AI"** above the chat to see it word for word.
* Your key is never saved in the app's data.

**Questions you could ask:**
- *"How can I spend less on food?"*
- *"Am I saving enough, going by the 50/30/20 rule?"*
- *"How long would it take me to save $5,000 for an emergency fund?"*

---

## 💾 Step 6: Keep a Backup

Your data stays on your computer, not online. The app saves a copy for you every day and keeps the last 7 days. It's still smart to keep your own copy somewhere safe, like a USB stick or your cloud storage:

1. Click **Backup** on the left.
2. Click **⬇️ Download my data**.

To bring a saved copy back, use **Bring back a saved copy** on the same page. Just in case, the app keeps what was there before as a file called `finance.db.bak`.

---

**You're all set! Enjoy taking control of your finances.** 🎉
