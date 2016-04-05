"""
Set-up and execute this script to run web-bank-connect from inside MoneyDance

Author: Alex Yushin <alexis@ww.net>

"""
import sys
import os

#
#
# 0. Configuration
#
#

# We have to have this one hard-coded as MoneyDance does not pass the __file__ to the script
WBC_HOME="/Users/alexis/Work/Python/web-bank-connect"
sys.path.append(WBC_HOME)

# Directory where selenium is installed, normally /Library/Python/2.7/site-packages or alike
SELENIUM_DIR="/Library/Python/2.7/site-packages"
sys.path.append(SELENIUM_DIR)

# The path to firefox
FIREFOX_PATH='/Applications/Firefox.app/Contents/MacOS'
os.environ['PATH'] = FIREFOX_PATH

from config import CONNECTIONS
from wbc.wbc import scrape_all

from datetime import date, datetime

from com.infinitekind.moneydance.model import OnlineTxn
from com.moneydance.apps.md.view.gui import MDAccountProxy

#
#
# 1. Sanity check and setup last downloaded transaction...
#
#

# Get MoneyDance RootAccount...
ra = moneydance.getRootAccount()

# Iterate through all the configured accounts to check if they are present in MoneyDance and
# find out the last transaction...
for connection in CONNECTIONS:
    for account in connection['accounts']:
        mdAccount = ra.getAccountByName(account['name'])
        assert mdAccount
        # Find the last downloaded transaction in this account
        account['datefrom'] = date(2016, 01, 01) # mdAccount.getLastTxn().getDatePosted()
        # We should check mdAccount.getAccountType() here... How to deal with identical names for Current and Savings?

        # If account's moneydance name is not configured, set it to account's name
        if not account.get('moneydance_name'):
            account['moneydance_name'] = account['name']

#
#
# 2. Scrape all
#
#
statements = scrape_all(CONNECTIONS)


#
#
# 3. Post the transactions to MoneyDance
#
#
for statement in statements:

    # Get the mdAccount to work with
    mdAccount = ra.getAccountByName(statement['account']['moneydance_name'])
    assert mdAccount

    # Get the downloadedTransactions list...
    downloadedTransactions = mdAccount.getDownloadedTxns()

    # Iterate through the transactions we scraped in (2) above
    for transaction in statement['transactions']:
        newTxn = downloadedTransactions.newTxn()

        newTxn.setDatePostedInt(int(transaction['date'].strftime("%Y%m%d")))
        newTxn.setName(transaction['name'])
        newTxn.setMemo(transaction['memo'])
        newTxn.setRefNum(transaction['refnum'])
        newTxn.setAmount(mdAccount.getCurrencyType().parse(str(transaction['amount']), '.'))
        newTxn.setTxnType(transaction['type'])

        downloadedTransactions.addNewTxn(newTxn)

    if statement.get('closing_balance'):
        downloadedTransactions.setOnlineLedgerBalance(\
            account.getCurrencyType().parse(str(statement['closing_balance']['amount']), '.'),
                                              statement['closing_balance']['date'].toordinal())

    # A little MoneyDance magic to get the transactions updated -- thank you Sean!
    moneydance.getUI().getOnlineManager().getDefaultUIProxy().receivedStatement(MDAccountProxy(mdAccount))
