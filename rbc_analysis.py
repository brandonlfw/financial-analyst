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

    filler_words = ["THE", "OF", "LTD", "STORE"]

    if not isinstance(merchant_name, str): # if merchant is not a string, skip to next merchant
        return "N/A" # return N/A for NAIC category

    # turn merchant all uppercase, replace non-letters with space, get rid of whitespace
    clean_name = re.sub(r"[^A-Z\s'-]", ' ', merchant_name.upper()).strip()

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
        SELECT
            CASE
                WHEN derived_NAICS = '11' THEN 'Agriculture, forestry, fishing and hunting'
                WHEN derived_NAICS = '21' THEN 'Mining, quarrying, and oil and gas extraction'
                WHEN derived_NAICS = '22' THEN 'Utilities'
                WHEN derived_NAICS = '23' THEN 'Construction'

                WHEN derived_NAICS BETWEEN '31' AND '33' THEN 'Manufacturing'
                WHEN derived_NAICS = '41' THEN 'Wholesale trade'
                WHEN derived_NAICS BETWEEN '44' AND '45' THEN 'Retail trade'
                WHEN derived_NAICS BETWEEN '48' AND '49' THEN 'Transportation and warehousing'

                WHEN derived_NAICS = '51' THEN 'Information and cultural industries'
                WHEN derived_NAICS = '52' THEN 'Finance and insurance'
                WHEN derived_NAICS = '53' THEN 'Real estate and rental and leasing'
                WHEN derived_NAICS = '54' THEN 'Professional, scientific and technical services'
                WHEN derived_NAICS = '55' THEN 'Management of companies and enterprises'
                WHEN derived_NAICS = '56' THEN 'Administrative and support, waste management and remediation services'

                WHEN derived_NAICS = '61' THEN 'Educational services'
                WHEN derived_NAICS = '62' THEN 'Health care and social assistance'
                WHEN derived_NAICS = '71' THEN 'Arts, entertainment and recreation'
                WHEN derived_NAICS = '72' THEN 'Accommodation and food services'
                WHEN derived_NAICS = '81' THEN 'Other services (except public administration)'
                WHEN derived_NAICS = '91' THEN 'Public administration'

                ELSE 'N/A'
            END AS merchant_category
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
            LIMIT 1
        ) sub2
    """

    # Any word match =========================================
    any_clause = " OR ".join([pair_clause for _ in split_name])
    any_query = f"""
        SELECT
            CASE
                WHEN derived_NAICS = '11' THEN 'Agriculture, forestry, fishing and hunting'
                WHEN derived_NAICS = '21' THEN 'Mining, quarrying, and oil and gas extraction'
                WHEN derived_NAICS = '22' THEN 'Utilities'
                WHEN derived_NAICS = '23' THEN 'Construction'

                WHEN derived_NAICS BETWEEN '31' AND '33' THEN 'Manufacturing'
                WHEN derived_NAICS = '41' THEN 'Wholesale trade'
                WHEN derived_NAICS BETWEEN '44' AND '45' THEN 'Retail trade'
                WHEN derived_NAICS BETWEEN '48' AND '49' THEN 'Transportation and warehousing'

                WHEN derived_NAICS = '51' THEN 'Information and cultural industries'
                WHEN derived_NAICS = '52' THEN 'Finance and insurance'
                WHEN derived_NAICS = '53' THEN 'Real estate and rental and leasing'
                WHEN derived_NAICS = '54' THEN 'Professional, scientific and technical services'
                WHEN derived_NAICS = '55' THEN 'Management of companies and enterprises'
                WHEN derived_NAICS = '56' THEN 'Administrative and support, waste management and remediation services'

                WHEN derived_NAICS = '61' THEN 'Educational services'
                WHEN derived_NAICS = '62' THEN 'Health care and social assistance'
                WHEN derived_NAICS = '71' THEN 'Arts, entertainment and recreation'
                WHEN derived_NAICS = '72' THEN 'Accommodation and food services'
                WHEN derived_NAICS = '81' THEN 'Other services (except public administration)'
                WHEN derived_NAICS = '91' THEN 'Public administration'

                ELSE 'N/A'
            END AS merchant_category
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
            LIMIT 1
        ) sub2
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



def save_transactions(statement_df):
    other_categories = [
        'ONLINE BANKING TRANSFER',
        'CONTACTLESS INTERAC REFUND',
        'E-TRANSFER SENT',
        'ATM TRANSFER TO DEPOSIT ACCT',
        'ATM DEPOSIT',
        'ATM WITHDRAWAL',
        'E-TRANSFER',
        'INSURANCE CPL:',
        'PAYROLL DEPOSIT',
        'ONLINE TRANSFER TO DEPOSIT ACCOUNT',
        'MISC PAYMENT MFRP'
    ]

    provinces = input("\nProvince (separate with ', ' if multiple): ").strip()
    cities = input("City (separate with ', ' if multiple): ").strip()

    statement_df["Transaction Date"] = statement_df["Transaction Date"].dt.date

    def get_category(row):
        # if category is in other_categories, return that as the category
        for cat in other_categories:
            if cat in str(row["Description 1"]):
                return cat
        
        # else, find NAIC code using categorize_merchants()
        return categorize_merchants(row["Description 2"], provinces, cities)

    statement_df["Category"] = statement_df.apply(get_category, axis=1)


    # Write categorized transactions to excel
    statement_df.to_excel("statement.xlsx", index=False)
    print("\nSuccessfully wrote dataframe to statement.xlsx")

    # Save categorized transactions to db
    conn = sqlite3.connect('transactions.db')
    statement_df.to_sql('transactions', conn, if_exists='replace', index=True, index_label='id')

    # For testing db
    # cursor = conn.cursor()
    # cursor.execute('SELECT * FROM transactions')
    # for row in cursor:
    #     print(row)

    conn.close()
    print("Successfully saved transactions to transactions.db\n")



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