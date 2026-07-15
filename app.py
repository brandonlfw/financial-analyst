import streamlit as st
import pandas as pd
from main import process_statement
import charts
import rbc_analysis

NEW_CATEGORY_SENTINEL = "+ New category..."

st.set_page_config(page_title="RBC Financial Analyzer", layout="wide")
st.title("RBC Financial Statement Analyzer")

# INPUTS
uploaded_file = st.file_uploader("Upload RBC Statement CSV", type="csv")

if uploaded_file is not None and st.session_state.get("last_uploaded_file_id") != uploaded_file.file_id:
    try:
        tx_dates = pd.to_datetime(pd.read_csv(uploaded_file, usecols=["Transaction Date"])["Transaction Date"])
        st.session_state["start_date"] = tx_dates.min().date()
        st.session_state["end_date"] = tx_dates.max().date()
    except (KeyError, ValueError):
        st.warning("Couldn't read transaction dates from this file to auto-fill the date range.")
    finally:
        uploaded_file.seek(0)
        st.session_state["last_uploaded_file_id"] = uploaded_file.file_id

col1, col2 = st.columns(2)
start_date = col1.date_input("Start Date", key="start_date")
end_date = col2.date_input("End Date", key="end_date")

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

    categories = sorted(df["Category"].dropna().unique().tolist())
    pending_categories = st.session_state.setdefault("pending_categories", {})

    edited_rows = st.session_state.get("tx_editor", {}).get("edited_rows", {})
    awaiting_custom_rows = []
    needs_reset = False

    for row_pos, changes in edited_rows.items():
        if "Category" not in changes:
            continue
        row_id = df.index[row_pos]
        new_val = changes["Category"]
        if new_val == NEW_CATEGORY_SENTINEL:
            custom = st.session_state.get(f"custom_cat_{row_id}", "")
            if not custom:
                awaiting_custom_rows.append(row_id)
                continue
            new_val = custom
            needs_reset = True
        if df.at[row_id, "Category"] == new_val:
            pending_categories.pop(row_id, None)
        else:
            pending_categories[row_id] = new_val

    if needs_reset:
        del st.session_state["tx_editor"]
        st.rerun()

    display_df = df.copy()
    for row_id, new_val in pending_categories.items():
        display_df.at[row_id, "Category"] = new_val

    highlighted_rows = set(pending_categories) | set(awaiting_custom_rows)
    styler = display_df.style.apply(
        lambda row: ["background-color: #e6b400" if row.name in highlighted_rows else "" for _ in row],
        axis=1,
    )

    custom_options = sorted(v for v in set(pending_categories.values()) if v not in categories)

    edited = st.data_editor(
        styler,
        use_container_width=True,
        hide_index=True,
        key="tx_editor",
        column_config={
            "Category": st.column_config.SelectboxColumn(
                "Category", options=categories + custom_options + [NEW_CATEGORY_SENTINEL]
            )
        },
        disabled=[c for c in df.columns if c != "Category"],
    )

    for row_id in awaiting_custom_rows:
        st.text_input(f"New category for row {row_id}", key=f"custom_cat_{row_id}")

    _, save_col = st.columns([5, 1])
    with save_col:
        if st.button(
            "Save Changes",
            type="primary",
            use_container_width=True,
            disabled=not pending_categories,
        ):
            for row_id, new_val in pending_categories.items():
                df.at[row_id, "Category"] = new_val
                rbc_analysis.update_transaction_category(row_id, new_val)
            insights["category_breakdown"] = rbc_analysis.categorize_spending(df=df)
            st.session_state["excel_bytes"] = rbc_analysis.build_excel_bytes(df)
            st.session_state["df"] = df
            st.session_state["pending_categories"] = {}
            del st.session_state["tx_editor"]
            st.rerun()

    st.divider()

    chart_col, reserved_col = st.columns(2)
    with chart_col:
        st.header("Pie Chart of Spending")

        fig = charts.build_category_pie_chart(insights["category_breakdown"], st.context.theme.type)
        st.plotly_chart(fig, use_container_width=True)
