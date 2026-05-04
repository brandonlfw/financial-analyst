import pandas as pd
import plot_graphs
import json
import sqlite3
import re
from datetime import datetime


def categorize_merchants(merchant_name, provinces, cities):
    """
    This function is passed a merchant name from transactions_to_json and classifies the merchant's category based off the name and user-passed province(s)/city(s) of purchase.
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

    df = statement_df.copy()
    df["Transaction Date"] = df["Transaction Date"].dt.date

    # Create new 'Merchant' column: Description 2 if it exists, else use Description 1
    df["Merchant"] = df.apply(
        lambda row: row["Description 2"] if isinstance(row["Description 2"], str) else row["Description 1"],
        axis=1
    )

    def get_category(row):
        # if category is in other_categories, return that as the category
        for cat in other_categories:
            if cat in str(row["Description 1"]):
                return cat
        
        # else, find NAIC code using categorize_merchants()
        return categorize_merchants(row["Merchant"], provinces, cities)

    df["Category"] = df.apply(get_category, axis=1)


    # Write categorized transactions to excel
    df.to_excel("statement.xlsx", index=False)
    print("Successfully wrote dataframe to statement.xlsx\n")

    # Save categorized transactions to db
    conn = sqlite3.connect('transactions.db')
    df.to_sql('transactions', conn, if_exists='replace', index=False)
    conn.close()
    print("Successfully saved transactions to transactions.db\n")



def analyze_transactions(statement_df, start_date, end_date):
    """
    Iterate each transaction in statement_df and sum and print all debits, credits, and create list of all transactions $50 or above.
    Plot transactions graph with stars on flagged purchases >= $50 using plot_graphs() from plot_graphs module.
    """
    total_debits = 0 # per date range/statement period
    total_credits = 0 # ^
    flagged_above = []
    flagged_below = []
    
    debits = {} # date: [trans1, trans2...]
    credits = {} # ^


    # Debit transaction flagging
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
        
    # Loop thru all transactions and sums all debits for total spending
    for index, row in statement_df.iterrows(): 
        if row["CAD$"] < 0: # transactions with '-' are debits
            total_debits += row["CAD$"]
        total_debits = round(total_debits, 2)

        if row["CAD$"] > 0: # transactions with '+' are credits
            total_credits += row["CAD$"]
        total_credits = round(total_credits, 2)

        # Flag transactions at or ABOVE upper_limit
        if row["CAD$"] <= upper_limit:
            flagged_above.append(index) # the index is 2 behind the number on the csv

        # Flag transactions at or BELOW lower_limit but ABOVE 0
        if row["CAD$"] >= lower_limit and row["CAD$"] < 0:
            flagged_below.append(index)

        # converts date format to YYYY-MM-DD
        date_str = row["Transaction Date"].strftime("%Y-%m-%d") 


        # DEBITS AND CREDITS DICTIONARY FOR SUMMING TOTALS ------------------------------------------------------------------------------------
        # Store all debits and credits from each merchant by date into a dictionary
        if row["CAD$"] < 0: # debits
            if date_str not in debits:
                debits[date_str] = []
            debits[date_str].append(row["CAD$"])
        elif row["CAD$"] > 0: # credits
            if date_str not in credits:
                credits[date_str] = []
            credits[date_str].append(row["CAD$"])
        
    # debits_by_date and credits_by_date are dicts with dates (keys) where there was a transaction(s), then adds the TOTAL debits/credits (value) for that day
    debits_by_date = {date: round(sum(amts),2) for (date, amts) in debits.items()} # sum all debits for each date in dict
    credits_by_date = {date: round(sum(amts),2) for (date, amts) in credits.items()} # sum all credits for each date in dict

    # SUMMARY ----------------------------------------------------------------------
    print(f"Summary of transactions from {start_date.date()} to {end_date.date()}:")
    print(f"Total debits: ${-total_debits}") # Total spending in period
    print(f"Total credits: ${total_credits}\n") # Total credits in period

    print(f"\nThe following transactions were flagged for being at or ABOVE ${-upper_limit}:\n")
    for index in flagged_above:
        transaction = statement_df.loc[index]
        print(f"CSV Index {index + 2} {transaction['Transaction Date'].date()}: {transaction['Description 1']} from {transaction['Description 2']} for ${-transaction['CAD$']}")
        # the dataframe index is 2 behind the number on the CSV, so we add 2 to it to get the correct index in the CSV statement

    print(f"\nThe following transactions were flagged for being at or BELOW ${-lower_limit}:\n")
    for index in flagged_below:
        transaction = statement_df.loc[index]
        print(f"CSV Index {index + 2} {transaction['Transaction Date'].date()}: {transaction['Description 1']} from {transaction['Description 2']} for ${-transaction['CAD$']}")

    # PLOT GRAPHS ------------------------------------------------------------------
    # plot_graphs.plot_graphs(statement_df, start_date, end_date, debits_by_date, credits_by_date) # disable until fixed with new flagging system



def create_filtered_tuples():
    conn = sqlite3.connect('transactions.db')
    cursor = conn.cursor()
    cursor.execute('SELECT Merchant, "CAD$", "Transaction Date" FROM transactions')
    all_transactions = [(row[0], row[1], row[2]) for row in cursor.fetchall()]
    conn.close()
    return all_transactions



def filter_transactions(all_transactions, merchant, min_amt, max_amt, min_date, max_date):
    """
    all_transactions containing (merchant, amt, date) tuples are passed along with user-inputted merchant name, min and max amount, earliest and latest date.
    Each filter will reduce the # of tuples in filtered_list if the filter condition is not satisfied for that tuple, removing it.
    The resulting filtered_list is printed.
    """

    filtered_list = all_transactions

    # MERCHANT FILTER ---------------------------------------------------
    if merchant:
        filtered_list = [trans for trans in filtered_list if merchant.lower() in trans[0].lower()]

    # TRANSACTION AMT FILTER --------------------------------------------
    if min_amt:
        filtered_list = [trans for trans in filtered_list if abs(trans[1]) >= float(min_amt)]
    if max_amt:
        filtered_list = [trans for trans in filtered_list if abs(trans[1]) <= float(max_amt)]
    
    # DATE FILTER -------------------------------------------------------
    if min_date:
        filtered_list = [trans for trans in filtered_list if datetime.strptime(trans[2], "%Y-%m-%d") >= min_date]
    if max_date:
        filtered_list = [trans for trans in filtered_list if datetime.strptime(trans[2], "%Y-%m-%d") <= max_date]

    print(f"The filtered list is: {filtered_list}\n")