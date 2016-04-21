"""

Author: Alex Yushin <alexis@ww.net>

"""
from plugins.base import load_plugin
from hashlib import md5
from datetime import datetime

NEVER = datetime.utcfromtimestamp(0)

import logging
logger = logging.getLogger(__name__)

class Connection(object):
    accounts = []

    def __init__(self, plugin, name, username, password, accounts, **kwargs):
        self.plugin = load_plugin(plugin)
        self.name = name
        self.username = username
        self.password = password
        self.accounts = accounts

        # Pass the optional arguments to the connection
        for kw in kwargs.keys():
            self.__setattr__(kw, kwargs[kw])

    def download_all_transactions(self):
        # Log-in if not already
        if not self.plugin.logged_in:
            self.plugin.login(username = self.username, password = self.password)
        assert self.plugin.logged_in

        for account in self.accounts:
            getattr(self.plugin, 'download_' + account.type)(account)

        # self.plugin.logout()


    def list_accounts(self):
        """
        Returns a list of accounts available from this connection. Also appends this list to Connection.accounts
        making it ready for download_transactions

        :return:
        """
        # Log-in if not already
        if not self.plugin.logged_in:
            self.plugin.login(username = self.username, password = self.password)
        assert self.plugin.logged_in

        self.accounts =  self.plugin.list_accounts()

        return self.accounts

class Account(object):
    last_download = None
    active = True
    def __init__(self, name, type, currency = None, **kwargs):
        self.name = name
        self.type = type
        self.currency = currency

        # Pass the optional arguements to the account
        for kw in kwargs.keys():
            self.__setattr__(kw, kwargs[kw])

class Statement(object):
    transactions = []

    opening_balance = None
    closing_balance = None

    def generate_txn_ids(self):
        """

        Generates transactions id's for those transactions which do not have them


        """

        duplicates = {}
        assert self.transactions

        for transaction in self.transactions:
            # only generate transaction ids if there is no unique identifier scraped from bank
            if hasattr(transaction, 'fi_txn_id'):
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

            transaction.fi_txn_id = trnhash + '/' + str(duplicates[trnhash])


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
    reservation = False
    refnum = None

    # @property
    # def datePosted(self, datePosted):
    #     datePosted

    def __init__(self, date, **kwargs):
        self.date = date

        # Pass the optional attributes
        for kw in kwargs.keys():
            self.__setattr__(kw, kwargs[kw])


    def __str__(self):
        return "%s:%s:%s:%s:%s:%s (%s)" % (self.date, self.name, self.memo, self.type, self.amount, self.refnum, self.fi_txn_id)
