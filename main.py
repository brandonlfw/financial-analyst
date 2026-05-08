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
                     "ONLINE TRANSFER TO DEPOSIT ACCOUNT",
                     "ONLINE BANKING TRANSFER"] # set desc2 = ref code

etransfers = ["E-TRANSFER SENT",
             "E-TRANSFER - AUTO-DEPOSIT RECIPIENT"] # set desc2 = recipient or sender, specify TO or FROM in flagging

other = ["STUDENT LOAN CANADA",
         "STUDENT LOAN BC STUDENT AID",
         "INSURANCE CPL:"] # set desc2 = desc1



# Initialize Description 2 as object dtype so string assignments don't fail
statement_df["Description 2"] = None

# Purchases and Refunds - split left half of the '-' as Desc1, the right half for Desc2
p_r_pattern = '|'.join(purchases_and_refunds)
p_r_mask = statement_df["Description 1"].str.contains(p_r_pattern, na=False)
split_result = statement_df.loc[p_r_mask, "Description 1"].str.split(r" - |-", expand=True, n=1, regex=True)
statement_df.loc[p_r_mask, "Description 1"] = split_result[0].values
statement_df.loc[p_r_mask, "Description 2"] = split_result[1].str[5:].values # get rid of 5 digit reference code

# ATM and Transfers
a_t_pattern = '|'.join(atm_and_transfers)
a_t_mask = statement_df["Description 1"].str.contains(a_t_pattern, na=False)
split_result = statement_df.loc[a_t_mask, "Description 1"].str.split(r' - |-', expand=True, regex=True)
statement_df.loc[a_t_mask, "Description 1"] = split_result[0].values
statement_df.loc[a_t_mask, "Description 2"] = split_result[1].values

# E-TRANSFER - AUTODEPOSIT
et_autodeposit = statement_df["Description 1"].str.contains("E-TRANSFER - AUTODEPOSIT")
statement_df.loc[et_autodeposit, "Description 2"] = statement_df.loc[et_autodeposit, "Description 1"].str[25:].str.rsplit(' ', n=1).str[0]
statement_df.loc[et_autodeposit, "Description 1"] = statement_df.loc[et_autodeposit, "Description 1"].str[:24]

# E-TRANSFER SENT
et_sent = statement_df["Description 1"].str.contains("E-TRANSFER SENT")
recipient = statement_df.loc[et_sent, "Description 1"].str[16:].str.rsplit(' ', n=1).str[0]
statement_df.loc[et_sent, "Description 1"] = "E-TRANSFER SENT"
statement_df.loc[et_sent, "Description 2"] = recipient

# other: Description 2 = Description 1
other_mask = statement_df["Description 1"].str.contains("|".join(other), na=False)
statement_df.loc[other_mask, "Description 2"] = statement_df.loc[other_mask, "Description 1"]



rbc_analysis.save_transactions(statement_df)
rbc_analysis.analyze_transactions(statement_df, start_date, end_date)
rbc_analysis.categorize_spending()

# Save transactions (merchant, amt, date) to all_transactions list
all_transactions = filter_transactions.create_filtered_tuples()
filter_transactions.filter(all_transactions)