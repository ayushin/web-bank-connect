# -*- coding: utf-8 -*-
"""
Web-bank-connect for Raiffeisen Bank CZ

http://mijn.ing.nl

Author: Alex Yushin <alexis@ww.net>

"""

from wbc.wbc import Connector

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


class Plugin(Connector):
    login_url = 'https://klient1.rb.cz/ebts/version_02/eng/banka3.html'

    def login(self, username, password):
        self.open_browser()
        self.driver.get(self.login_url)

        # Get the main frame...
        self.driver.switch_to.frame('Main')

        # Wait for the username and type it in...
        elem_xpath = "//input[@name='a_username' and @type='text']"
        WebDriverWait(self.driver, 3).until(EC.visibility_of_element_located((By.XPATH, elem_xpath)))
        elem = self.driver.find_element_by_xpath(elem_xpath)
        elem.send_keys(username)

        # Open the certification prompt box and accept it...
        self.driver.find_element_by_name("b_authcode_Button").click()
        WebDriverWait(self.driver, 3).until(EC.alert_is_present())
        self.driver.switch_to.alert.accept()

        # Get the auth code from the user and send it together with the 'pin'...
        auth_code = input("Please enter the auth code:\n")
        elem = self.driver.find_element_by_name("a_userpassword")
        elem.send_keys(auth_code)
        elem = self.driver.find_element_by_name("Pin")
        elem.send_keys(password)

        # Click OK to log in
        self.driver.find_element_by_name("b_ok_Button").click()

    def list_accounts(self):
        self.driver.switch_to.default_content()
        self.driver.switch_to.frame('Choice')

        accounts = []

        for account_option in self.driver.find_elements_by_css_selector('select[name="a_account"] option'):
            account_option.click()
            WebDriverWait(self.driver, 3)
            for currency_option in self.driver.find_elements_by_css_selector('select[name="a_currency"] option'):
                accounts.append({
                    'name': account_option.text.encode('utf-8'),
                    'type': 'current',
                    'currency' : currency_option.text.encode('utf-8')
                })

        return accounts

    def choose_account(self, account, currency):
        self.driver.switch_to.default_content()
        self.driver.switch_to.frame('Choice')
        for account_option in self.driver.find_elements_by_css_selector('select[name="a_account"] option'):
            if account_option.text.encode('utf-8') == account:
                account_option.click()
                WebDriverWait(self.driver, 3)
                for currency_option in self.driver.find_elements_by_css_selector('select[name="a_currency"] option'):
                    if currency_option.text.encode('utf-8') == currency:
                        currency_option.click()
                        WebDriverWait(self.driver, 3)
                        self.driver.switch_to.default_content()
                        return
        raise ValueError('Not found account %s currency %s' % (account, currency))


    def scrape_current(self, account, datefrom, currency):
        # Navigate to the correct account...
        self.choose_account(account, currency)
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

        transactions = []
        # Scrape the account...
        while True:
            for tr in self.driver.find_elements_by_css_selector('form[name="ListRealTr"] table tbody tr td table tbody tr'):
                cols = tr.find_elements_by_css_selector('td font')
                logger.debug('found statement line:\n%s' % tr.text)
                if cols[0].text.encode('utf-8') == 'NO.\nNUMBER':
                    continue

                if  'TOTAL OF SELECTED CREDIT ITEMS' in cols[0].text.encode('utf-8'):
                    return transactions

                col = {'no': int(cols[0].text.encode('utf-8'))}

                (col['date'], col['time'], col_dummy) = cols[1].get_attribute('innerHTML').encode('utf-8').split('<br>')
                (col['note'], col['account_name'], col['account_number']) = cols[2].get_attribute('innerHTML').encode('utf-8').split('<br>')
                (col['date_deducted'], col['value'], col['type'], col['code']) = cols[3].get_attribute('innerHTML').encode('utf-8').split('<br>')
                (col['variable_symbol'], col['constant_symbol'], col['specific_symbol'])= cols[4].get_attribute('innerHTML').encode('utf-8').split('<br>')
                col['amount'] = cols[5].text.encode('utf-8').split('\n')[0].replace(' ','').replace(',','.')
                col['fee']  = cols[6].text.encode('utf-8').replace(' ','').replace(',','.')
                col['exchange'] = cols[7].text.encode('utf-8').replace(' ','').replace(',','.')
                col['message'] = cols[8].text.encode('utf-8')

                line = {
                    'date': datetime.strptime(col['date'],'%d.%m.%Y').date(),
                    'name': col['note'] or col['account_name'] or col['account_number'],
                    'memo': col['note'] + '\n' + col['account_name'] + '\n' + col['account_number'] + '\n'  + col['type'] + '\n' + col['variable_symbol'] + '/' + col['constant_symbol'] + '/' + col['specific_symbol'],
                    'refnum': col['code']
                }

                if datefrom and line['date'] < datefrom:
                    return transactions

                # Figure out the transaction type
                # Figure out amount or fee
              #'amount' : float(tr.find_element_by_class_name("riaf-datatable-column-amount").text.replace('.','').replace(',','.'))}

                transactions.append(line)

            self.driver.find_element_by_css_selector('a[href="javascript:top.Common.v_SubList.Next(1);"]').click()
