# -*- coding: utf-8 -*-
"""
Web-bank-connect for Raiffeisen Bank CZ

http://mijn.ing.nl

Author: Alex Yushin <alexis@ww.net>

TODO:

    - actually select -370 days in the period of account movements

"""

from wbc.plugins.base import Plugin
from wbc.models import Account, Statement, Transaction, transactionType

import re

from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from datetime import datetime

from time import sleep

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Plugin(Plugin):
    CLICK_SLEEP = 1
    DEFAULT_TIMEOUT = 3
    LOGIN_TIMEOUT = 15
    LOGIN_URL = 'https://klient1.rb.cz/ebts/version_02/eng/banka3.html'

    def logout(self):
        pass


    def login(self, username, password):
        self.open_browser()
        self.driver.get(self.LOGIN_URL)

        # Get the main frame...
        self.driver.switch_to.frame('Main')

        # Wait for the username and type it in...
        self.locate(
            (By.XPATH, "//input[@name='a_username' and @type='text']")
        ).send_keys(username)

        # Open the certification prompt box and accept it...
        self.locate((By.NAME, "b_authcode_Button")).click()
        self.wait().until(EC.alert_is_present())
        self.driver.switch_to.alert.accept()

        # Get the auth code from the user and send it together with the 'pin'...
        auth_code = ''
        while not re.match('\d{11}', auth_code):
            auth_code = self.user_input("Please enter 11 digit auth code without dashes:\n")

        self.locate((By.NAME, "a_userpassword")).send_keys(auth_code)
        self.locate((By.NAME, "Pin")).send_keys(password)

        # Click OK to log in
        self.locate((By.NAME, "b_ok_Button")).click()

        # Wait for the MainMenu to appear...
        self.driver.switch_to.default_content()
        self.wait(wait = self.LOGIN_TIMEOUT).until(
            EC.frame_to_be_available_and_switch_to_it('MainMenu'))

        self.logged_in = True

    def list_accounts(self):
        self.driver.switch_to.default_content()
        self.driver.switch_to.frame('Choice')

        accounts = []

        for account_option in self.driver.find_elements_by_css_selector('select[name="a_account"] option'):
            account_option.click()
            sleep(1)

            for currency_option in self.driver.find_elements_by_css_selector('select[name="a_currency"] option'):
                accounts.append(Account(
                    name =  account_option.text,
                    type = 'current',
                    currency =  currency_option.text
                ))

        return accounts



    def download_current(self, account):
        # Choose the specified account...
        self.driver.switch_to.default_content()
        self.driver.switch_to.frame('Choice')
        # try
        self.locate((By.XPATH, "//select[@name='a_account']/option[contains(.,'" + account.name + "')]")).click()
        sleep(self.CLICK_SLEEP)
        self.locate((By.XPATH, "//select[@name='a_currency']/option[contains(.,'" + account.currency + "')]")).click()
        sleep(self.CLICK_SLEEP)
        #raise ValueError('No account named %s in %s currency found' % (account.name, account.currency))

        # Select account history, account movements
        self.driver.switch_to.default_content()
        self.driver.switch_to.frame('MainMenu')
        self.locate((By.XPATH, u"//td[@class='MainMenu'][contains(., 'ACCOUNT\u00A0HISTORY')]")).click()
        self.locate((By.XPATH, u"//td[@class='submenu_low'][contains(., 'Account movements')]")).click()
        sleep(self.CLICK_SLEEP)

        # Switch back to the default frame
        self.driver.switch_to.default_content()
        self.driver.switch_to.frame('Main')

        # XXX We should make sure we select -370 transaction in the filter
        self.locate((By.XPATH, "//select[@name='CBRealTrFilters']/option[contains(.,'last 370 days')]")).click()
        sleep(self.CLICK_SLEEP)
        # self.locate((By.CSS_SELECTOR, 'a[href="javascript:top.Program.ShowRealTrFilter();"]')).click()
        # sleep(self.CLICK_SLEEP)
        # elem = self.locate((By.CSS_SELECTOR, 'input[name="a_Name"]'))
        # elem.clear()
        # elem.send_keys("last 370 days")
        # elem = self.locate((By.CSS_SELECTOR, 'input[name="a_ValidFrom"]'))
        # elem.clear()
        # elem.send_keys('-370')
        # # Here we should clear all other fields too
        # self.locate((By.CSS_SELECTOR, 'a[href="javascript:top.Program.ShowRealTransactions();"]')).click()
        # sleep(self.CLICK_SLEEP)


        statement = Statement(account = account)

        # Known transaction types...
        transaction_types = {
            'Card payment'              :   transactionType.POS,
            'Enter transfer'            :   transactionType.XFER,
            'Card issue fee'            :   transactionType.FEE,
            'Repeating transfer'        :   transactionType.REPEATPMT,
            'Withdraw from ATM'         :   transactionType.ATM,
            'Outgoing payment'          :   transactionType.PAYMENT,
            'Enter reverse transfer'    :   transactionType.DIRECTDEBIT,
            'Cash deposit'              :   transactionType.DEP,
            'Administration of current account' :   transactionType.SRVCHG,
            'Withholding tax on interest'   : transactionType.OTHER,
            'Cash withdrawal'           : transactionType.CASH,
            'Currency conversion'       : transactionType.XFER,
            'ATM withdrawal while abroad': transactionType.ATM,
            'Outgoing SEPA payment':    transactionType.PAYMENT,
            'Credit interest'           : transactionType.INT,
            'Transfer'                  : transactionType.XFER,
            'Incoming SEPA payment'     : transactionType.PAYMENT
        }

        # Scrape the account...
        while True:
            for tr in self.locate_all(
                (By.CSS_SELECTOR, 'form[name="ListRealTr"] table tbody tr td table tbody tr')):

                logger.debug('found statement line:\n%s' % tr.text)
                cols = tr.find_elements_by_css_selector('td font')

                # Skip the header...
                if cols[0].text == u"NO.\nNUMBER":
                    continue

                # We have reached teh end
                if  u"TOTAL OF SELECTED CREDIT ITEMS" in cols[0].text:
                    return statement.finalize()

                col = {'no': int(cols[0].text)}

                (col['date'], col['time'], col_dummy) = cols[1].text.split("\n")
                (col['note'], col['account_name'], col['account_number']) = cols[2].get_attribute('innerHTML').replace('&nbsp;','').split('<br>')
                (col['date_deducted'], col['value'], col['type'], col['code']) = cols[3].get_attribute('innerHTML').split('<br>')
                (col['variable_symbol'], col['constant_symbol'], col['specific_symbol']) = cols[4].get_attribute('innerHTML').replace('&nbsp;','').split('<br>')

                col['amount'] = cols[5].text.split('\n')[0].replace(' ','').replace(',','.')
                col['fee']  = cols[6].text.replace(' ','').replace(',','.')
                col['exchange'] = cols[7].text.replace(' ','').replace(',','.')
                col['message'] = cols[8].text.replace(' ','').replace(',','.')

                transaction = Transaction(
                    date = datetime.strptime(col['date'],'%d.%m.%Y').date(),
                    memo = col['note'],
                    refnum =  col['code']
                )

                if account.last_download and transaction.date < account.last_download.date():
                    return statement.finalize()

                # Figure out the transaction type
                transaction.type = transaction_types.get(col['type'], None)

                if transaction.type == transactionType.POS:
                    transaction.name = col['note']
                    transaction.memo = (col['account_name'] + col['account_number']).strip()
                else:
                    transaction.name =  col['account_name'] or col['account_number'] or col['note']

                    # Construct a useful memo...
                    transaction.memo = col['note']
                    if col['account_name']:
                        transaction.memo += '/ ' + col['account_name']
                    if col['account_number']:
                        transaction.memo += ' [' + col['account_number'] + ']'

                if col['variable_symbol']:
                    transaction.memo += ' VS:' + col['variable_symbol']
                if col['constant_symbol']:
                    transaction.memo += ' CS:' + col['constant_symbol']
                if col['specific_symbol']:
                    transaction.memo += ' SS:' + col['specific_symbol']


                # Find out the correct amount and transaction type...
                if col['amount']:
                    transaction.amount = float(col['amount'])

                    if col['fee']:
                        statement.transactions.append(Transaction(
                            type    = transactionType.SRVCHG,
                            date    = transaction.date,
                            name    = 'Service charges',
                            memo    = 'Service charges for transaction %s' % transaction.refnum,
                            amount  = float(col['fee'])
                        ))

                    if col['exchange']:
                        statement.transactions.append(Transaction(
                            type    = transactionType.SRVCHG,
                            date    = transaction.date,
                            name    = 'Exchange fees',
                            memo    = 'Exchange fees for transaction %s' % transaction.refnum,
                            amount  = float(col['exchange'])
                        ))

                    if col['message']:
                        statement.transactions.append(Transaction(
                            type    = transactionType.SRVCHG,
                            date    = transaction.date,
                            name    = 'Operational fees',
                            memo    = 'Operational fees for transaction %s' % transaction.refnum,
                            amount  = float(col['message']),
                        ))
                else:
                    if col['fee']:
                        transaction.type    = transactionType.SRVCHG
                        transaction.amount  = float(col['fee'])
                    elif col['exchange']:
                        transaction.type    = transactionType.SRVCHG
                        transaction.amount  = float(col['exchange'])
                    elif col['message']:
                        transaction.type    = transactionType.SRVCHG
                        transaction.amount  = float(col['message'])
                    else:
                        raise ValueError('No amount neither service charge')

                    # Add the actual transaction type to the memo
                    transaction.memo   = (transaction.memo + ' ' + col['type']).strip()

                if not transaction.type:
                    if transaction.amount > 0:
                        transaction.type = transactionType.CREDIT
                        logger.warning('found unknown transaction type %s, using generic credit' % col['type'])
                    else:
                        transaction.type = transactionType.DEBIT
                        logger.warning('found unknown transaction type %s, using generic debit' % col['type'])

                statement.transactions.append(transaction)

            self.locate((By.CSS_SELECTOR, 'a[href="javascript:top.Common.v_SubList.Next(1);"]')).click()
            sleep(self.CLICK_SLEEP)
