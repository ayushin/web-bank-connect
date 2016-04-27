# -*- coding: utf-8 -*-
"""
Web-bank-connect for Yapi Kredi Bank Turkey


Author: Alex Yushin <alexis@ww.net>

"""

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


from wbc import Connector

import re

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from datetime import datetime

from time import sleep

class Plugin(Connector):
    LOGIN_URL = 'https://internetsube.yapikredi.com.tr/ngi/index.do?lang=en'
    CLICK_TIMEOUT = 3
    LOGIN_TIMEOUT = 60

    def login(self, username, password):
        self.open_browser()

        # self.driver.implicitly_wait(self.LOGIN_TIMEOUT)

        self.driver.get(self.LOGIN_URL)
        assert u"Yapı Kredi" in self.driver.title

        # Wait for the username and type it in...
        elem = self.driver.find_element_by_id('userCodeTCKN')
        elem.send_keys(username)

        elem = self.driver.find_element_by_id('password')
        elem.send_keys(password)

        self.driver.find_element_by_id('btnSubmit').click()

        # Get the auth code from the user and send it together with the 'pin'...
        # auth_code = raw_input("Please enter the auth code:\n")
        # elem = self.driver.find_element_by_id('otpPassword')
        # elem.send_keys(auth_code)
        # self.driver.find_element_by_id('btnSubmit').click()


        # Wait until the home page loads...
        WebDriverWait(self.driver, self.LOGIN_TIMEOUT).\
            until(EC.presence_of_element_located((By.LINK_TEXT,"MY ACCOUNTS")))

    def wait_and_click(self, link_text):
        WebDriverWait(self.driver, self.CLICK_TIMEOUT).\
        until(EC.presence_of_element_located((By.LINK_TEXT,link_text))).click()

    #
    #
    # List the accounts online
    #
    #
    # def list_accounts(self):
    #     accounts = []
    #
    #     logger.debug('Navigating to accounts list..')
    #     self.driver.find_element_by_link_text("MY ACCOUNTS").click()
    #     self.wait_and_find_link_text("My Current Accounts").click()
    #
    #     accounts_table = self.driver.find_element_by_xpath("//table[@class='dataTable']")
    #
    #     for account_tr in accounts_table.find_elements_by_xpath('tbody/tr'):
    #         (td_check, td_name, td_balance, td_limit, td_avail) = account_tr.find_elements_by_xpath('td')
    #         account_div = td_name.find_element_by_class_name('module-account')
    #         account = {
    #             'type'          :   'current',
    #             'name'          :   account_div.find_element_by_tag_name('h1').text.encode('utf-8'),
    #             # 'balance'       :   {
    #             #     'amount'    :   float(account_data[2].text.encode('utf-8').replace('.', '').replace(',','.').replace('€ ','')),
    #             #     'date'      :   datetime.utcnow().date()
    #             #}
    #         }
    #         accounts.append(account)
    #
    #     return accounts

    def scrape_current(self, account, datefrom, currency=None):
        logger.debug('Navigating to the account movements..')

        assert datefrom

        # self.driver.implicitly_wait(self.CLICK_TIMEOUT)
        self.wait_and_click("MY ACCOUNTS")
        self.wait_and_click("My Current Accounts")
        sleep(1)

        self.driver.find_element_by_xpath(
            "//div[@class='table-wrapper']/table/tbody/tr/td/div[@class='module-account']"
            + "/h1[@title='" + account + "']/../../..").click()

        self.wait_and_click('Account Movements')
        self.wait_and_click('Detailed Search')

        startDate = self.driver.find_element_by_id('startDate')
        startDate.clear()
        startDate.send_keys(datefrom.strftime("%d/%m/%Y"))
        self.driver.find_element_by_id('startDateFC').\
            find_element_by_css_selector('img.ui-datepicker-trigger').click()
        self.driver.find_element_by_id('btnList').click()
        sleep(2)

        transactions = []
        # # Plan A
        # for tr in self.driver.find_elements_by_css_selector('div.table-wrapper table tbody tr'):
        #     # Get the row of td elements...
        #     td = tr.find_elements_by_tag_name('td')
        #
        #     # If we reached the last line.. Get more
        #     if 'getMore_row' in td[0].get_attribute('class') and td[0].is_displayed():
        #         td[0].find_element_by_id('btnGetMore').click()
        #         continue
        #
        #     logger.debug('transaction: %s' % tr.text)

        # Plan B
        while True:
            getMoreRow = self.driver.find_elements_by_css_selector('div.table-wrapper table tbody tr td.getMore_row')
            if getMoreRow and getMoreRow[0].is_displayed():
                element_id = getMoreRow[0].find_element_by_xpath('..').id
                getMoreRow[0].click()
                while self.driver.find_elements_by_id(element_id):
                    sleep(1)
                sleep(5) # Should check Please wait longer mesage.
            else:
                break

        # The amount regular expression...
        amount_p = re.compile('([-+,.\d]+)\s(\w{2,3})')

        for tr in self.driver.find_elements_by_css_selector('div.table-wrapper table tbody tr'):
            td = tr.find_elements_by_tag_name('td')

            #if 'getMore_row' in td[0].get_attribute('class'):
            #    continue

            logger.debug('# %s' % tr.text)

            line = {
                'date': datetime.strptime(td[1].text.encode('utf-8'), '%d/%m/%Y'),
                'name': td[4].text,
                'memo': td[4].text,
                'amount': float(amount_p.match(td[5].text.encode('utf-8')).group(1).replace('.','').replace(',','.')),
            }
            if(line['amount'] > 0):
                line['type'] = 'CREDIT'
            else:
                line['type'] = 'DEBIT'

            transactions.append(line)

        return transactions

    def logout(self):
        pass