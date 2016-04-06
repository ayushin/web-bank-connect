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

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


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
        # If account's moneydance name is not configured, set it to account's name
        if not account.get('moneydance_name'):
            account['moneydance_name'] = account['name']

        mdAccount = ra.getAccountByName(account['moneydance_name'])
        assert mdAccount

        # Find the last downloaded transaction in this account -- thank you Sean!
        # ...unless hardcoded or overriden in CONNECTIONS
        account['lastupdate'] = account.get('lastupdate',
                    datetime.utcfromtimestamp(MDAccountProxy(mdAccount).getOFXLastTxnUpdate()/1000).date())

        print 'last download for this account was on %s' % account['lastupdate']


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

    # Keep track of reserved transactions
    date_last_update = date.today()

    # Get the downloadedTransactions list...
    downloadedTransactions = mdAccount.getDownloadedTxns()

    # Iterate through the transactions we scraped in (2) above
    for transaction in statement['transactions']:

        # We do not add reservation, but
        # If we have a reservation --  next time we should start our update from that date...
        if transaction.get('reservation'):
            logger.info('skipping reservation of %s on %s' % (transaction['amount'], transaction['date']))
            if transaction['date'] < date_last_update:
                date_last_update = transaction['date']
            continue

        newTxn = downloadedTransactions.newTxn()

        newTxn.setDatePostedInt(int(transaction['date'].strftime("%Y%m%d")))
        newTxn.setName(transaction['name'])
        newTxn.setMemo(transaction['memo'])
        newTxn.setRefNum(transaction['refnum'])
        newTxn.setAmount(mdAccount.getCurrencyType().parse(str(transaction['amount']), '.'))
        newTxn.setTxnType(transaction['type'])

        downloadedTransactions.addNewTxn(newTxn)


    if statement.get('balance'):
        downloadedTransactions.setOnlineLedgerBalance(\
            account.getCurrencyType().parse(str(statement['balance']['amount']), '.'),
                long((statement['balance']['date'] - date(1970, 1, 1)).total_seconds()*1000))


    # Update the last download date...
    #
    # One weak spot below can be if some older transactions only appear at some later date, after a
    # weekend for example: sale was done saturday, download was done saturday, transaction was reserved only,
    # sunday we downloaded transactions again, so the download date is sunday, but
    # then monday the saturday transaction was finalised but with the saturday's date
    MDAccountProxy(mdAccount).setOFXLastTxnUpdate(long((date_last_update - date(1970, 1, 1)).total_seconds()*1000))

    # A little MoneyDance magic to get the transactions updated -- thank you Sean!
    moneydance.getUI().getOnlineManager().getDefaultUIProxy().receivedStatement(MDAccountProxy(mdAccount))
