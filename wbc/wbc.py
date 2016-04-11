#
#
# Author: Alex Yushin <alexis@ww.net>
#
#

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


from datetime import date
from hashlib import md5

import logging
logger = logging.getLogger(__name__)

# Transaction types from OFX 2.1.1 specification...
TRANSACTION_TYPES = (
    'CREDIT',       # Generic credit
    'DEBIT',        # Generic debit
    'INT',          # Interest earned or paid
    'DIV',          # Dividend
    'FEE',          # FI fee
    'SRVCHG',       # Service charge
    'DEP',          # Deposit
    'ATM',          # ATM debit or credit
    'POS',          # Point of sale debit or credit
    'XFER',         # Transfer
    'CHECK',        # Check
    'PAYMENT',      # Electronic payment
    'CASH',         # Cash withdrawal
    'DIRECTDEP',    # Direct deposit
    'DIRECTDEBIT',  # Merchant initiated debit
    'REPEATPMT',    # Repeating payment/standing order
    'OTHER',        # Other
)

# Definition of web bank connector
class Connector:
    def open_browser(self):
        self.driver = webdriver.Firefox()

        # XXX implicitly_wait is plugin dependent...
        #self.driver.implicitly_wait(3)

    def login(self, username, password):
        pass

    def scrape(self, account, datefrom):
        pass

    def list_accounts(self):
        pass

    def logout(self):
        self.close_browser()
        pass

    def close_browser(self):
        self.driver.quit()

    # def wait_and_find_link_text(self, link_text):
    #     return WebDriverWait(self.driver, self.CLICK_TIMEOUT).until(
    #         EC.presence_of_element_located((By.LINK_TEXT, link_text)))
    #
    # def wait_and_find_css_selector(self, selector_text):
    #     return WebDriverWait(self.driver, self.CLICK_TIMEOUT).until(
    #         EC.presence_of_element_located((By.CSS_SELECTOR, selector_text)))

def load_plugin(plugin_name):
    plugin  = 'plugins.' + plugin_name + '.Plugin'
    parts = plugin.split('.')
    module = ".".join(parts[:-1])
    m = __import__( module )
    for comp in parts[1:]:
        m = getattr(m, comp)
    return m()

#
# transaction = { 'date'        : '2016-01-01',
#                'name'         : 'name or payee',
#                'memo'         : 'transactino description',
#                'amount'       : 'transaction amount',
#                'type'         : 'DEBIT or CREDIT',
#                'refnum'       : 'unique transaction id either provided by bank or generated'
#

#
#
# Generates transactions id's for those transactions which do not have them
#
#
def generate_refnums(transactions):
    duplicates = {}

    if not transactions:
        return

    for transaction in transactions:
        # only generate transaction ids if there is no unique identifier scraped from bank
        if transaction.get('refnum'):
            continue

        trnhash = md5(str(transaction['date'])+transaction['name'].encode('utf-8') +
                      transaction['memo'].encode('utf-8') + transaction['type'] +
                      str(transaction['amount'])).hexdigest()

        if trnhash in duplicates.keys():
            duplicates[trnhash] += 1
            print "Found identical transaction on %s" % transaction['date']
        else:
            duplicates[trnhash] = 0

        transaction['refnum'] = trnhash + str(duplicates[trnhash])


#
#  Scrapes all the accounts of the given connections
#
def scrape_all(connections):
    statements = []

    for connection in connections:

        plugin = load_plugin(connection['plugin'])
        plugin.login(connection['username'], connection['password'])

        for account in connection['accounts']:
            transactions = getattr(plugin, 'scrape_' + account['type'])(account = account['name'],
                                        datefrom = account.get('lastupdate', date(1977,3,3)),
                                        currency = account.get('currency', None))

            generate_refnums(transactions)

            statements.append({'account': account,
                               'transactions': transactions})

        plugin.logout()

    return statements