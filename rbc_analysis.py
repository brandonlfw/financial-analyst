import pandas as pd
# import plot_graphs
import sqlite3
import re
import io


def categorize_merchants(merchant_name, provinces, cities):
    """
    This function is passed a merchant name from save_transactions() and classifies the merchant's category based off the name and user-passed province(s)/city(s) of purchase.
    It queries CA_MERCHANTS.db for direct or similar matches to existing merchants in the ODBus database to find its NAIC code, then converts it to the corresponding category and returns it as a string.
    """

    conn = sqlite3.connect('CA_MERCHANTS.db')
    cursor = conn.cursor()

    # Convert provinces and cities into list for SQL IN (...)
    provinces_list = [province.strip() for province in provinces.split(', ') if province.strip()] if provinces else []
    city_list = [city.strip() for city in cities.split(', ') if city.strip()] if cities else []

    filler_words = ["THE", "OF", "LTD", "STORE", "WHOLESALE"]

    if not isinstance(merchant_name, str): # if merchant is not a string, skip to next merchant
        return "Other" # return 'Other' for NAIC category

    # turn merchant all uppercase, replace non-letters with space, get rid of whitespace
    clean_name = re.sub(r"[^A-Z\s]", '', merchant_name.upper()).strip()

    # insert each word from clean_name as an element of split_name list; do not add word if only 1 character (ex. '-')
    split_name = [word for word in clean_name.split() if word and word not in filler_words and len(word) > 1]

    if not split_name: # if split_name is empty, skip to next merchant
        return "Other"
    

    # build parameterized SQL per-merchant; try stricter AND-match first, then OR-match. =========================================

    # base WHERE clauses (province + city IN ...)
    where_clause = []
    params = []
    if provinces_list:
        prov_placeholders = ", ".join(["?"] * len(provinces_list)) # create a string of '?, ?...' based on # of provinces (3 provinces -> "?, ?, ?")
        where_clause.append(f"prov_terr IN ({prov_placeholders})")
        params.extend(provinces_list)
    if city_list:
        cities_placeholders = ", ".join(["?"] * len(city_list)) 
        where_clause.append(f"city IN ({cities_placeholders})")
        params.extend(city_list)

    # word match clause template (checks business_name OR alt_business_name)
    pair_clause = "(UPPER(business_name) LIKE ? OR UPPER(alt_business_name) LIKE ?)"

    # Direct match =========================================
    all_clause = " AND ".join([pair_clause for _ in split_name])
    all_query = f"""
        SELECT merchant_category
        FROM (
            SELECT
                CASE
                    WHEN derived_NAICS = '22' THEN 'Utilities'
                    WHEN derived_NAICS BETWEEN '44' AND '45' THEN 'Retail and Groceries'
                    WHEN derived_NAICS = '52' THEN 'Finance and Insurance'
                    WHEN derived_NAICS IN ('54', '81', '91') THEN 'Professional Services'
                    WHEN derived_NAICS = '62' THEN 'Healthcare'
                    WHEN derived_NAICS = '71' THEN 'Entertainment and Recreation'
                    WHEN derived_NAICS = '72' THEN 'Accommodation and Food Services'
                    ELSE 'Other'
                END AS merchant_category,
                NAIC_count
            FROM (
                SELECT
                    derived_NAICS,
                    COUNT(*) AS NAIC_count
                FROM (
                    SELECT
                        UPPER(business_name),
                        UPPER(alt_business_name),
                        derived_NAICS,
                        city,
                        prov_terr
                    FROM
                        MERCHANT_INFO
                    WHERE
                        {(' AND '.join(where_clause) + ' AND ') if where_clause else ''}({all_clause})
                    LIMIT 20
                ) sub
                GROUP BY
                    derived_NAICS
                ORDER BY
                    NAIC_count DESC
            ) sub2
        ) sub3
        WHERE merchant_category != 'Other'
        ORDER BY NAIC_count DESC
        LIMIT 1
    """

    # Any word match =========================================
    any_clause = " OR ".join([pair_clause for _ in split_name])
    any_query = f"""
        SELECT merchant_category
        FROM (
            SELECT
                CASE
                    WHEN derived_NAICS = '22' THEN 'Utilities'
                    WHEN derived_NAICS BETWEEN '44' AND '45' THEN 'Retail and Groceries'
                    WHEN derived_NAICS = '52' THEN 'Finance and Insurance'
                    WHEN derived_NAICS IN ('54', '81', '91') THEN 'Professional Services'
                    WHEN derived_NAICS = '62' THEN 'Healthcare'
                    WHEN derived_NAICS = '71' THEN 'Entertainment and Recreation'
                    WHEN derived_NAICS = '72' THEN 'Accommodation and Food Services'
                    ELSE 'Other'
                END AS merchant_category,
                NAIC_count
            FROM (
                SELECT
                    derived_NAICS,
                    COUNT(*) AS NAIC_count
                FROM (
                    SELECT
                        UPPER(business_name),
                        UPPER(alt_business_name),
                        derived_NAICS,
                        city,
                        prov_terr
                    FROM
                        MERCHANT_INFO
                    WHERE
                        {(' AND '.join(where_clause) + ' AND ') if where_clause else ''}({any_clause})
                    LIMIT 20
                ) sub
                GROUP BY
                    derived_NAICS
                ORDER BY
                    NAIC_count DESC
            ) sub2
        ) sub3
        WHERE merchant_category != 'Other'
        ORDER BY NAIC_count DESC
        LIMIT 1
    """

    # add # wildcard to front and back of each word in split_word twice (b/c business_name and alt_business_name are back to back in the WHERE)
    full_params = list(params) + [f"%{word}%" for word in split_name for __ in (0, 1)]

    # Attempt A: all words present (AND between pair_clauses)
    cursor.execute(all_query, full_params)
    row = cursor.fetchone()

    if row is not None:
        # return the NAIC category
        return row[0]
    else:
        # Attempt B: any word present (OR between pair_clauses) if no rows found
        cursor.execute(any_query, full_params)
        row = cursor.fetchone()
        if row is not None:
            # return the NAIC category
            return row[0]
    
    conn.close()

    # if no NAIC category found, return 'Other'
    return "Other"



def categorize_transactions(statement_df, provinces="", cities=""):
    """
    Assigns the Category column for every row in statement_df based on Description 1
    patterns (withdrawal/deposit/purchase-refund) and, for purchases/refunds, a NAIC
    merchant lookup via categorize_merchants(). Mutates statement_df in place. This
    should only be run once per statement (at initial analysis) since re-running it
    would overwrite any categories a user has manually corrected afterward.
    """
    withdrawals = [
        "E-TRANSFER SENT",
        "E-TRANSFER REQUEST FULFILLED",
        "ATM WITHDRAWAL",
        "ATM TRANSFER TO DEPOSIT ACCT",
        "ONLINE TRANSFER TO DEPOSIT ACCOUNT"
    ]

    deposits = [
        "E-TRANSFER - AUTODEPOSIT RECIPIENT",
        "E-TRANSFER RECEIVED",
        "E-TRANSFER - REQUEST MONEY",
        "DEPOSIT",
        "PAYROLL DEPOSIT",
        "ATM DEPOSIT",
        "ONLINE BANKING TRANSFER",
        "MOBILE CHEQUE DEPOSIT",
        "INSURANCE CPL:"
    ]

    purchases_and_refunds = ["CONTACTLESS INTERAC PURCHASE",
                         "CONTACTLESS INTERAC REFUND",
                         "VISA DEBIT PURCHASE",
                         "VISA DEBIT REFUND",
                         "VISA DEBIT REVERSAL",
                         "INTERAC PURCHASE",
                         "INTERAC TRANSIT"
                         ]

    non_merchant_categories = withdrawals + deposits + purchases_and_refunds

    statement_df["Transaction Date"] = statement_df["Transaction Date"].dt.date

    withdrawal_pattern = '|'.join(withdrawals)
    deposit_pattern = '|'.join(deposits)
    pr_pattern = '|'.join(purchases_and_refunds)
    non_merchant_pattern = '|'.join(non_merchant_categories)

    withdrawal_mask = statement_df["Description 1"].str.contains(withdrawal_pattern)
    deposit_mask = statement_df["Description 1"].str.contains(deposit_pattern)
    pr_mask = statement_df["Description 1"].str.contains(pr_pattern)
    non_merchant_mask = ~statement_df["Description 1"].str.contains(non_merchant_pattern, na=False, case=False)

    # if a withdrawal or deposit is in Desc1, set that as the Category (withdrawals applied last to take priority over deposit substring matches)
    if deposit_mask.any():
        statement_df.loc[deposit_mask, "Category"] = "Deposit"

    if withdrawal_mask.any():
        statement_df.loc[withdrawal_mask, "Category"] = "Withdrawal"

    # use categorize_merchants() to find NAIC code for merchants whose Desc1 not in other_categories
    if pr_mask.any():
        statement_df.loc[pr_mask, "Category"] = statement_df.loc[pr_mask].apply(
            lambda row: categorize_merchants(row["Description 2"], provinces, cities), axis=1
        )

    # if Desc1 is not a category or a purchase/refund, set its Category to "Other"
    if non_merchant_mask.any():
        statement_df.loc[non_merchant_mask, "Description 2"] = statement_df.loc[non_merchant_mask, "Description 1"]
        statement_df.loc[non_merchant_mask, "Category"] = "Other"


def build_excel_bytes(statement_df):
    """
    Serializes the already-categorized statement_df into the analyzed .xlsx layout
    (an "All Transactions" sheet plus one sheet per Category with a TOTAL row) and
    returns the bytes. Pure serialization of in-memory data - safe/cheap to call
    again after a manual category edit.
    """
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        statement_df.to_excel(writer, sheet_name="All Transactions", index=False)
        for category, group_df in statement_df.groupby("Category"):
            sheet_name = re.sub(r'[\\/*?:\[\]]', '', str(category))[:31] # strip forbidden characters (\ / * ? : [ ]) for sheet names and truncate name to 31 characters max
            total_row = {col: None for col in group_df.columns}
            total_row["Description 2"] = "TOTAL"
            total_row["CAD$"] = group_df["CAD$"].sum()
            group_df = pd.concat([group_df, pd.DataFrame([total_row])], ignore_index=True) # add total row to bottom of the group_df
            group_df.to_excel(writer, sheet_name=sheet_name, index=False)
    return buffer.getvalue()


def save_transactions_to_db(statement_df, db_path="transactions.db"):
    conn = sqlite3.connect(db_path)
    statement_df.to_sql('transactions', conn, if_exists='replace', index=True, index_label='id')
    conn.close()


def update_transaction_category(row_id, new_category):
    """
    Applies a single manually-edited Category value to transactions.db without
    touching any other row (unlike save_transactions_to_db's full-table replace).
    row_id is the statement_df's pandas index value, matching the 'id' column
    written by save_transactions_to_db's index_label='id'.
    """
    conn = sqlite3.connect("transactions.db")
    conn.execute('UPDATE transactions SET Category = ? WHERE id = ?', (new_category, int(row_id)))
    conn.commit()
    conn.close()


def save_transactions(statement_df, statement_fname, provinces="", cities="", return_bytes=False):
    categorize_transactions(statement_df, provinces, cities)
    excel_bytes = build_excel_bytes(statement_df)

    if return_bytes:
        save_transactions_to_db(statement_df)
        return excel_bytes

    with open(f"{statement_fname}_analyzed.xlsx", "wb") as f:
        f.write(excel_bytes)
    print(f"\nSuccessfully wrote dataframe to {statement_fname}_analyzed.xlsx")

    save_transactions_to_db(statement_df)
    print("Successfully saved transactions to transactions.db\n")



def analyze_transactions(statement_df, start_date, end_date, interactive=True):
    """
    Summarize debits and credits. In interactive mode, prompts for fraud flagging thresholds
    and prints results. In non-interactive mode, returns a dict with totals (no DB access).
    """
    if not interactive:
        total_debits = abs(statement_df[statement_df["CAD$"] < 0]["CAD$"].sum())
        total_credits = statement_df[statement_df["CAD$"] > 0]["CAD$"].sum()
        return {"total_debits": total_debits, "total_credits": total_credits}

    total_debits = 0
    total_credits = 0

    conn = sqlite3.connect('transactions.db')
    cursor = conn.cursor()

    enable_flagging = input("\nEnable debit transaction flagging to catch fraud? Flag transactions that are ABOVE or BELOW a certain amount (Y/N): ")
    if enable_flagging == 'Y':
        print("\nType any NON-NUMERICAL character to skip a limit.")
        try:
            upper_limit = float("-" + input("Flag transactions above $"))
        except ValueError:
            upper_limit = statement_df['CAD$'].min() - 0.01 # choose the min value (most negative) - $0.01 as no debits exceed that, so no flagging
        try:
            lower_limit = float("-" + input("Flag transactions below $"))
        except ValueError:
            lower_limit = 0
    elif enable_flagging == 'N':
        upper_limit = statement_df['CAD$'].min() - 0.01
        lower_limit = 0

    total_debits = cursor.execute('SELECT SUM("CAD$") FROM transactions WHERE "CAD$" < 0').fetchone()[0]
    total_credits = cursor.execute('SELECT SUM("CAD$") FROM transactions WHERE "CAD$" > 0').fetchone()[0]
    print(f"The total debits from {start_date.date()} to {end_date.date()} is ${-total_debits}")
    print(f"The total credits from {start_date.date()} to {end_date.date()} is ${total_credits}")

    flagged_above_query = '''
        SELECT id, "Transaction Date", "Description 1", "Description 2", "CAD$"
        FROM transactions
        WHERE "CAD$" < ?
    ''' # < because want amounts GREATER than a negative number (debit)

    cursor.execute(flagged_above_query, (upper_limit,))
    print(f"\nThese transactions were flagged for being at or above ${-upper_limit}:\n")

    for row in cursor:
        if row[2] == "E-TRANSFER SENT":
            print(f"CSV Index {row[0] + 2} on {row[1]}: {row[2]} to {row[3]} for ${-row[4]}")
        elif row[2] == "E-TRANSFER - AUTO-DEPOSIT":
            print(f"CSV Index {row[0] + 2} on {row[1]}: {row[2]} recieved from {row[3]} for ${-row[4]}")
        else:
            print(f"CSV Index {row[0] + 2} on {row[1]}: {row[2]} purchased from {row[3]} for ${-row[4]}")

    flagged_below_query = '''
        SELECT id, "Transaction Date", "Description 1", "Description 2", "CAD$"
        FROM transactions
        WHERE "CAD$" > ? AND "CAD$" < 0
    ''' # > because want amounts LESS than a negative number (ex. lower_limit=-5, amt=$-3 => -3 > -5, so -3 is flagged)

    cursor.execute(flagged_below_query, (lower_limit,))
    print(f"\nThese transactions were flagged for being at or below ${-lower_limit} but above $0:\n")
    for row in cursor:
        if row[2] == "E-TRANSFER SENT":
            print(f"CSV Index {row[0] + 2} on {row[1]}: {row[2]} to {row[3]} for ${-row[4]}") # + 2 in on index because CSV has row 1 = column titles
        elif row[2] == "E-TRANSFER - AUTO-DEPOSIT":
            print(f"CSV Index {row[0] + 2} on {row[1]}: {row[2]} recieved from {row[3]} for ${-row[4]}")
        else:
            print(f"CSV Index {row[0] + 2} on {row[1]}: {row[2]} purchased from {row[3]} for ${-row[4]}")

    conn.close()



def categorize_spending(df=None):
    if df is not None:
        debit_mask = df["CAD$"] < 0
        grouped = df[debit_mask].groupby("Category")["CAD$"].sum()
        return {cat: abs(val) for cat, val in grouped.items()}

    conn = sqlite3.connect('transactions.db')
    cursor = conn.cursor()

    cursor.execute('SELECT Category, SUM("CAD$") FROM transactions WHERE "CAD$" < 0 GROUP BY Category')
    categories = cursor.fetchall()

    categorized_spending = {rows[0]: "$" + str(-rows[1]) for rows in categories}
    print("\nThis is a categorized breakdown of your DEBIT transactions:\n")
    print(categorized_spending)

    conn.close()