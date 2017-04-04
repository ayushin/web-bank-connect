#
#
# Copy this file to ~/.wbc/config.py (or elsewhere and use --config option) and modify according to your needs
#
#
# Author: Alex Yushin <alexis@ww.net>
#
#
CONNECTIONS = [
    Connection(
        name        = 'BANK1',
        plugin      = 'nl.bank1',
        # It is possible to override the default driver
        # driver    = 'Chrome'
        # driver    = 'PhantomJS'
        username    = 'user1',
        password    = 'password1',
        accounts    = [
            Account(
                name            = '12353795871',
                type            = 'ccard',
                moneydance_name = 'Visa Card',
                # It is possible to override the last download date and time, otherwise Moneydance last
                # download timestamp will be used (if used with moneydance)
                last_download = NEVER,
                # If download interval is specified then the wbc won't try downloading this account until
                # download_interval is elapsed since the last_download
                download_interval=timedelta(hours=1),
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