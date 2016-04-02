"""
Set-up and execute this script to run web-bank-connect from inside MoneyDance

Author: Alex Yushin <alexis@ww.net>

"""

import sys

from datetime import date

#
#
# Set-up
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

#
#
# Scraping part...
#
#
import wbc
from local_connections import CONNECTIONS

# Download all statements...
statements = wbc.scrape_all(CONNECTIONS)

#
#
#
# Moneydance part
#
#
from com.moneydance.apps.md.model import ParentTxn, SplitTxn, AbstractTxn

ra = moneydance.getRootAccount()

# Create Moneydance transactions
for st in statements:
    print "Creating %s transactions"  % st['account']

    md_account = ra.getAccountByName(st['account'])
    md_category = ra.getAccountByName("Miscellaneous")

    for line in st['transactions']:
        date = int(line['date'].strftime("%Y%m%d"))

        new_txn = ParentTxn(date, date, date, line['refnum'], md_account, line['name'], line['memo'], -1,
                            ParentTxn.STATUS_UNRECONCILED)
        new_txn.setTransferType(AbstractTxn.TRANSFER_TYPE_BANK)

        txnSplit = SplitTxn(new_txn, line['amount'], line['amount'], 1.0, md_category, line['name'],
                            -1, AbstractTxn.STATUS_UNRECONCILED  )
        new_txn.addSplit(txnSplit)
        print new_txn
        ra.getTransactionSet().addNewTxn(new_txn)

ra.refreshAccountBalances()