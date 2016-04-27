import argparse
import logging
logging.basicConfig()


# 1. Configure
parser = argparse.ArgumentParser('web bank connect utility script')
parser.add_argument('--config', default='local.config', type = str, help = 'config module to load')
parser.add_argument('--account', default = None, type = str, help = 'account for downloading of transactions')

parser.add_argument('command', choices=['login', 'download', 'list'])
parser.add_argument('connection', type = str, help = 'use this connection', nargs='?', default=None)

args = parser.parse_args()

# 2. Load connections from local
__temp = __import__(args.config, globals(), locals(), ['CONNECTIONS'], -1)
CONNECTIONS = __temp.CONNECTIONS

def find_connection_by_name(connection_name, connections):
    for c in connections:
        if c.name == connection_name:
            return c
    raise ValueError('could not find connection %s in configuration' % connection_name)

if args.command == 'login':
    if args.connection:
        find_connection_by_name(args.connection, CONNECTIONS).login()
    else:
        raise argparse.ArgumentError(args.connection, "login command requires connection name")

elif args.command == 'download':
    if args.connection:
        CONNECTIONS = [find_connection_by_name(args.connection, CONNECTIONS)]

    statements = []

    # 2. Download the transactions...
    for connection in CONNECTIONS:
        statements.extend(connection.download_statements())

    # 3. Print the result
    for statement in statements:
        print statement.account
        for transaction in statement.transactions:
            print transaction.encode('utf-8')
elif args.command == 'list':
    pass