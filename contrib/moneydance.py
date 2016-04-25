"""

Set-up and execute this script to run web-bank-connect from inside MoneyDance

Author: Alex Yushin <alexis@ww.net>

"""


# 0.1 Essential system imports
import sys
import os

# 0.2 Set up logging for debugging...
import logging
logging.basicConfig()

# 1.0 We have to have this one hard-coded as MoneyDance does not pass the __file__ to the script
WBC_PATH = os.environ['WBC_PATH']
sys.path.append(WBC_PATH)

# 1.1 Directory where selenium is installed, normally /Library/Python/2.7/site-packages or alike
SELENIUM_PATH = os.environ['SELENIUM_PATH']
sys.path.append(SELENIUM_PATH)


# 1.2 The path to firefox and phantomjs binary...
FIREFOX_PATH = '/Applications/Firefox.app/Contents/MacOS'
# FIREFOX_PATH = os.environ['FIREFOX_PATH']
os.environ['PATH'] += os.pathsep + FIREFOX_PATH

# 2. Set up local connections...
from local.config import *

# 3. Run the script..
from wbc.moneydance import download_all_transactions

download_all_transactions(
    ra = moneydance.getRootAccount(),
    moneydance = moneydance,
    connections = CONNECTIONS,
)