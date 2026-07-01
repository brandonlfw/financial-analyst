import pandas as pd
import rbc_analysis
import filter_transactions
from datetime import datetime


def _clean_statement(statement_df):
    purchases_and_refunds = [
        "CONTACTLESS INTERAC PURCHASE",
        "CONTACTLESS INTERAC REFUND",
        "VISA DEBIT PURCHASE",
        "VISA DEBIT REFUND",
        "VISA DEBIT REVERSAL",
        "INTERAC PURCHASE",
        "INTERAC TRANSIT"
    ]

    atm_and_transfers = [
        "ATM DEPOSIT",
        "ATM WITHDRAWAL",
        "ATM TRANSFER TO DEPOSIT ACCT",
        "ONLINE TRANSFER TO DEPOSIT ACCOUNT",
        "ONLINE BANKING TRANSFER"
    ]

    statement_df["Description 2"] = None

    p_r_pattern = '|'.join(purchases_and_refunds)
    p_r_mask = statement_df["Description 1"].str.contains(p_r_pattern, na=False)
    if p_r_mask.any():
        split_result = statement_df.loc[p_r_mask, "Description 1"].str.split(r" - |-", expand=True, n=1, regex=True)
        statement_df.loc[p_r_mask, "Description 1"] = split_result[0].values
        statement_df.loc[p_r_mask, "Description 2"] = split_result[1].str[5:].values

    a_t_pattern = '|'.join(atm_and_transfers)
    a_t_mask = statement_df["Description 1"].str.contains(a_t_pattern, na=False)
    if a_t_mask.any():
        split_result = statement_df.loc[a_t_mask, "Description 1"].str.split(r' - |-', expand=True, regex=True)
        statement_df.loc[a_t_mask, "Description 1"] = split_result[0].values
        statement_df.loc[a_t_mask, "Description 2"] = split_result[1].values

    et_ad_mask = statement_df["Description 1"].str.contains("E-TRANSFER - AUTODEPOSIT")
    if et_ad_mask.any():
        sender = statement_df.loc[et_ad_mask, "Description 1"].str[25:].str.rsplit(' ', n=1, expand=True)
        statement_df.loc[et_ad_mask, "Description 1"] = "E-TRANSFER - AUTODEPOSIT"
        statement_df.loc[et_ad_mask, "Description 2"] = sender[0]

    et_rqm_mask = statement_df["Description 1"].str.contains("E-TRANSFER - REQUEST MONEY")
    if et_rqm_mask.any():
        sender = statement_df.loc[et_rqm_mask, "Description 1"].str[27:].str.rsplit(' ', n=1).str[0]
        statement_df.loc[et_rqm_mask, "Description 1"] = "E-TRANSFER - REQUEST MONEY"
        statement_df.loc[et_rqm_mask, "Description 2"] = sender

    et_rq_ff_mask = statement_df["Description 1"].str.contains("E-TRANSFER REQUEST FULFILLED")
    if et_rq_ff_mask.any():
        recipient = statement_df.loc[et_rq_ff_mask, "Description 1"].str[30:].str.rsplit(' ', n=1).str[0]
        statement_df.loc[et_rq_ff_mask, "Description 1"] = "E-TRANSFER REQUEST FULFILLED"
        statement_df.loc[et_rq_ff_mask, "Description 2"] = recipient

    et_mask = statement_df["Description 1"].str.contains("E-TRANSFER SENT|E-TRANSFER RECEIVED", na=False)
    if et_mask.any():
        type_and_person = statement_df.loc[et_mask, "Description 1"].str.split(' ', n=2, expand=True)
        statement_df.loc[et_mask, "Description 1"] = type_and_person[0] + " " + type_and_person[1]
        statement_df.loc[et_mask, "Description 2"] = type_and_person[2].str.rsplit(' ', n=1).str[0]

    payroll_mask = statement_df["Description 1"].str.contains("PAYROLL DEPOSIT")
    if payroll_mask.any():
        company = statement_df.loc[payroll_mask, "Description 1"].str[16:]
        statement_df.loc[payroll_mask, "Description 1"] = "PAYROLL DEPOSIT"
        statement_df.loc[payroll_mask, "Description 2"] = company

    br_mask = statement_df["Description 1"].str.contains("BR TO BR")
    if br_mask.any():
        ref_code = statement_df.loc[br_mask, "Description 1"].str[11:]
        statement_df.loc[br_mask, "Description 1"] = "IN-BRANCH TRANSACTION"
        statement_df.loc[br_mask, "Description 2"] = ref_code

    cheque_mask = statement_df["Description 1"].str.contains("MOBILE CHEQUE DEPOSIT")
    if cheque_mask.any():
        ref_code = statement_df.loc[cheque_mask, "Description 1"].str.rsplit(' ', n=1).str[1]
        statement_df.loc[cheque_mask, "Description 1"] = "MOBILE CHEQUE DEPOSIT"
        statement_df.loc[cheque_mask, "Description 2"] = "CHEQUE #" + ref_code

    insurance_mask = statement_df["Description 1"].str.contains("INSURANCE")
    if insurance_mask.any():
        statement_df.loc[insurance_mask, "Description 2"] = "INSURANCE"

    deposit_mask = statement_df["Description 1"] == "DEPOSIT"
    if deposit_mask.any():
        statement_df.loc[deposit_mask, "Description 2"] = "DEPOSIT"

    misc_mask = statement_df["Description 1"].str.contains("MISC PAYMENT")
    if misc_mask.any():
        statement_df.loc[misc_mask, "Description 2"] = statement_df.loc[misc_mask, "Description 1"].str[13:]
        statement_df.loc[misc_mask, "Description 1"] = "MISC PAYMENT"


def process_statement(csv_file, start_date, end_date, provinces, cities):
    """
    Dashboard entry point. No input() calls, no disk writes, no DB writes.
    Returns (df, insights, excel_bytes).
    """
    statement_df = pd.read_csv(csv_file)
    statement_df = statement_df.drop(columns=["Cheque Number", "USD$"], errors="ignore")

    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)

    statement_df["Transaction Date"] = pd.to_datetime(statement_df["Transaction Date"])
    statement_df = statement_df[
        (statement_df["Transaction Date"] >= start_dt) &
        (statement_df["Transaction Date"] <= end_dt)
    ].copy()

    _clean_statement(statement_df)

    prov_str = ", ".join(p.strip() for p in provinces if p.strip())
    city_str = ", ".join(c.strip() for c in cities if c.strip())

    excel_bytes = rbc_analysis.save_transactions(statement_df, "output", prov_str, city_str, return_bytes=True)

    insights = rbc_analysis.analyze_transactions(statement_df, start_dt, end_dt, interactive=False)
    insights["category_breakdown"] = rbc_analysis.categorize_spending(df=statement_df)

    return statement_df, insights, excel_bytes


if __name__ == "__main__":
    statement_file = input("Enter the name of the statement: ")
    statement_name = statement_file.rsplit('.', 1)[0]
    statement_df = pd.read_csv(statement_file)
    statement_df = statement_df.drop(columns=["Cheque Number", "USD$"], errors="ignore")

    print("Enter a custom statement range or press 'Enter' to use the end ranges.")

    try:
        start_date = input("Start date (YYYY-MM-DD): ")
        datetime.strptime(start_date, '%Y-%m-%d')
        print(f"Start date {start_date} is valid.")
    except:
        earliest_date = statement_df.iloc[0]["Transaction Date"]
        print(f"Invalid end date {start_date} detected; using earliest date {earliest_date} from statement.")
        start_date = earliest_date

    try:
        end_date = input("End date (YYYY-MM-DD): ")
        datetime.strptime(end_date, '%Y-%m-%d')
        print(f"End date {end_date} is valid.")
    except:
        last_date = statement_df.iloc[-1]["Transaction Date"]
        print(f"Invalid end date {end_date} detected; using last date {last_date} on statement.")
        end_date = last_date

    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    statement_df["Transaction Date"] = pd.to_datetime(statement_df["Transaction Date"])
    statement_df = statement_df[
        (statement_df["Transaction Date"] >= start_date) &
        (statement_df["Transaction Date"] <= end_date)
    ]

    _clean_statement(statement_df)

    provinces = input("\nProvince (separate with ', ' if multiple): ").strip()
    cities = input("City (separate with ', ' if multiple): ").strip()

    rbc_analysis.save_transactions(statement_df, statement_name, provinces, cities)
    rbc_analysis.analyze_transactions(statement_df, start_date, end_date)
    rbc_analysis.categorize_spending()

    all_transactions = filter_transactions.create_filtered_tuples()
    filter_transactions.filter(all_transactions)
