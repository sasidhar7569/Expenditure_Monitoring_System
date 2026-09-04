import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import plotly.express as px
from pathlib import Path
from datetime import date

# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Personal Finance Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

# Step 7: SQLite database
DB_FILE = BASE_DIR / "finance.db"

# Existing CSV is kept only for one-time migration/back-up
LEGACY_CSV = BASE_DIR.parent / "expenses.csv"

CATEGORIES = [
    "Food",
    "Travel",
    "Bills",
    "Shopping",
    "Education",
    "Entertainment",
    "Health",
    "Salary",
    "Other"
]

# =========================================================
# DATABASE
# =========================================================

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            transaction_date TEXT NOT NULL,
            transaction_type TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            monthly_budget REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def signup_user(username, password):
    username = username.strip()

    if not username or not password:
        return False, "Please fill in all fields."

    conn = get_connection()

    try:
        conn.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, hash_password(password))
        )
        conn.commit()
        return True, "Account created successfully. Please login."

    except sqlite3.IntegrityError:
        return False, "Username already exists."

    finally:
        conn.close()


def login_user(username, password):
    conn = get_connection()

    user = conn.execute(
        """
        SELECT id, username
        FROM users
        WHERE username = ? AND password = ?
        """,
        (username.strip(), hash_password(password))
    ).fetchone()

    conn.close()

    if user:
        return dict(user)

    return None


# =========================================================
# ONE-TIME LEGACY CSV MIGRATION
# =========================================================

def migrate_legacy_csv(user_id):
    """
    Import the old expenses.csv only when the SQLite database
    has no transactions at all. This prevents new users from
    receiving another user's legacy transactions.
    """

    conn = get_connection()

    total_count = conn.execute(
        "SELECT COUNT(*) AS count FROM transactions"
    ).fetchone()["count"]

    if total_count > 0:
        conn.close()
        return

    if not LEGACY_CSV.exists() or LEGACY_CSV.stat().st_size == 0:
        conn.close()
        return

    try:
        old_df = pd.read_csv(LEGACY_CSV)

        required = [
            "Date",
            "Type",
            "Category",
            "Description",
            "Amount"
        ]

        if not all(column in old_df.columns for column in required):
            conn.close()
            return

        old_df["Date"] = pd.to_datetime(
            old_df["Date"],
            dayfirst=True,
            errors="coerce"
        )

        old_df["Amount"] = pd.to_numeric(
            old_df["Amount"],
            errors="coerce"
        )

        old_df = old_df.dropna(
            subset=["Date", "Amount"]
        )

        for _, row in old_df.iterrows():
            transaction_type = str(row["Type"]).strip().title()

            if transaction_type not in ["Income", "Expense"]:
                continue

            conn.execute(
                """
                INSERT INTO transactions
                (
                    user_id,
                    transaction_date,
                    transaction_type,
                    category,
                    description,
                    amount
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    row["Date"].strftime("%Y-%m-%d"),
                    transaction_type,
                    str(row["Category"]).strip(),
                    str(row["Description"]).strip(),
                    float(row["Amount"])
                )
            )

        conn.commit()

    except Exception:
        conn.rollback()

    finally:
        conn.close()


# =========================================================
# TRANSACTION DATA
# =========================================================

def load_data(user_id):
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT
            id AS ID,
            transaction_date AS Date,
            transaction_type AS Type,
            category AS Category,
            description AS Description,
            amount AS Amount
        FROM transactions
        WHERE user_id = ?
        ORDER BY transaction_date DESC, id DESC
        """,
        (user_id,)
    ).fetchall()

    conn.close()

    columns = [
        "ID",
        "Date",
        "Type",
        "Category",
        "Description",
        "Amount"
    ]

    if not rows:
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame([dict(row) for row in rows])

    df["Date"] = pd.to_datetime(
        df["Date"],
        errors="coerce"
    )

    df["Amount"] = pd.to_numeric(
        df["Amount"],
        errors="coerce"
    )

    return df.dropna(
        subset=["Date", "Amount"]
    )


def add_transaction(
    user_id,
    transaction_date,
    transaction_type,
    category,
    description,
    amount
):
    conn = get_connection()

    conn.execute(
        """
        INSERT INTO transactions
        (
            user_id,
            transaction_date,
            transaction_type,
            category,
            description,
            amount
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            pd.Timestamp(transaction_date).strftime("%Y-%m-%d"),
            transaction_type,
            category,
            description.strip(),
            float(amount)
        )
    )

    conn.commit()
    conn.close()


def update_transaction(
    user_id,
    transaction_id,
    transaction_date,
    transaction_type,
    category,
    description,
    amount
):
    conn = get_connection()

    conn.execute(
        """
        UPDATE transactions
        SET
            transaction_date = ?,
            transaction_type = ?,
            category = ?,
            description = ?,
            amount = ?
        WHERE id = ? AND user_id = ?
        """,
        (
            pd.Timestamp(transaction_date).strftime("%Y-%m-%d"),
            transaction_type,
            category,
            description.strip(),
            float(amount),
            int(transaction_id),
            user_id
        )
    )

    conn.commit()
    conn.close()


def delete_transaction(user_id, transaction_id):
    conn = get_connection()

    conn.execute(
        """
        DELETE FROM transactions
        WHERE id = ? AND user_id = ?
        """,
        (int(transaction_id), user_id)
    )

    conn.commit()
    conn.close()


# =========================================================
# BUDGET
# =========================================================

def load_budget(user_id):
    conn = get_connection()

    row = conn.execute(
        """
        SELECT monthly_budget
        FROM budgets
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()

    conn.close()

    if row is None:
        return 0.0

    return float(row["monthly_budget"])


def save_budget(user_id, amount):
    conn = get_connection()

    conn.execute(
        """
        INSERT INTO budgets (user_id, monthly_budget)
        VALUES (?, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET monthly_budget = excluded.monthly_budget
        """,
        (user_id, float(amount))
    )

    conn.commit()
    conn.close()


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

init_database()

# =========================================================
# SESSION STATE
# =========================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "username" not in st.session_state:
    st.session_state.username = ""


# =========================================================
# CUSTOM CSS
# =========================================================

st.markdown("""
<style>

.main {
    background-color: #f7f8fa;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}

.dashboard-title {
    font-size: 38px;
    font-weight: 700;
    margin-bottom: 5px;
}

.dashboard-subtitle {
    font-size: 17px;
    color: #6b7280;
    margin-bottom: 25px;
}

.metric-card {
    background-color: white;
    padding: 20px;
    border-radius: 14px;
    border: 1px solid #e5e7eb;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.metric-title {
    font-size: 14px;
    color: #4b5563 !important;
}

.metric-value {
    font-size: 27px;
    font-weight: 700;
    margin-top: 5px;
    color: #111827 !important;
}

.section-title {
    font-size: 23px;
    font-weight: 650;
    margin-top: 20px;
    margin-bottom: 10px;
}

.login-box {
    max-width: 650px;
    margin: 40px auto;
    padding: 35px;
    border-radius: 18px;
    background: white;
    border: 1px solid #e5e7eb;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# LOGIN / SIGNUP PAGE
# =========================================================

def authentication_page():

    st.markdown(
        """
        <div class="login-box">
            <h1 style="text-align:center;">
                💰 Personal Finance
            </h1>
            <p style="text-align:center; color:#6b7280;">
                Securely manage your income, expenses and budget
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:

        login_tab, signup_tab = st.tabs(
            ["🔐 Login", "📝 Create Account"]
        )

        with login_tab:

            st.subheader("Welcome Back")

            username = st.text_input(
                "Username",
                key="login_username"
            )

            password = st.text_input(
                "Password",
                type="password",
                key="login_password"
            )

            if st.button(
                "🔓 Login",
                use_container_width=True
            ):

                if not username.strip() or not password:

                    st.warning(
                        "Please enter username and password."
                    )

                else:

                    user = login_user(
                        username,
                        password
                    )

                    if user:

                        st.session_state.logged_in = True
                        st.session_state.user_id = user["id"]
                        st.session_state.username = user["username"]

                        # Import existing CSV data for the first user
                        migrate_legacy_csv(
                            user["id"]
                        )

                        st.rerun()

                    else:

                        st.error(
                            "Invalid username or password."
                        )

        with signup_tab:

            st.subheader("Create Your Account")

            new_username = st.text_input(
                "Choose Username",
                key="signup_username"
            )

            new_password = st.text_input(
                "Choose Password",
                type="password",
                key="signup_password"
            )

            confirm_password = st.text_input(
                "Confirm Password",
                type="password",
                key="confirm_password"
            )

            if st.button(
                "✨ Create Account",
                use_container_width=True
            ):

                if (
                    not new_username.strip()
                    or not new_password
                    or not confirm_password
                ):

                    st.warning(
                        "Please fill in all fields."
                    )

                elif len(new_password) < 6:

                    st.warning(
                        "Password must contain at least 6 characters."
                    )

                elif new_password != confirm_password:

                    st.error(
                        "Passwords do not match."
                    )

                else:

                    success, message = signup_user(
                        new_username,
                        new_password
                    )

                    if success:
                        st.success(message)
                    else:
                        st.error(message)


if not st.session_state.logged_in:
    authentication_page()
    st.stop()


# =========================================================
# LOAD CURRENT USER DATA
# =========================================================

user_id = st.session_state.user_id
username = st.session_state.username

df = load_data(user_id)


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown(
        "# 💰 Personal Finance"
    )

    st.caption(
        "Expenditure Monitoring System"
    )

    st.divider()

    st.success(
        f"👤 {username}"
    )

    if st.button(
        "🚪 Logout",
        use_container_width=True
    ):

        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.username = ""

        st.rerun()

    st.divider()

    page = st.radio(
        "Navigation",
        [
            "🏠 Dashboard",
            "💳 Transactions",
            "📊 Analytics"
        ]
    )

    st.divider()

    st.markdown(
        "### 🔎 Filters"
    )

    if not df.empty:

        min_date = df["Date"].min().date()
        max_date = df["Date"].max().date()

        date_range = st.date_input(
            "Date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )

        if (
            isinstance(date_range, tuple)
            and len(date_range) == 2
        ):

            start_date = date_range[0]
            end_date = date_range[1]

            filtered_df = df[
                (
                    df["Date"].dt.date >= start_date
                )
                &
                (
                    df["Date"].dt.date <= end_date
                )
            ].copy()

        else:

            filtered_df = df.copy()

    else:

        filtered_df = df.copy()

    st.divider()

    st.markdown(
        "### 💰 Monthly Budget"
    )

    current_budget = load_budget(user_id)

    new_budget = st.number_input(
        "Set Monthly Budget (₹)",
        min_value=0.0,
        value=float(current_budget),
        step=500.0,
        format="%.2f"
    )

    if st.button(
        "💾 Save Budget",
        use_container_width=True
    ):

        save_budget(
            user_id,
            new_budget
        )

        st.success(
            "Budget saved successfully!"
        )

        st.rerun()


# =========================================================
# FINANCIAL CALCULATIONS
# =========================================================

if filtered_df.empty:

    income = 0.0
    expense = 0.0

else:

    income = filtered_df.loc[
        filtered_df["Type"].str.lower() == "income",
        "Amount"
    ].sum()

    expense = filtered_df.loc[
        filtered_df["Type"].str.lower() == "expense",
        "Amount"
    ].sum()

balance = income - expense

if income > 0:
    savings_rate = (balance / income) * 100
else:
    savings_rate = 0.0


# =========================================================
# DASHBOARD PAGE
# =========================================================

if page == "🏠 Dashboard":

    st.markdown(
        '<div class="dashboard-title">'
        '💰 Personal Finance Dashboard'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="dashboard-subtitle">'
        f'Welcome back, {username}. Track your income, spending and savings in one place.'
        '</div>',
        unsafe_allow_html=True
    )

    # -----------------------------------------------------
    # METRIC CARDS
    # -----------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">💰 Total Income</div>
                <div class="metric-value">₹{income:,.2f}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">💸 Total Expenses</div>
                <div class="metric-value">₹{expense:,.2f}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">🏦 Balance</div>
                <div class="metric-value">₹{balance:,.2f}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">📊 Savings Rate</div>
                <div class="metric-value">{savings_rate:.1f}%</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # -----------------------------------------------------
    # MONTHLY BUDGET
    # -----------------------------------------------------

    st.divider()

    st.markdown(
        '<div class="section-title">'
        '💰 Monthly Budget'
        '</div>',
        unsafe_allow_html=True
    )

    monthly_budget = load_budget(user_id)

    if monthly_budget > 0:

        budget_remaining = monthly_budget - expense

        budget_used = (
            expense / monthly_budget
        ) * 100

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Monthly Budget",
                f"₹{monthly_budget:,.2f}"
            )

        with col2:
            st.metric(
                "Spent",
                f"₹{expense:,.2f}"
            )

        with col3:
            st.metric(
                "Remaining",
                f"₹{budget_remaining:,.2f}"
            )

        progress = min(
            max(budget_used / 100, 0),
            1
        )

        st.progress(progress)

        st.caption(
            f"{budget_used:.1f}% of your monthly budget used"
        )

        if budget_used >= 100:
            st.error(
                "🔴 You have exceeded your monthly budget!"
            )
        elif budget_used >= 80:
            st.warning(
                "🟡 You have used more than 80% of your monthly budget."
            )
        else:
            st.success(
                "🟢 You are within your monthly budget."
            )

    else:

        st.info(
            "Set a monthly budget from the sidebar."
        )

    # -----------------------------------------------------
    # CHARTS
    # -----------------------------------------------------

    st.divider()

    expense_df = filtered_df[
        filtered_df["Type"].str.lower() == "expense"
    ].copy()

    if not expense_df.empty:

        col1, col2 = st.columns(2)

        with col1:

            st.markdown(
                '<div class="section-title">'
                '🍕 Spending by Category'
                '</div>',
                unsafe_allow_html=True
            )

            category_data = (
                expense_df
                .groupby("Category")["Amount"]
                .sum()
                .reset_index()
            )

            fig_pie = px.pie(
                category_data,
                names="Category",
                values="Amount",
                hole=0.45
            )

            fig_pie.update_layout(
                margin=dict(
                    t=20,
                    b=20,
                    l=20,
                    r=20
                )
            )

            st.plotly_chart(
                fig_pie,
                use_container_width=True
            )

        with col2:

            st.markdown(
                '<div class="section-title">'
                '📊 Income vs Expense'
                '</div>',
                unsafe_allow_html=True
            )

            comparison = pd.DataFrame({
                "Type": ["Income", "Expense"],
                "Amount": [income, expense]
            })

            fig_bar = px.bar(
                comparison,
                x="Type",
                y="Amount",
                text="Amount"
            )

            fig_bar.update_traces(
                texttemplate="₹%{text:,.0f}",
                textposition="outside"
            )

            fig_bar.update_layout(
                yaxis_title="Amount (₹)",
                xaxis_title="",
                margin=dict(
                    t=20,
                    b=20,
                    l=20,
                    r=20
                )
            )

            st.plotly_chart(
                fig_bar,
                use_container_width=True
            )

        st.markdown(
            '<div class="section-title">'
            '📈 Monthly Spending'
            '</div>',
            unsafe_allow_html=True
        )

        expense_df["Month"] = (
            expense_df["Date"]
            .dt.to_period("M")
            .astype(str)
        )

        monthly = (
            expense_df
            .groupby("Month")["Amount"]
            .sum()
            .reset_index()
        )

        fig_line = px.line(
            monthly,
            x="Month",
            y="Amount",
            markers=True
        )

        fig_line.update_layout(
            xaxis_title="Month",
            yaxis_title="Expenses (₹)"
        )

        st.plotly_chart(
            fig_line,
            use_container_width=True
        )

    else:

        st.info(
            "No expense data available yet."
        )

    # -----------------------------------------------------
    # RECENT TRANSACTIONS
    # -----------------------------------------------------

    st.markdown(
        '<div class="section-title">'
        '🧾 Recent Transactions'
        '</div>',
        unsafe_allow_html=True
    )

    if not filtered_df.empty:

        recent = (
            filtered_df
            .sort_values(
                "Date",
                ascending=False
            )
            .head(5)
            .copy()
        )

        recent["Date"] = (
            recent["Date"]
            .dt.strftime("%d-%m-%Y")
        )

        recent["Amount"] = recent["Amount"].map(
            lambda x: f"₹{x:,.2f}"
        )

        st.dataframe(
            recent[
                [
                    "Date",
                    "Type",
                    "Category",
                    "Description",
                    "Amount"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "No transactions available."
        )


# =========================================================
# TRANSACTIONS PAGE
# =========================================================

elif page == "💳 Transactions":

    st.markdown(
        '<div class="dashboard-title">'
        '💳 Transactions'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="dashboard-subtitle">'
        'Manage your income and expenses in one place.'
        '</div>',
        unsafe_allow_html=True
    )

    # -----------------------------------------------------
    # ADD TRANSACTION
    # -----------------------------------------------------

    st.subheader("✨ Add New Transaction")

    st.caption(
        "Record your income or spending and keep your finances organized."
    )

    with st.form(
        "transaction_form",
        clear_on_submit=True
    ):

        transaction_type = st.radio(
            "Transaction Type",
            ["💸 Expense", "💰 Income"],
            horizontal=True
        )

        if transaction_type == "💸 Expense":
            transaction_type = "Expense"
        else:
            transaction_type = "Income"

        col1, col2 = st.columns(2)

        with col1:

            transaction_date = st.date_input(
                "📅 Date",
                value=date.today()
            )

        with col2:

            category = st.selectbox(
                "🏷️ Category",
                CATEGORIES
            )

        description = st.text_input(
            "📝 Description",
            placeholder="What did you spend on?"
        )

        amount = st.number_input(
            "💵 Amount (₹)",
            min_value=0.0,
            step=50.0,
            format="%.2f"
        )

        submitted = st.form_submit_button(
            "＋ Add Transaction",
            use_container_width=True
        )

        if submitted:

            if not description.strip():

                st.error(
                    "Please enter a description."
                )

            elif amount <= 0:

                st.error(
                    "Amount must be greater than zero."
                )

            else:

                add_transaction(
                    user_id,
                    transaction_date,
                    transaction_type,
                    category,
                    description,
                    amount
                )

                st.success(
                    "Transaction added successfully!"
                )

                st.rerun()

    st.divider()

    # -----------------------------------------------------
    # FIND TRANSACTIONS
    # -----------------------------------------------------

    st.subheader("🔎 Find Transactions")

    st.caption(
        "Search and filter your financial records."
    )

    current_df = load_data(user_id)

    if not current_df.empty:

        col1, col2, col3 = st.columns(3)

        with col1:

            search_text = st.text_input(
                "🔍 Search",
                placeholder="Search description or category..."
            )

        with col2:

            type_filter = st.selectbox(
                "💳 Type",
                ["All", "Expense", "Income"]
            )

        with col3:

            category_filter = st.selectbox(
                "🏷️ Category",
                ["All"]
                + sorted(
                    current_df["Category"]
                    .dropna()
                    .unique()
                    .tolist()
                )
            )

        filtered_transactions = current_df.copy()

        if search_text.strip():

            search = search_text.lower()

            description_match = (
                filtered_transactions["Description"]
                .astype(str)
                .str.lower()
                .str.contains(
                    search,
                    na=False
                )
            )

            category_match = (
                filtered_transactions["Category"]
                .astype(str)
                .str.lower()
                .str.contains(
                    search,
                    na=False
                )
            )

            filtered_transactions = (
                filtered_transactions[
                    description_match | category_match
                ]
            )

        if type_filter != "All":

            filtered_transactions = (
                filtered_transactions[
                    filtered_transactions["Type"] == type_filter
                ]
            )

        if category_filter != "All":

            filtered_transactions = (
                filtered_transactions[
                    filtered_transactions["Category"]
                    == category_filter
                ]
            )

        st.write(
            f"Showing {len(filtered_transactions)} transaction(s)"
        )

        # -------------------------------------------------
        # TRANSACTION TABLE
        # -------------------------------------------------

        st.subheader("🧾 Your Transactions")

        if not filtered_transactions.empty:

            display_df = filtered_transactions.copy()

            display_df["Date"] = (
                display_df["Date"]
                .dt.strftime("%d-%m-%Y")
            )

            display_df["Amount"] = (
                display_df["Amount"]
                .map(lambda x: f"₹{x:,.2f}")
            )

            st.dataframe(
                display_df[
                    [
                        "Date",
                        "Type",
                        "Category",
                        "Description",
                        "Amount"
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info(
                "No transactions match your filters."
            )

        st.divider()

        # -------------------------------------------------
        # EDIT TRANSACTION
        # -------------------------------------------------

        st.subheader("✏️ Edit Transaction")

        if not filtered_transactions.empty:

            edit_options = []

            for _, row in filtered_transactions.iterrows():

                label = (
                    f"{row['Date'].strftime('%d-%m-%Y')} | "
                    f"{row['Type']} | "
                    f"{row['Category']} | "
                    f"{row['Description']} | "
                    f"₹{row['Amount']:,.2f}"
                )

                edit_options.append(
                    (int(row["ID"]), label)
                )

            selected_edit = st.selectbox(
                "Select transaction to edit",
                edit_options,
                format_func=lambda x: x[1],
                key="edit_transaction"
            )

            edit_id = selected_edit[0]

            edit_row = current_df[
                current_df["ID"] == edit_id
            ].iloc[0]

            col1, col2 = st.columns(2)

            with col1:

                edit_date = st.date_input(
                    "📅 Date",
                    value=edit_row["Date"].date(),
                    key="edit_date"
                )

                edit_type = st.selectbox(
                    "💳 Type",
                    ["Expense", "Income"],
                    index=(
                        0
                        if edit_row["Type"] == "Expense"
                        else 1
                    ),
                    key="edit_type"
                )

                if edit_row["Category"] in CATEGORIES:
                    category_index = CATEGORIES.index(
                        edit_row["Category"]
                    )
                else:
                    category_index = 0

                edit_category = st.selectbox(
                    "🏷️ Category",
                    CATEGORIES,
                    index=category_index,
                    key="edit_category"
                )

            with col2:

                edit_description = st.text_input(
                    "📝 Description",
                    value=str(edit_row["Description"]),
                    key="edit_description"
                )

                edit_amount = st.number_input(
                    "💵 Amount (₹)",
                    min_value=0.0,
                    value=float(edit_row["Amount"]),
                    step=50.0,
                    key="edit_amount"
                )

            if st.button(
                "💾 Save Changes",
                use_container_width=True
            ):

                if not edit_description.strip():

                    st.error(
                        "Description cannot be empty."
                    )

                elif edit_amount <= 0:

                    st.error(
                        "Amount must be greater than zero."
                    )

                else:

                    update_transaction(
                        user_id,
                        edit_id,
                        edit_date,
                        edit_type,
                        edit_category,
                        edit_description,
                        edit_amount
                    )

                    st.success(
                        "Transaction updated successfully!"
                    )

                    st.rerun()

        st.divider()

        # -------------------------------------------------
        # DELETE TRANSACTION
        # -------------------------------------------------

        st.subheader("🗑️ Delete Transaction")

        if not filtered_transactions.empty:

            delete_options = []

            for _, row in filtered_transactions.iterrows():

                label = (
                    f"{row['Date'].strftime('%d-%m-%Y')} | "
                    f"{row['Category']} | "
                    f"{row['Description']} | "
                    f"₹{row['Amount']:,.2f}"
                )

                delete_options.append(
                    (int(row["ID"]), label)
                )

            selected_delete = st.selectbox(
                "Select transaction to delete",
                delete_options,
                format_func=lambda x: x[1],
                key="delete_transaction"
            )

            delete_id = selected_delete[0]

            if st.button(
                "🗑️ Delete Selected Transaction",
                use_container_width=True
            ):

                delete_transaction(
                    user_id,
                    delete_id
                )

                st.success(
                    "Transaction deleted successfully!"
                )

                st.rerun()

    else:

        st.info(
            "No transactions available. Add your first transaction above."
        )


# =========================================================
# ANALYTICS PAGE
# =========================================================

elif page == "📊 Analytics":

    st.markdown(
        '<div class="dashboard-title">'
        '📊 Analytics'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="dashboard-subtitle">'
        'Understand where your money is going.'
        '</div>',
        unsafe_allow_html=True
    )

    expense_df = filtered_df[
        filtered_df["Type"].str.lower() == "expense"
    ].copy()

    if not expense_df.empty:

        st.subheader("Category-wise Spending")

        category_summary = (
            expense_df
            .groupby("Category")["Amount"]
            .sum()
            .reset_index()
            .sort_values(
                "Amount",
                ascending=False
            )
        )

        fig_category = px.bar(
            category_summary,
            x="Category",
            y="Amount",
            text="Amount"
        )

        fig_category.update_traces(
            texttemplate="₹%{text:,.0f}",
            textposition="outside"
        )

        st.plotly_chart(
            fig_category,
            use_container_width=True
        )

        top_category = category_summary.iloc[0]

        st.info(
            f"Your highest spending category is "
            f"**{top_category['Category']}** "
            f"with "
            f"**₹{top_category['Amount']:,.2f}**."
        )

        days = (
            expense_df["Date"]
            .dt.date
            .nunique()
        )

        if days > 0:
            average_daily = (
                expense_df["Amount"].sum()
                / days
            )
        else:
            average_daily = 0

        col1, col2 = st.columns(2)

        with col1:

            st.metric(
                "Average Daily Spending",
                f"₹{average_daily:,.2f}"
            )

        with col2:

            st.metric(
                "Number of Expenses",
                len(expense_df)
            )

    else:

        st.info(
            "Add expenses to see analytics."
        )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "Automated Personal Expenditure Monitoring System "
    "| Interactive Personal Finance Dashboard"
)
