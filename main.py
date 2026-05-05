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

# Split "Description 1" by the " - " for all transaction types EXCEPT ones listed in edge cases below
statement_df[["Description 1", "Description 2"]] = statement_df["Description 1"].str.split(" - ", expand=True, n=1) # split "Description 1" column at the " - ": 1st half remains in "Description 1", 2nd half goes in "Description 2"
statement_df["Description 2"] = statement_df["Description 2"].str[5:]

# Edge cases
for index, row in statement_df.iterrows():
    if "CONTACTLESS INTERAC REFUND" in row["Description 1"]:
        issuer = row["Description 1"][32:]
        statement_df.loc[index, "Description 1"] = "CONTACTLESS INTERAC REFUND"
        statement_df.loc[index, "Description 2"] = issuer

    elif "E-TRANSFER SENT" in row["Description 1"]: # No '-' separator. Strip the 16-char prefix "E-TRANSFER SENT ", then drop the last 7 chars (space + 6 digit ref code)
        recipient_and_code = row["Description 1"][16:]
        recipient = recipient_and_code.rsplit(' ', 1)[0] # split recipient_and_code into [recipient, code] and take recipient only
        statement_df.loc[index, "Description 1"] = "E-TRANSFER SENT"
        statement_df.loc[index, "Description 2"] = recipient

    # E-TRANSFER - AUTO-DEPOSIT RECIPIENT



rbc_analysis.save_transactions(statement_df)
rbc_analysis.analyze_transactions(statement_df, start_date, end_date)

# Save transactions (merchant, amt, date) to all_transactions list
all_transactions = filter_transactions.create_filtered_tuples()
filter_transactions.filter(all_transactions)