#
#
# A sample script that reads local connections from config_local.py
# and scrapes them all
#

import logging

from config.config_local import *
from wbc.wbc import scrape_all

logging.basicConfig()

all_statements = scrape_all(CONNECTIONS)
print all_statements