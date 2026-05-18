import pandas as pd
import rbc_analysis
import filter_transactions
from datetime import datetime


statement_file = input("Enter the name of the statement: ")
statement_df = pd.read_csv(statement_file)

print("Enter a custom statement range or press 'Enter' to use the end ranges.")

# ----------------------- START AND END DATE CONFIGURATION ---------------------------
try: # Validate start date input
    start_date = input("Start date (YYYY-MM-DD): ")
    datetime.strptime(start_date, '%Y-%m-%d')
    print(f"Start date {start_date} is valid.")
except: # Default to earliest day in statement if invalid entry
    earliest_date = statement_df.iloc[0]["Transaction Date"]
    print(f"Invalid end date {start_date} detected; using earliest date {earliest_date} from statement.")
    start_date = earliest_date

try: # Validate end date input
    end_date = input("End date (YYYY-MM-DD): ")
    datetime.strptime(end_date, '%Y-%m-%d')
    print(f"End date {end_date} is valid.")
except: # Default to last day in statement if invalid entry
    last_date = statement_df.iloc[-1]["Transaction Date"]
    print(f"Invalid end date {end_date} detected; using last date {last_date} on statement.")
    end_date = last_date


start_date = pd.to_datetime(start_date)
end_date = pd.to_datetime(end_date)

statement_df["Transaction Date"] = pd.to_datetime(statement_df["Transaction Date"]) # convert 'Transaction Date' column in csv to datetime format
statement_df = statement_df[(statement_df["Transaction Date"] >= start_date) & (statement_df["Transaction Date"] <= end_date)] # create new df with rows between start and end date



# ------------------------ CLEAN "Description 1" by separating transaction type and setting business description to "Description 2" ------------------------------

purchases_and_refunds = ["CONTACTLESS INTERAC PURCHASE",
                         "CONTACTLESS INTERAC REFUND",
                         "VISA DEBIT PURCHASE",
                         "VISA DEBIT REFUND",
                         "VISA DEBIT REVERSAL",
                         "INTERAC PURCHASE",
                         "INTERAC TRANSIT"] # set desc2 = merchant


atm_and_transfers = ["ATM DEPOSIT",
                     "ATM WITHDRAWAL",
                     "ATM TRANSFER TO DEPOSIT ACCT",
                     "ONLINE TRANSFER TO DEPOSIT ACCOUNT",
                     "ONLINE BANKING TRANSFER"] # set desc2 = ref code

''' E-TRANSFERS: set desc2 = recipient or sender, specify TO or FROM in flagging
    "E-TRANSFER SENT",
    "E-TRANSFER - AUTODEPOSIT RECIPIENT",
    "E-TRANSFER RECEIVED",
    "E-TRANSFER - REQUEST MONEY",
    "E-TRANSFER REQUEST FULFILLED"
'''


# Initialize Description 2 as object dtype so string assignments don't fail
statement_df["Description 2"] = None

# Purchases and Refunds - split left half of the '-' as Desc1, the right half for Desc2
p_r_pattern = '|'.join(purchases_and_refunds)
p_r_mask = statement_df["Description 1"].str.contains(p_r_pattern, na=False)
if p_r_mask.any():
    split_result = statement_df.loc[p_r_mask, "Description 1"].str.split(r" - |-", expand=True, n=1, regex=True)
    statement_df.loc[p_r_mask, "Description 1"] = split_result[0].values
    statement_df.loc[p_r_mask, "Description 2"] = split_result[1].str[5:].values # get rid of 5 digit reference code

# ATM and Transfers
a_t_pattern = '|'.join(atm_and_transfers)
a_t_mask = statement_df["Description 1"].str.contains(a_t_pattern, na=False)
if a_t_mask.any():
    split_result = statement_df.loc[a_t_mask, "Description 1"].str.split(r' - |-', expand=True, regex=True)
    statement_df.loc[a_t_mask, "Description 1"] = split_result[0].values
    statement_df.loc[a_t_mask, "Description 2"] = split_result[1].values


# --------------------- SPECIAL CASES ----------------------
# E-TRANSFER - AUTODEPOSIT
et_ad_mask = statement_df["Description 1"].str.contains("E-TRANSFER - AUTODEPOSIT")
if et_ad_mask.any():
    sender = statement_df.loc[et_ad_mask, "Description 1"].str[25:].str.rsplit(' ', n=1, expand=True) # [24:] gives sender + code, rsplit strips the code
    statement_df.loc[et_ad_mask, "Description 1"] = "E-TRANSFER - AUTODEPOSIT"
    statement_df.loc[et_ad_mask, "Description 2"] = sender[0]

# E-TRANSFER - REQUEST MONEY
et_rqm_mask = statement_df["Description 1"].str.contains("E-TRANSFER - REQUEST MONEY")
if et_rqm_mask.any():
    sender = statement_df.loc[et_rqm_mask, "Description 1"].str[27:].str.rsplit(' ', n=1).str[0]
    statement_df.loc[et_rqm_mask, "Description 1"] = "E-TRANSFER - REQUEST MONEY"
    statement_df.loc[et_rqm_mask, "Description 2"] = sender

# E-TRANSFER REQUEST FULFILLED
et_rq_ff_mask = statement_df["Description 1"].str.contains("E-TRANSFER REQUEST FULFILLED")
if et_rq_ff_mask.any():
    recipient = statement_df.loc[et_rq_ff_mask, "Description 1"].str[30:].str.rsplit(' ', n=1).str[0]
    statement_df.loc[et_rq_ff_mask, "Description 1"] = "E-TRANSFER REQUEST FULFILLED"
    statement_df.loc[et_rq_ff_mask, "Description 2"] = recipient

# E-TRANSFER SENT and E-TRANSFER RECEIVED
et_mask = statement_df["Description 1"].str.contains("E-TRANSFER SENT|E-TRANSFER RECEIVED", na=False)
if et_mask.any():
    type_and_person = statement_df.loc[et_mask, "Description 1"].str.split(' ', n=2, expand=True) # split into ['E-TRANSFER', either 'SENT' or 'RECEIVED', 'PERSON']
    statement_df.loc[et_mask, "Description 1"] = type_and_person[0] + " " + type_and_person[1] # "E-TRANSFER SENT" or "E-TRANSFER RECEIVED"
    statement_df.loc[et_mask, "Description 2"] = type_and_person[2].str.rsplit(' ', n=1).str[0]

# PAYROLL DEPOSIT
payroll_mask = statement_df["Description 1"].str.contains("PAYROLL DEPOSIT")
if payroll_mask.any():
    company = statement_df.loc[payroll_mask, "Description 1"].str[16:]
    statement_df.loc[payroll_mask, "Description 1"] = "PAYROLL DEPOSIT"
    statement_df.loc[payroll_mask, "Description 2"] = company

# BANK INTERNAL TRANSACTION (BR TO BR)
br_mask = statement_df["Description 1"].str.contains("BR TO BR")
if br_mask.any():
    ref_code = statement_df.loc[br_mask, "Description 1"].str[11:]
    statement_df.loc[br_mask, "Description 1"] = "IN-BRANCH TRANSACTION"
    statement_df.loc[br_mask, "Description 2"] = ref_code

# MOBILE CHEQUE DEPOSIT
cheque_mask = statement_df["Description 1"].str.contains("MOBILE CHEQUE DEPOSIT")
if cheque_mask.any():
    ref_code = statement_df.loc[cheque_mask, "Description 1"].str.rsplit(' ', n=1).str[1]
    statement_df.loc[cheque_mask, "Description 1"] = "MOBILE CHEQUE DEPOSIT"
    statement_df.loc[cheque_mask, "Description 2"] = "CHEQUE #" + ref_code

# INSURANCE
insurance_mask = statement_df["Description 1"].str.contains("INSURANCE")
if insurance_mask.any():
    statement_df.loc[insurance_mask, "Description 2"] = "INSURANCE"

# DEPOSITS
deposit_mask = statement_df["Description 1"] == "DEPOSIT"
if deposit_mask.any():
    statement_df.loc[deposit_mask, "Description 2"] = "DEPOSIT"

# MISC PAYMENT
misc_mask = statement_df["Description 1"].str.contains("MISC PAYMENT")
if misc_mask.any():
    statement_df.loc[misc_mask, "Description 2"] = statement_df.loc[misc_mask, "Description 1"].str[13:]
    statement_df.loc[misc_mask, "Description 1"] = "MISC PAYMENT"




rbc_analysis.save_transactions(statement_df, statement_file)
rbc_analysis.analyze_transactions(statement_df, start_date, end_date)
rbc_analysis.categorize_spending()

# Save transactions (merchant, amt, date) to all_transactions list
all_transactions = filter_transactions.create_filtered_tuples()
filter_transactions.filter(all_transactions)