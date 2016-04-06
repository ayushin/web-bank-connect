#
#
# A sample script that downloads the list of the accounts for each connection
# configured in config.py
#


from config import *
from wbc.wbc import load_plugin

import logging
logging.basicConfig()

for connection in CONNECTIONS:
    plugin = load_plugin(connection['plugin'])
    plugin.login(connection['username'], connection['password'])
    connection['accounts'] = plugin.list_accounts()
    plugin.logout()

print CONNECTIONS