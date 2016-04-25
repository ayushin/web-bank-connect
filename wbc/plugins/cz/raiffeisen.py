# -*- coding: utf-8 -*-
"""
Web-bank-connect for Raiffeisen Bank CZ

http://mijn.ing.nl

Author: Alex Yushin <alexis@ww.net>

"""

from wbc.plugins.base import Plugin
from wbc.models import Account, Statement, Transaction, transactionType

from datetime import datetime, date, timedelta
import re

from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException,TimeoutException,ElementNotVisibleException
from datetime import date, datetime

from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys

from time import sleep

from pprint import pformat

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Plugin(Plugin):
    CLICK_WAIT = 3
    CLICK_SLEEP = 1
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
        elem_xpath = "//input[@name='a_username' and @type='text']"
        WebDriverWait(self.driver, self.CLICK_WAIT).until(EC.visibility_of_element_located((By.XPATH, elem_xpath)))
        elem = self.driver.find_element_by_xpath(elem_xpath)
        elem.send_keys(username)

        # Open the certification prompt box and accept it...
        self.driver.find_element_by_name("b_authcode_Button").click()
        WebDriverWait(self.driver, self.CLICK_WAIT).until(EC.alert_is_present())
        self.driver.switch_to.alert.accept()

        # Get the auth code from the user and send it together with the 'pin'...
        auth_code = ''
        while not re.match('\d{11}', auth_code):
            auth_code = self.user_input_method("Please enter the 11 digit auth code without dashes:\n")

        elem = self.driver.find_element_by_name("a_userpassword")
        elem.send_keys(auth_code)
        elem = self.driver.find_element_by_name("Pin")
        elem.send_keys(password)

        # Click OK to log in
        self.driver.find_element_by_name("b_ok_Button").click()

        # Wait for the MainMenu to appear...
        self.driver.switch_to.default_content()
        WebDriverWait(self.driver, self.LOGIN_TIMEOUT).until(EC.frame_to_be_available_and_switch_to_it('MainMenu'))
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

    def choose_account(self, account):
        """
        A helper function to select an account specified by 'account' and 'currency' pair

        :return: None
        """
        self.driver.switch_to.default_content()
        self.driver.switch_to.frame('Choice')
        for account_option in WebDriverWait(self.driver, self.CLICK_WAIT).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'select[name="a_account"] option'))):
            if account_option.text.encode('utf-8') == account.name:
                account_option.click()
                sleep(1)
                for currency_option in WebDriverWait(self.driver, self.CLICK_WAIT).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'select[name="a_currency"] option'))):
                    if currency_option.text.encode('utf-8') == account.currency:
                        currency_option.click()
                        sleep(1)
                        self.driver.switch_to.default_content()
                        return
        raise ValueError('Not found account %s currency %s' % (account.name, account.currency))


    def download_current(self, account):

        # Navigate to the correct account...
        self.choose_account(account)
        self.driver.switch_to.default_content()
        self.driver.switch_to.frame('MainMenu')

        # Select account history, account movements
        account_history = self.driver.find_element_by_css_selector('table tbody tr#MainMenu1')
        account_history.click()
        account_movements = self.driver.find_element_by_css_selector('table tbody td table#SubMenu1 tbody tr td table tbody tr td')
        assert "Account movements" in account_movements.text.encode('utf-8')
        account_movements.click()

        # Switch back to the default frame
        self.driver.switch_to.default_content()
        self.driver.switch_to.frame('Main')

        # XXX We should make sure we select -370 transaction in the filter

        statement = Statement()

        # Scrape the account...
        while True:
            for tr in WebDriverWait(self.driver, self.CLICK_WAIT).until(
                EC.presence_of_all_elements_located((
                        By.CSS_SELECTOR, 'form[name="ListRealTr"] table tbody tr td table tbody tr'))):

                cols = tr.find_elements_by_css_selector('td font')
                logger.debug('found statement line:\n%s' % tr.text)

                # Skip the header...
                if cols[0].text == u"NO.\nNUMBER":
                    continue

                # We have reached teh end
                if  u"TOTAL OF SELECTED CREDIT ITEMS" in cols[0].text:
                    return statement.finalize()

                col = {'no': int(cols[0].text.encode('utf-8'))}

                (col['date'], col['time'], col_dummy) = cols[1].get_attribute('innerHTML').encode('utf-8').split('<br>')
                (col['note'], col['account_name'], col['account_number']) = cols[2].get_attribute('innerHTML').split('<br>')
                (col['date_deducted'], col['value'], col['type'], col['code']) = cols[3].get_attribute('innerHTML').encode('utf-8').split('<br>')
                (col['variable_symbol'], col['constant_symbol'], col['specific_symbol'])= cols[4].get_attribute('innerHTML').replace('&nbsp;','').split('<br>')

                col['amount'] = cols[5].text.encode('utf-8').split('\n')[0].replace(' ','').replace(',','.')
                col['fee']  = cols[6].text.encode('utf-8').replace(' ','').replace(',','.')
                col['exchange'] = cols[7].text.encode('utf-8').replace(' ','').replace(',','.')
                col['message'] = cols[8].text.encode('utf-8').replace(' ','').replace(',','.')

                transaction = Transaction(
                    date = datetime.strptime(col['date'],'%d.%m.%Y').date(),
                    name =  col['note'] or col['account_name'] or col['account_number'],
                    memo =  col['note'] + '\n' + col['account_name'] + '\n' + col['account_number'] + '\n'  + col['type'] + '\n' + col['variable_symbol'] + '/' + col['constant_symbol'] + '/' + col['specific_symbol'],
                    refnum =  col['code']
                )

                if account.last_download and transaction.date < account.last_download.date():
                    return statement.finalize()

                # XXX Figure out the transaction type

                if col['amount']:
                    transaction.amount = float(col['amount'])

                    if transaction.amount > 0:
                        transaction.type = transactionType.CREDIT
                    else:
                        transaction.type = transactionType.DEBIT

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

                statement.transactions.append(transaction)

            self.driver.find_element_by_css_selector('a[href="javascript:top.Common.v_SubList.Next(1);"]').click()
            sleep(self.CLICK_SLEEP)