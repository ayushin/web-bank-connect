"""

Author: Alex Yushin <alexis@ww.net>

Configuration:

        Connection1
                |
                +---> name
                |
                +---> plugin
                |
                +---> username
                |
                +---> password
                |
                |
                +---> accounts[]
                        Account1
                            |
                            +-----> name
                            |
                            +-----> type
                            |
                            +-----> currency
                            |
                            +-----> internal_name (can be i.e. moneydance_name to specify moneydance account)
                        ...
                        Account2
                        Account3
        Connection2
                ...

Downloaded transactions:

        Statement1
                |
                +----> account -> Account1 (link to the account in configuration)
                |
                +----> opening_balance
                |           Balance
                |
                +----> closing_balance
                |           Balance
                |
                +----> transactions[]
                            Transaction1
                            Transaction2
                            ....
                            TransactionXXX


"""

from plugins.base import load_plugin
from hashlib import md5
from datetime import datetime

NEVER = datetime.utcfromtimestamp(0)

import logging
logger = logging.getLogger(__name__)

class Connection(object):
    """
    This class stores the connections configuration and serves as an interface to the underlying
    plugins methods.

    """
    active = True
    accounts = []

    def __init__(self, plugin, name, username, password, accounts = None, **kwargs):
        """
        Creates a connection object and loads the specified plugin.

        :param plugin:  The name of the plugin to be loaded. It will be prefixed
                        with wbc.plugins.base.PLUGINS_PREFIX and suffixed with
                        wbc.plugins.base.PLUGINS_SUFFIX

                        i.e. plugin = nl.ingbank might load wbc.plugins.nl.ingbank.Plugin()

        :param name:    An arbitraty name of the connection, not used at the moment

        :param username: The username to use while logging in

        :param password: Password to be used with the username

        :param accounts: A list of the accounts associated with this connection. Usually:
                        accounts = [Account(..), Account(...)]

        :param: **kwargs A list of arguements that will be passed to the plugin as attributes
                        after it is loaded

        """
        self.plugin = load_plugin(plugin)
        self.name = name
        self.username = username
        self.password = password
        self.accounts = accounts

        # Pass the optional arguments to the connection
        for kw in kwargs.keys():
            self.plugin.__setattr__(kw, kwargs[kw])

    def login(self):
        # Log-in if not already
        if not self.plugin.logged_in:
            self.plugin.login(username = self.username, password = self.password)
        assert self.plugin.logged_in

    def download_statements(self, accounts = None):
        """
        Downloads the transactions for the accounts that are configured and not marked inactive

        :return:    A list of statements
        """

        statements = []

        if not accounts:
            accounts = self.accounts
        assert accounts

        self.login()

        for account in accounts:
            if account.active:
                statement = getattr(self.plugin, 'download_' + account.type)(account)
                if statement:
                    statement.account = account
                    statements.append(statement)

        # self.plugin.logout()

        return statements



    def list_accounts(self):
        """
        Returns a list of accounts available from this connection. Keeps the current list of accounts
        intact.

        :return:
        """
        self.login()

        return self.plugin.list_accounts()

    def __conf__str__(self):
        """
        Prints python configuration string to initialize this Connection object.

        :return:
        """
        conf_str = """Connection(
            name        = %s,
            plugin      = %s,
            username    = %s,
            password    = %s,
            active      = %s,
            accounts    = [
            """
        for account in self.accounts:
            conf_str += account.__conf__str__()

        conf_str += """]
            )"""

        return conf_str

class Account(object):
    last_download = None
    active = True
    currency = None

    def __init__(self, name, type, currency = None, **kwargs):
        self.name = name
        self.type = type
        self.currency = currency

        # Pass the optional arguements to the account
        for kw in kwargs.keys():
            self.__setattr__(kw, kwargs[kw])

    def __conf__str__(self):
        return """Account(
            name = %s,
            type = %s,
            active = %s,
            last_download = %s,
            currency = %s
            )""" % (self.name, self.type, self.active, self.last_download, self.currency)

    def __str__(self):
        return "Account %s; type=%s; currency=%s" % (self.name, self.type, self.currency)

class Statement(object):
    transactions = []

    opening_balance = None
    closing_balance = None

    def finalize(self):
        self.generate_fitids()
        return self

    def generate_fitids(self):
        """

        Generates transactions id's for those transactions which do not have them


        """
        duplicates = {}

        for transaction in self.transactions:
            # only generate transaction ids if there is no unique identifier scraped from bank
            if transaction.fitid:
                continue

            trnhash = md5(
                str(transaction.date) +
                transaction.name.encode('utf-8') +
                transaction.memo.encode('utf-8') +
                str(transaction.type) +
                str(transaction.amount) +
                (transaction.refnum or '')
            ).hexdigest()

            if duplicates.get('trnhash'):
                duplicates[trnhash] += 1
                logger.info("Found identical transaction on %s, amount %f" % (transaction.date, transaction.amount))
            else:
                duplicates[trnhash] = 0

            transaction.fitid = trnhash + '/' + str(duplicates[trnhash])

class Balance(object):
    def __init__(self, date, amount):
        self.date = date
        self.amount = amount
        return self

class transactionType:
    CREDIT      = 'credit'      # Generic credit
    DEBIT       = 'debit'       # Generic debit
    INT         = 'int'         # Interest earned or paid
    DIV         = 'div'         # Dividend
    FEE         = 'fee'         # FI fee
    SRVCHG      = 'srvchg'      # Service charge
    DEP         = 'dep'         # Deposit
    ATM         = 'atm'         # ATM debit or credit
    POS         = 'pos'         # Point of sale debit or credit
    XFER        = 'xfer'        # Transfer
    CHECK       = 'check'       # Check
    PAYMENT     = 'payment'     # Electronic payment
    CASH        = 'cash'        # Cash withdrawal
    DIRECTDEP   = 'directdep'   # Direct deposit
    DIRECTDEBIT = 'directdebit' # Merchant initiated debit
    REPEATPMT   = 'repeatpmt'   # Repeating payment/standing order
    OTHER       = 'other'       # Other

class Transaction(object):
    # Provide reasonable defaults
    reservation = False
    refnum = None
    fitid = None

    # @property
    # def datePosted(self, datePosted):
    #     datePosted

    def __init__(self, date, **kwargs):
        self.date = date

        # Pass the optional attributes
        for kw in kwargs.keys():
            self.__setattr__(kw, kwargs[kw])


    def __str__(self):
        return "%s:%s:%s:%s:%s:%s (%s)" % (self.date, self.name, self.memo, self.type, self.amount, self.refnum, self.fitid)

    def __ofx__(self):
        pass

        # ofx_str = """<STMTTRN>
        #     <TRNTYPE>%s</TRNTYPE>
        #         <DTPOSTED>%s</DTPOSTED>
        #         <DTUSER>{{ trn.date_user | date:"Ymd"}}</DTUSER>
        #         <TRNAMT>{{ trn.amount }}</TRNAMT>
        #         <FITID>{{ trn.refnum }}</FITID>
        #         <NAME>{{ trn.payee }}</NAME>
        #         <MEMO>{{ trn.memo }}</MEMO>
        #     </STMTTRN>