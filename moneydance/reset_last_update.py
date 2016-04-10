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

from config.config_local import CONNECTIONS

from datetime import date, datetime

from com.moneydance.apps.md.view.gui import MDAccountProxy


new_date = date(2016, 1, 1)
new_date_long = long((new_date - date(1970, 1, 1)).total_seconds()*1000)

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

        print 'last download for this account was on %s now set to %s' % (account['lastupdate'], new_date)

        MDAccountProxy(mdAccount).setOFXLastTxnUpdate(new_date_long)
