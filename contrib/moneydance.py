"""

Set-up and execute this script to run web-bank-connect from inside MoneyDance

Author: Alex Yushin <alexis@ww.net>

"""

#
# 0. Essential system imports
#
import sys
import os
from datetime import datetime

import logging
logging.basicConfig()

#
#
# 1. Configuration
#
#

# 1.0 We have to have this one hard-coded as MoneyDance does not pass the __file__ to the script
WBC_HOME="/Users/alexis/Work/Python/web-bank-connect"
sys.path.append(WBC_HOME)

# 1.1 Directory where selenium is installed, normally /Library/Python/2.7/site-packages or alike
SELENIUM_DIR="/Library/Python/2.7/site-packages"
sys.path.append(SELENIUM_DIR)

# 1.2 The path to firefox
FIREFOX_PATH='/Applications/Firefox.app/Contents/MacOS'
os.environ['PATH'] = FIREFOX_PATH

#
# 2. Set up local connections...
#
from wbc.models import Connection, Account, NEVER

# 1. Configure the connections...
CONNECTIONS = [
    Connection(
        name        = 'BANK1',
        plugin      = 'nl.bank1',
        username    = 'user1',
        password    = 'password1',
        accounts    = [
            Account(
                name            = '12353795871',
                type            = 'ccard',
                moneydance_name = 'Visa Card',
                # It is possible to override the last download date and time, otherwise using Moneydance last
                # download timestamp
                last_download = NEVER,
                # The import will skip inactive account
                # active = False,
            ),
        ]
    ),
    Connection(
        name            = 'BANK2',
        plugin          = 'nl.bank2',
        username        = 'user2',
        password        = 'password2',
        accounts = [
            Account(
                type            = 'current',
                name            =  'IBAN123',
                moneydance_name = 'NL BANK IBAN123',
            ),
            Account(
                type            = 'ccard',
                name            =  '234723984732897982',
                moneydance_name = 'MasterCard',
                # last_download   = datetime(2016, 2, 12)
            ),
]

#
# 3. Run the script..
#
from wbc.moneydance2015 import download_all_transactions

download_all_transactions(
    ra = moneydance.getRootAccount(),
    moneydance = moneydance,
    connections = CONNECTIONS,
)