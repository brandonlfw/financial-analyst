import pandas as pd
# import plot_graphs
import sqlite3
import re


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
        return "N/A" # return N/A for NAIC category

    # turn merchant all uppercase, replace non-letters with space, get rid of whitespace
    clean_name = re.sub(r"[^A-Z\s]", '', merchant_name.upper()).strip()

    # insert each word from clean_name as an element of split_name list; do not add word if only 1 character (ex. '-')
    split_name = [word for word in clean_name.split() if word and word not in filler_words and len(word) > 1]

    if not split_name: # if split_name is empty, skip to next merchant
        return "N/A"
    

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
                    WHEN derived_NAICS BETWEEN '44' AND '45' THEN 'Retail Trade'
                    WHEN derived_NAICS = '52' THEN 'Finance and Insurance'
                    WHEN derived_NAICS IN ('54', '81', '91') THEN 'Professional Services'
                    WHEN derived_NAICS = '62' THEN 'Healthcare'
                    WHEN derived_NAICS = '71' THEN 'Entertainment and Recreation'
                    WHEN derived_NAICS = '72' THEN 'Accommodation and Food Services'
                    ELSE 'N/A'
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
        WHERE merchant_category != 'N/A'
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
                    WHEN derived_NAICS BETWEEN '44' AND '45' THEN 'Retail Trade'
                    WHEN derived_NAICS = '52' THEN 'Finance and Insurance'
                    WHEN derived_NAICS IN ('54', '81', '91') THEN 'Professional Services'
                    WHEN derived_NAICS = '62' THEN 'Healthcare'
                    WHEN derived_NAICS = '71' THEN 'Entertainment and Recreation'
                    WHEN derived_NAICS = '72' THEN 'Accommodation and Food Services'
                    ELSE 'N/A'
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
        WHERE merchant_category != 'N/A'
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
        # print(f"{merchant_name} NAIC code is {row[0]}")
        return row[0]
    else:
        # Attempt B: any word present (OR between pair_clauses) if no rows found
        cursor.execute(any_query, full_params)
        row = cursor.fetchone()
        if row is not None:
            # return the NAIC category
            # print(f"{merchant_name} NAIC code is {row[0]}")
            return row[0]
    
    conn.close()

    # if no NAIC category found, return N/A
    return "N/A"



def save_transactions(statement_df, statement_fname):
    categories = [
        'Online Banking Transfer',
        'Contactless Interac Refund',
        'ATM Transaction',
        'E-Transfer',
        'Insurance',
        'Payroll Deposit',
        'Online Transfer to Deposit Account',
        'Misc Payment',
        'Deposit',
        'Cheque'
    ]

    purchases_and_refunds = ["CONTACTLESS INTERAC PURCHASE",
                         "CONTACTLESS INTERAC REFUND",
                         "VISA DEBIT PURCHASE",
                         "VISA DEBIT REFUND",
                         "VISA DEBIT REVERSAL",
                         "INTERAC PURCHASE",
                         "INTERAC TRANSIT"
                         ]
    
    non_merchant_categories = categories + purchases_and_refunds

    provinces = input("\nProvince (separate with ', ' if multiple): ").strip()
    cities = input("City (separate with ', ' if multiple): ").strip()

    statement_df["Transaction Date"] = statement_df["Transaction Date"].dt.date

    cat_pattern = '|'.join(re.escape(cat) for cat in categories) # re.escape to allow special chars
    pr_pattern = '|'.join(purchases_and_refunds)
    non_merchant_pattern = '|'.join(non_merchant_categories)

    cat_mask = statement_df["Description 1"].str.contains(cat_pattern, na=False, case=False)
    pr_mask = statement_df["Description 1"].str.contains(pr_pattern)
    non_merchant_mask = ~statement_df["Description 1"].str.contains(non_merchant_pattern, na=False, case=False)

    # if one of the categories are in Desc1, find the matching category name and set as Category
    if cat_mask.any():
        def find_category(desc):
            for cat in categories:
                if re.search(re.escape(cat), desc, re.IGNORECASE):
                    return cat
            return None
        statement_df.loc[cat_mask, "Category"] = statement_df.loc[cat_mask, "Description 1"].apply(find_category)

    # use categorize_merchants() to find NAIC code for merchants whose Desc1 not in other_categories
    if pr_mask.any():
        statement_df.loc[pr_mask, "Category"] = statement_df.loc[pr_mask].apply(
            lambda row: categorize_merchants(row["Description 2"], provinces, cities), axis=1
        )

    # if Desc1 is not a category or a purchase/refund, set its Category to "Other"
    if non_merchant_mask.any():
        statement_df.loc[non_merchant_mask, "Description 2"] = statement_df.loc[non_merchant_mask, "Description 1"]
        statement_df.loc[non_merchant_mask, "Category"] = "Other"



    # Write categorized transactions to excel
    with pd.ExcelWriter(f"{statement_fname}_analyzed.xlsx", engine="openpyxl") as writer:
        statement_df.to_excel(writer, sheet_name="All Transactions", index=False)

        for category, group_df in statement_df.groupby("Category"):
            sheet_name = re.sub(r'[\\/*?:\[\]]', '', str(category))[:31] # strip forbidden characters (\ / * ? : [ ]) for sheet names and truncate name to 31 characters max
            
            total_row = {col: None for col in group_df.columns}
            total_row["Description 2"] = "TOTAL"
            total_row["CAD$"] = group_df["CAD$"].sum()

            group_df = pd.concat([group_df, pd.DataFrame([total_row])], ignore_index=True) # add total row to bottom of the group_df

            group_df.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"\nSuccessfully wrote dataframe to {statement_fname}_analyzed.xlsx")


    # Save categorized transactions to db
    conn = sqlite3.connect('transactions.db')
    statement_df.to_sql('transactions', conn, if_exists='replace', index=True, index_label='id')
    print("Successfully saved transactions to transactions.db\n")


    conn.close()
    


def analyze_transactions(statement_df, start_date, end_date):
    """
    Iterate each transaction in statement_df and sum and print all debits, credits, and create list of all transactions $50 or above.
    Plot transactions graph with stars on flagged purchases >= $50 using plot_graphs() from plot_graphs module.
    """
    total_debits = 0
    total_credits = 0
 
    # Connect to transactions.db
    conn = sqlite3.connect('transactions.db')
    cursor = conn.cursor()


    # Debit transaction flagging user inputs
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
        
    
    # Summary
    total_debits = cursor.execute('SELECT SUM("CAD$") FROM transactions WHERE "CAD$" < 0').fetchone()[0]
    total_credits = cursor.execute('SELECT SUM("CAD$") FROM transactions WHERE "CAD$" > 0').fetchone()[0]
    print(f"The total debits from {start_date.date()} to {end_date.date()} is ${-total_debits}")
    print(f"The total credits from {start_date.date()} to {end_date.date()} is ${total_credits}")


    # Flag transactions queries
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



    # PLOT GRAPHS ------------------------------------------------------------------
    # plot_graphs.plot_graphs(statement_df, start_date, end_date, debits_by_date, credits_by_date) # disable until fixed with new flagging system


    conn.close()



def categorize_spending():
    conn = sqlite3.connect('transactions.db')
    cursor = conn.cursor()

    # Find distinct categories that have DEBIT transactions
    cursor.execute('SELECT Category, SUM("CAD$") FROM transactions WHERE "CAD$" < 0 GROUP BY Category')
    categories = cursor.fetchall()
    
    categorized_spending = {rows[0]: "$" + str(-rows[1]) for rows in categories}
    print("\nThis is a categorized breakdown of your DEBIT transactions:\n")
    print(categorized_spending)


    conn.close()