#
#
# A sample script that reads local connections from config.py
# and scrapes them all
#

from config import *
from wbc.wbc import scrape_all


all_statements = scrape_all(CONNECTIONS)
print all_statements