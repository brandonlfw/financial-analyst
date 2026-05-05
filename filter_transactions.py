import sqlite3
from datetime import datetime



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




def filter(all_transactions):
    '''
    Takes all_transactions (tuples) and searches for matches on filter criteria to return to user.
    '''

    while True:
        use_filter = input("\nWould you like to filter transactions? (Y/N) ")

        if use_filter == "Y":
            print("Answer the following prompts to filter transactions. Press 'Enter' to skip a filter.\n")
            filter_merchant = input("Filter by merchant: ")
            filter_min_amt = input("Filter by minimum amount: $")
            filter_max_amt = input("Filter by maximum amount: $")
            filter_min_date = input("Filter by earliest date (YYYY-MM-DD): ")
            filter_max_date = input("Filter by latest date (YYYY-MM-DD): ")
            
            # Convert user string date input to datetime format
            if filter_min_date: 
                filter_min_date = datetime.strptime(filter_min_date, "%Y-%m-%d")
            else:
                filter_min_date = None

            if filter_max_date:
                filter_max_date = datetime.strptime(filter_max_date, "%Y-%m-%d")
            else:
                filter_max_date = None
            
            filter_transactions(all_transactions, filter_merchant, filter_min_amt, filter_max_amt, filter_min_date, filter_max_date)

        else:
            break