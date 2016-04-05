"""
This script downloads the list of accounts from the specified connections
and creates those accounts that are missing

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
from wbc.wbc import load_plugin

from datetime import date, datetime

from com.infinitekind.moneydance.model import OnlineTxn
from com.moneydance.apps.md.view.gui import MDAccountProxy



#
#
# 1. Download the accounts
#
#
for connection in CONNECTIONS:
    plugin = load_plugin(connection['plugin'])
    plugin.login(connection['username'], connection['password'])
    connection['accounts'] = plugin.list_accounts()
    plugin.logout()


#
#
# 2. Create the missing accounts in Moneydance
#
#
ra = moneydance.getRootAccount()

for connection in CONNECTIONS:
    for account in connection['accounts']:
        # here we should be creating the accounts
        pass