#
#
# web-bank-connect
#
# Copy this file to ~/.wbc/config.py (or elsewhere and use --config option) and modify according to your needs
#
# You can use 'Connection()', 'Account()', NEVER, datetime(), timedelta() functions as they are automatically
# imported in the command-line-interface code "cli.py"
#
#
# Author: Alex Yushin <alexis@ww.net>
#
#

#
# The local configuration file should create/override a list called 'CONNECTIONS' with your actual accounts
# information.
#
#         Connection1
#                 |
#                 +---> name
#                 |
#                 +---> plugin
#                 |
#                 +---> username
#                 |
#                 +---> password
#                 |
#                 |
#                 +---> accounts[]
#                         Account1
#                             |
#                             +-----> name
#                             |
#                             +-----> type
#                             |
#                             +-----> currency
#                             |
#                             +-----> internal_name (can be i.e. moneydance_name to specify moneydance account)
#                         ...
#                         Account2
#                         Account3
#         Connection2
#                 ...
#

CONNECTIONS = [
    # Each Connection object should have at least a 'name' and a 'plugin' configured for it
    # You also need to configure a 'username' and optionally a 'password' otherwise you will
    # have to type it in every time the wbc connects to your bank.
    #
    # Another handy parameter is 'shortcut' so that you can name your connection with an alias from
    # the command line interface.

    Connection(
        # A unique name for this connection
        name        = 'BANK1',
        shortcut    = 'b1',

        # The plugin name, the name of the module that is located in wbc.plugins - e.g. wbc/plugins/nl/bank1.py
        # cant be accessed as nl.bank1
        plugin      = 'nl.bank1',

        # It is possible to override the default driver
        # driver    = 'Chrome'
        # driver    = 'PhantomJS'
        driver    = FireFox
        # The username that you use for connecting to your bank with this connection
        username    = 'user1',

        # Password. It is recommended to leave it empty (None) for security reasons so that wbc will
        # ask it everytime it connects
        password    = 'password1',

        # A list of actual accounts associated with this connectoion
        accounts    = [
            Account(
                # Name of this account exactly as it is displayed in your web-banking
                name            = '12353795871',
                # Type of the account, can be 'current', 'savings' or 'ccard' for credit-card
                type            = 'ccard',
                # If you are using WBC with Moneydance and the account name is different there, specify.
                moneydance_name = 'Visa Card',
                # It is possible to override the last download date and time, otherwise Moneydance last
                # download timestamp will be used (if used with moneydance)
                last_download = NEVER,
                # If download interval is specified then the wbc won't try downloading this account until
                # download_interval is elapsed since the last_download
                download_interval = timedelta(hours=1),
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
            )
        ]
    )
]