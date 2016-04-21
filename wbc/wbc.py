#
#
# Author: Alex Yushin <alexis@ww.net>
#
#

import logging
logger = logging.getLogger(__name__)

from pprint import pprint, pformat


def download_all_transactions(connections):
    for connection in connections:
        connection.download_all_transactions()

def list_all_accounts(connections):
    for connection in connections:
        connection.list_accounts()

def print_all_transactions(connections):
    for c in connections:
        for a in c.accounts:
            pprint(a)
            for t in a.statement.transactions:
                print t