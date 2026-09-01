import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
from datetime import date
import json

# =========================================================
# CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Personal Finance Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

FILE = Path(__file__).parent.parent / "expenses.csv"
BUDGET_FILE = Path(__file__).parent.parent / "budget.json"

COLUMNS = [
    "Date",
    "Type",
    "Category",
    "Description",
    "Amount"
]

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

</style>
""", unsafe_allow_html=True)


# =========================================================
# FILE HANDLING
# =========================================================

def create_file():

    if not FILE.exists() or FILE.stat().st_size == 0:

        pd.DataFrame(
            columns=COLUMNS
        ).to_csv(
            FILE,
            index=False
        )


def load_data():

    create_file()

    try:

        df = pd.read_csv(FILE)

    except Exception:

        return pd.DataFrame(
            columns=COLUMNS
        )

    if df.empty:

        return pd.DataFrame(
            columns=COLUMNS
        )

    for column in COLUMNS:

        if column not in df.columns:

            df[column] = ""

    df = df[COLUMNS]

    df["Date"] = pd.to_datetime(
        df["Date"],
        dayfirst=True,
        errors="coerce"
    )

    df["Amount"] = pd.to_numeric(
        df["Amount"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["Date", "Amount"]
    )

    return df


def save_data(df):
    output = df.copy()

    if not output.empty:
        output["Date"] = pd.to_datetime(
            output["Date"],
            errors="coerce"
        )

        output["Date"] = output["Date"].dt.strftime(
            "%d-%m-%Y"
        )

    output.to_csv(
        FILE,
        index=False
    )

# =========================================================
# TRANSACTION FUNCTIONS
# =========================================================

def add_transaction(
    transaction_date,
    transaction_type,
    category,
    description,
    amount
):

    df = load_data()

    new_transaction = pd.DataFrame({
        "Date": [
            pd.Timestamp(transaction_date)
        ],
        "Type": [
            transaction_type
        ],
        "Category": [
            category
        ],
        "Description": [
            description
        ],
        "Amount": [
            float(amount)
        ]
    })

    df = pd.concat(
        [
            df,
            new_transaction
        ],
        ignore_index=True
    )

    save_data(df)


def delete_transaction(index):

    df = load_data()

    if 0 <= index < len(df):

        df = df.drop(
            index=index
        )

        df = df.reset_index(
            drop=True
        )

        save_data(df)
def update_transaction(
    index,
    transaction_date,
    transaction_type,
    category,
    description,
    amount
):

    df = load_data()

    if 0 <= index < len(df):

        df.loc[index, "Date"] = pd.Timestamp(
            transaction_date
        )

        df.loc[index, "Type"] = transaction_type

        df.loc[index, "Category"] = category

        df.loc[index, "Description"] = description

        df.loc[index, "Amount"] = float(amount)

        save_data(df)
def load_budget():

    if not BUDGET_FILE.exists():
        return 0.0

    try:

        with open(BUDGET_FILE, "r") as file:
            data = json.load(file)

        return float(
            data.get("monthly_budget", 0)
        )

    except Exception:

        return 0.0


def save_budget(amount):

    with open(BUDGET_FILE, "w") as file:

        json.dump(
            {
                "monthly_budget": float(amount)
            },
            file
        )

# =========================================================
# LOAD DATA
# =========================================================

df = load_data()


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
    st.divider()

    st.markdown(
        "### 💰 Monthly Budget"
    )

    current_budget = load_budget()

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

        save_budget(new_budget)

        st.success(
            "Budget saved successfully!"
        )

        st.rerun()
    

    if not df.empty:

        min_date = df["Date"].min().date()
        max_date = df["Date"].max().date()

        date_range = st.date_input(
            "Date range",
            value=(
                min_date,
                max_date
            ),
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
                    df["Date"].dt.date
                    >= start_date
                )
                &
                (
                    df["Date"].dt.date
                    <= end_date
                )
            ].copy()

        else:

            filtered_df = df.copy()

    else:

        filtered_df = df.copy()


# =========================================================
# FINANCIAL CALCULATIONS
# =========================================================

income = filtered_df.loc[
    filtered_df["Type"].str.lower()
    == "income",
    "Amount"
].sum()

expense = filtered_df.loc[
    filtered_df["Type"].str.lower()
    == "expense",
    "Amount"
].sum()

balance = income - expense

if income > 0:

    savings_rate = (
        balance / income
    ) * 100

else:

    savings_rate = 0


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
        'Track your income, spending and savings in one place.'
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
                <div class="metric-title">
                    💰 Total Income
                </div>
                <div class="metric-value">
                    ₹{income:,.2f}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:

        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">
                    💸 Total Expenses
                </div>
                <div class="metric-value">
                    ₹{expense:,.2f}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:

        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">
                    🏦 Balance
                </div>
                <div class="metric-value">
                    ₹{balance:,.2f}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col4:

        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">
                    📊 Savings Rate
                </div>
                <div class="metric-value">
                    {savings_rate:.1f}%
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    # =====================================================
    # MONTHLY BUDGET
    # =====================================================

    st.divider()

    st.markdown(
        '<div class="section-title">'
        '💰 Monthly Budget'
        '</div>',
        unsafe_allow_html=True
    )

    monthly_budget = load_budget()

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

    st.divider()


    # -----------------------------------------------------
    # CHARTS
    # -----------------------------------------------------

    expense_df = filtered_df[
        filtered_df["Type"].str.lower()
        == "expense"
    ].copy()


    if not expense_df.empty:

        col1, col2 = st.columns(2)


        # -------------------------------------------------
        # CATEGORY CHART
        # -------------------------------------------------

        with col1:

            st.markdown(
                '<div class="section-title">'
                '🍕 Spending by Category'
                '</div>',
                unsafe_allow_html=True
            )

            category_data = (
                expense_df
                .groupby("Category")
                ["Amount"]
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


        # -------------------------------------------------
        # INCOME VS EXPENSE
        # -------------------------------------------------

        with col2:

            st.markdown(
                '<div class="section-title">'
                '📊 Income vs Expense'
                '</div>',
                unsafe_allow_html=True
            )

            comparison = pd.DataFrame({
                "Type": [
                    "Income",
                    "Expense"
                ],
                "Amount": [
                    income,
                    expense
                ]
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


        # -------------------------------------------------
        # MONTHLY TREND
        # -------------------------------------------------

        st.markdown(
            '<div class="section-title">'
            '📈 Monthly Spending'
            '</div>',
            unsafe_allow_html=True
        )

        expense_df["Month"] = (
            expense_df["Date"]
            .dt
            .to_period("M")
            .astype(str)
        )

        monthly = (
            expense_df
            .groupby("Month")
            ["Amount"]
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
            .dt
            .strftime("%d-%m-%Y")
        )

        recent["Amount"] = (
            recent["Amount"]
            .map(
                lambda x:
                f"₹{x:,.2f}"
            )
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

    st.title("💳 Transactions")

    st.caption(
        "Manage your income and expenses in one place."
    )

    st.divider()

    # =====================================================
    # ADD TRANSACTION
    # =====================================================

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
            [
                "💸 Expense",
                "💰 Income"
            ],
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

    # =====================================================
    # FIND TRANSACTIONS
    # =====================================================

    st.subheader("🔎 Find Transactions")

    st.caption(
        "Search and filter your financial records."
    )

    current_df = load_data()

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
                [
                    "All",
                    "Expense",
                    "Income"
                ]
            )

        with col3:

            category_filter = st.selectbox(
                "🏷️ Category",
                ["All"]
                +
                sorted(
                    current_df["Category"]
                    .dropna()
                    .unique()
                    .tolist()
                )
            )

        filtered_transactions = current_df.copy()

        # Search

        if search_text.strip():

            search = search_text.lower()

            description_match = (
                filtered_transactions["Description"]
                .str.lower()
                .str.contains(
                    search,
                    na=False
                )
            )

            category_match = (
                filtered_transactions["Category"]
                .str.lower()
                .str.contains(
                    search,
                    na=False
                )
            )

            filtered_transactions = (
                filtered_transactions[
                    description_match
                    |
                    category_match
                ]
            )

        # Type filter

        if type_filter != "All":

            filtered_transactions = (
                filtered_transactions[
                    filtered_transactions["Type"]
                    == type_filter
                ]
            )

        # Category filter

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

        # =================================================
        # TRANSACTION TABLE
        # =================================================

        st.subheader("🧾 Your Transactions")

        if not filtered_transactions.empty:

            display_df = (
                filtered_transactions.copy()
            )

            display_df["Date"] = (
                display_df["Date"]
                .dt
                .strftime("%d-%m-%Y")
            )

            display_df["Amount"] = (
                display_df["Amount"]
                .map(
                    lambda x:
                    f"₹{x:,.2f}"
                )
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

        # =================================================
        # EDIT TRANSACTION
        # =================================================

        st.subheader("✏️ Edit Transaction")

        if not filtered_transactions.empty:

            edit_options = []

            for index, row in (
                filtered_transactions.iterrows()
            ):

                label = (
                    f"{row['Date'].strftime('%d-%m-%Y')} | "
                    f"{row['Type']} | "
                    f"{row['Category']} | "
                    f"{row['Description']} | "
                    f"₹{row['Amount']:,.2f}"
                )

                edit_options.append(
                    (index, label)
                )

            selected_edit = st.selectbox(
                "Select transaction to edit",
                edit_options,
                format_func=lambda x: x[1],
                key="edit_transaction"
            )

            edit_index = selected_edit[0]

            edit_row = current_df.loc[
                edit_index
            ]

            col1, col2 = st.columns(2)

            with col1:

                edit_date = st.date_input(
                    "📅 Date",
                    value=edit_row["Date"].date(),
                    key="edit_date"
                )

                edit_type = st.selectbox(
                    "💳 Type",
                    [
                        "Expense",
                        "Income"
                    ],
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
                    value=edit_row["Description"],
                    key="edit_description"
                )

                edit_amount = st.number_input(
                    "💵 Amount (₹)",
                    min_value=0.0,
                    value=float(
                        edit_row["Amount"]
                    ),
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
                        edit_index,
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

        # =================================================
        # DELETE TRANSACTION
        # =================================================

        st.subheader("🗑️ Delete Transaction")

        if not filtered_transactions.empty:

            delete_options = []

            for index, row in (
                filtered_transactions.iterrows()
            ):

                label = (
                    f"{row['Date'].strftime('%d-%m-%Y')} | "
                    f"{row['Category']} | "
                    f"{row['Description']} | "
                    f"₹{row['Amount']:,.2f}"
                )

                delete_options.append(
                    (index, label)
                )

            selected_delete = st.selectbox(
                "Select transaction to delete",
                delete_options,
                format_func=lambda x: x[1],
                key="delete_transaction"
            )

            delete_index = selected_delete[0]

            if st.button(
                "🗑️ Delete Selected Transaction",
                use_container_width=True
            ):

                delete_transaction(
                    delete_index
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
        filtered_df["Type"].str.lower()
        == "expense"
    ].copy()


    if not expense_df.empty:

        # -----------------------------------------------
        # CATEGORY SUMMARY
        # -----------------------------------------------

        st.subheader(
            "Category-wise Spending"
        )

        category_summary = (
            expense_df
            .groupby("Category")
            ["Amount"]
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


        # -----------------------------------------------
        # TOP CATEGORY
        # -----------------------------------------------

        top_category = (
            category_summary
            .iloc[0]
        )

        st.info(
            f"Your highest spending category is "
            f"**{top_category['Category']}** "
            f"with "
            f"**₹{top_category['Amount']:,.2f}**."
        )


        # -----------------------------------------------
        # AVERAGE DAILY SPENDING
        # -----------------------------------------------

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
