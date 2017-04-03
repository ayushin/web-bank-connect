import argparse
import logging


import os
import imp

DEFAULT_CONFIG = os.path.join(os.path.expanduser('~'), '.wbc_config.py')

logging.basicConfig()

from datetime import datetime, timedelta

def main():
    # 1. Configure
    parser = argparse.ArgumentParser('web bank connect utility script')
    parser.add_argument('--config', default = DEFAULT_CONFIG, type = str, help = 'config module to load')
    parser.add_argument('--account', default = None, type = str, help = 'account for downloading of transactions')

    parser.add_argument('command', choices=['login', 'download', 'list', 'config'])
    parser.add_argument('connection', type = str, help = 'use this connection', nargs='?', default=None)

    args = parser.parse_args()

    # 2. Load connections from local
    #__temp = __import__(args.config, globals(), locals(), ['CONNECTIONS'], -1)

    try:
        __temp = imp.load_source('wbc.config', args.config)
        CONNECTIONS = __temp.CONNECTIONS
    except:
        print "Unable to load the configuration from " + args.config
        raise


    def find_connection_by_shortcut(connection_shortcut, connections):
        for c in connections:
            if c.shortcut == connection_shortcut:
                return c
        raise ValueError('could not find connection %s in configuration' % connection_name)

    if args.command == 'login':
        if args.connection:
            find_connection_by_shortcut(args.connection, CONNECTIONS).login()
        else:
            raise argparse.ArgumentError(args.connection, "login command requires connection name")

    elif args.command == 'download':
        if args.connection:
            CONNECTIONS = [find_connection_by_shortcut(args.connection, CONNECTIONS)]

        statements = []

        # 2. Download the transactions...
        for connection in CONNECTIONS:
            statements.extend(connection.download_statements())

        # 3. Print the result
        for statement in statements:
            print statement.account
            for transaction in statement.transactions:
                print transaction

    elif args.command == 'list':
        if args.connection:
            CONNECTIONS = [find_connection_by_shortcut(args.connection, CONNECTIONS)]

        for connection in CONNECTIONS:
            connection.accounts = connection.list_accounts()
            print connection.__conf__str__()

    elif args.command == 'config':
        print __temp.__file__
