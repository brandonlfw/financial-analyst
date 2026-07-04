import streamlit as st
import pandas as pd
from main import process_statement

st.set_page_config(page_title="Financial Analyzer", layout="wide")
st.title("Financial Statement Analyzer")

# INPUTS
uploaded_file = st.file_uploader("Upload RBC Statement CSV", type="csv")

col1, col2 = st.columns(2)
start_date = col1.date_input("Start Date")
end_date = col2.date_input("End Date")

provinces = st.text_input("Provinces (comma-separated)", placeholder="ON, BC")
cities = st.text_input("Cities (comma-separated)", placeholder="Toronto, Vancouver")

if st.button("Analyze", type="primary"):
    if uploaded_file is None:
        st.error("Please upload a CSV statement first.")
    elif start_date > end_date:
        st.error("Start date must be before end date.")
    else:
        with st.spinner("Analyzing transactions... this may take a moment for merchant lookups."):
            prov_list = [p.strip() for p in provinces.split(",") if p.strip()]
            city_list = [c.strip() for c in cities.split(",") if c.strip()]

            df, insights, excel_bytes = process_statement(
                uploaded_file, start_date, end_date, prov_list, city_list
            )

            # Store results in session state (cleared automatically when the browser session ends)
            st.session_state["df"] = df
            st.session_state["insights"] = insights
            st.session_state["excel_bytes"] = excel_bytes
            st.session_state["filename"] = uploaded_file.name.rsplit(".", 1)[0]

# RESULTS (only shown after a successful analysis)
if "df" in st.session_state:
    df = st.session_state["df"]
    insights = st.session_state["insights"]
    excel_bytes = st.session_state["excel_bytes"]
    filename = st.session_state["filename"]

    st.divider()

    # Account + totals summary row
    acct_col, debit_col, credit_col = st.columns(3)
    with acct_col:
        st.metric(insights["account_type"], insights["account_number"])
    with debit_col:
        st.metric("Total Debits", f"${insights['total_debits']:,.2f}")
    with credit_col:
        st.metric("Total Credits", f"${insights['total_credits']:,.2f}")

    st.divider()

    # Spending by Category
    st.subheader("Spending by Category")
    breakdown = insights["category_breakdown"]
    breakdown_df = pd.DataFrame(
        sorted(breakdown.items(), key=lambda x: -x[1]),
        columns=["Category", "Total Spent (CAD$)"]
    )
    breakdown_df["Total Spent (CAD$)"] = breakdown_df["Total Spent (CAD$)"].map("${:,.2f}".format)
    st.table(breakdown_df)

    st.divider()

    # All Transactions header + download button on the far right
    header_col, export_col = st.columns([5, 1], vertical_alignment="center")
    with header_col:
        st.subheader("All Transactions")
    with export_col:
        st.download_button(
            label="Download Analyzed Excel",
            data=excel_bytes,
            file_name=f"{filename}_analyzed.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True,
        )

    st.dataframe(df, use_container_width=True, hide_index=True)
