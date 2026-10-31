# Royal Bank of Canada Statement Analyzer

Banking, simplified. A local Streamlit application to help you understand your Royal Bank of Canada (RBC) transactions, without the technical jargon. Upload an RBC CSV (instructions below) to view debit and credit account summaries, auto-map merchants to their spending category using a database of 446k+ Canadian business records, interact with a dynamic pie chart that breaks down your spending, and download an analyzed Excel spreadsheet with your new transaction insights.

## Setup

1. Clone or download this repository and open a terminal in the project folder.
2. Create and activate a virtual environment using the commands for your operating system.

   **Windows (PowerShell):**

   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate
   ```

   **macOS (Terminal, Zsh or Bash):**

   Install Python 3 if it is not already available, then run:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

   Activate the environment again whenever you open a new terminal. Once activated, use `python` for the commands below on either operating system.

3. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

4. Ensure `CA_MERCHANTS.db` is in the project root. The current categorizer queries its `MERCHANT_INFO` table.
5. Start the dashboard:

   ```powershell
   python -m streamlit run app.py
   ```

## Download RBC transactions as a CSV

Use RBC Online Banking in a desktop browser. Download transaction activity as CSV. A PDF account statement is not supported by this application.

1. Go to [RBC Royal Bank](https://www.rbcroyalbank.com/) and sign in to Online Banking.
2. From **My Accounts** or the accounts summary, select the account you want to analyze.
3. Open its transaction list. Use the date filter to select your desired period and apply the filter, if available.
4. Find **Download** above and to the right of the transactions table.
5. Choose **CSV** (sometimes described as comma-delimited or a spreadsheet format). If the download screen offers an account or date-range selector, confirm those selections there too.
6. Select **Continue** or the download confirmation button, and save the `.csv` file.
7. Check that the downloaded file contains the intended dates and transactions. Keep its original column headers and formatting.

Button labels and available history can vary by account and interface. If you only see PDF statements, return to the account's transaction list rather than the Statements/Documents page.

## Analyze a file

1. In the dashboard, upload the downloaded CSV. No special filename or file location is required.
2. Review the start and end dates, which are filled from the uploaded transactions.
3. Enter provinces or cities to narrow merchant lookups (highly advised).
4. Click **Analyze** to view totals, categories, the transaction table, and the spending chart.
5. Edit categories in the table and click **Save Changes**. You can also apply a category change to matching merchants.
6. Click **Download Analyzed Excel** to export the current results.

The current parser expects RBC columns including `Transaction Date`, `Description 1`, and `CAD$`. **DO NOT ALTER THESE COLUMN NAMES**. Merchant lookup results should be reviewed, especially for abbreviated or ambiguous names.

Analyzing a file currently replaces the contents of the local `transactions.db`; it does not maintain a combined history of uploads.

## Data files

- `data/raw/`: original CSV inputs and the Canadian business dataset.
- `data/labeled/`: analyzed workbooks.
- `CA_MERCHANTS.db`: merchant lookup database used by the current application.
- `transactions.db`: local results and saved category edits.

## Local storage and privacy

When you run the app on your own computer using the setup above, transaction processing and merchant lookups take place locally. The current application code does not send your transaction data to external APIs or remote databases.

**Analyzed transactions and saved category edits are stored on your computer in `transactions.db`. Closing the browser session or stopping the app does not delete this file.** To remove these saved results, stop the app and delete `transactions.db`; the app will recreate it the next time you analyze a file. Your original CSV files and any downloaded Excel workbooks remain wherever you saved them.

The app does not create a remote copy of your transactions as part of this local workflow. This description applies to running the app locally: if you deploy it on a hosted server, uploads are processed and the database is stored on that server instead. Files in cloud-synced folders may also be copied by your sync service independently of the app.

CSV files, Excel workbooks, and `transactions.db` are excluded from new Git commits by `.gitignore`; files already tracked by Git are not protected by ignore rules. You may remove account numbers and other personal identifiers before uploading, while preserving the required column headers.
