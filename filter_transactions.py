from rbc_analysis import filter_transactions
from datetime import datetime


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