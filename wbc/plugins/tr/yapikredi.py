# -*- coding: utf-8 -*-
"""
Web-bank-connect for Yapi Kredi Bank Turkey


Author: Alex Yushin <alexis@ww.net>

"""

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

from wbc.plugins.base import Plugin
from wbc.models import Statement, Transaction, Account, Balance, transactionType, NEVER
from selenium.common.exceptions import NoSuchElementException

import re

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from datetime import datetime

from time import sleep

class Plugin(Plugin):
    LOGIN_URL = 'https://internetsube.yapikredi.com.tr/ngi/index.do?lang=en'
    DEFAULT_TIMEOUT = 15
    CLICK_LONG_SLEEP = 3

    def login(self, username, password):
        self.open_browser()

        self.driver.get(self.LOGIN_URL)

        # Wait for the username and type it in...
        self.locate((By.ID, 'userCodeTCKN')).send_keys(username)
        self.locate((By.ID, 'password')).send_keys(password)
        self.locate((By.ID, 'btnSubmit')).click()


        # Get the auth code from the user and send it together with the 'pin'...
        auth_code = ''
        while not re.match('\d{5}', auth_code):
            auth_code = self.user_input("Please enter the 5 digit OTP:\n")

        self.locate((By.ID, 'otpPassword')).send_keys(auth_code)
        self.locate((By.ID, 'btnSubmit')).click()

        self.locate((By.LINK_TEXT,"MY ACCOUNTS"), wait = self.LOGIN_TIMEOUT)
        self.logged_in = True

    def navigate_current_accounts(self):
        logger.debug('Navigating to accounts list..')
        self.locate((By.LINK_TEXT, "MY ACCOUNTS")).click()
        sleep(self.CLICK_SLEEP)
        self.locate((By.LINK_TEXT, "My Current Accounts")).click()
        sleep(self.CLICK_LONG_SLEEP)

    #
    # List the accounts online
    #
    def list_accounts(self):
        accounts = []

        self.navigate_current_accounts()

        accounts_table = self.locate_all((By.XPATH, "//table[@class='dataTable']"))

        for tr in accounts_table.find_elements_by_css_selector('tbody tr'):
            (td_check, td_name, td_balance, td_limit, td_avail) = tr.find_elements_by_tag_name('td')
            account_div = td_name.find_element_by_class_name('module-account')
            account = Account(
                type        =   'current',
                name        =   account_div.find_element_by_tag_name('h1').text,
                currency    =   '???'
            )
            account.closing_balance = Balance(
                amount      = float(account_data[2].text.encode('utf-8').replace('.', '').replace(',','.').replace('€ ','')),
                date        = datetime.utcnow().date()
            )
            accounts.append(account)

        return accounts

    def download_current(self, account):

        if not account.last_download:
            account.last_download = NEVER

        self.navigate_current_accounts()

        self.locate((By.XPATH,
            "//div[@class='module-account']"
            + "/h1[@title='" + account.name + "']/../../..")
        ).click()

        self.locate((By.LINK_TEXT, 'Account Movements')).click()
        self.locate((By.LINK_TEXT, 'Detailed Search')).click()

        startDate = self.locate((By.ID, 'startDate'))
        startDate.clear()
        startDate.send_keys(account.last_download.strftime("%d/%m/%Y"))

        # This is necessary to trigger an update of the javascript selector...
        self.driver.find_element_by_id('startDateFC').\
            find_element_by_css_selector('img.ui-datepicker-trigger').click()
        self.driver.find_element_by_id('btnList').click()
        sleep(self.CLICK_SLEEP)

        statement = Statement(account = account)

        # The amount regular expression...
        amount_p = re.compile('([-+,.\d]+)\s(\w{2,3})')

        # Plan A
        tr = self.locate((By.CSS_SELECTOR, 'div.table-wrapper table tbody tr'))
        prev_tr = None

        while True:
            td = tr.find_elements_by_tag_name('td')
            # Empty list?
            if 'dataTables_empty' in td[0].get_attribute('class'):
                break

            # More rows?
            if 'getMore_row' in td[0].get_attribute('class'):
                if td[0].is_displayed():
                    tr.find_element_by_id('btnGetMore').click()
                    self.wait().until_not(self.element_is_displayed(tr))
                else:
                    # No more rows?
                    break
            else:
                transaction = Transaction(
                    date    = datetime.strptime(td[1].text.encode('utf-8'), '%d/%m/%Y'),
                    name    = td[4].text,
                    memo    = td[4].text,
                    amount  = float(amount_p.match(td[5].text).group(1).replace('.','').replace(',','.'))
                )

                if(transaction.amount > 0):
                    transaction.type = transactionType.CREDIT
                else:
                    transaction.type = transactionType.DEBIT

                statement.transactions.append(transaction)

                # Save this tr as prev_tr...
                prev_tr = tr
            try:
                tr = prev_tr.find_element_by_xpath('following-sibling::tr')
            except NoSuchElementException:
                # No more rows...
                break

        return statement.finalize()

    def logout(self):
        pass