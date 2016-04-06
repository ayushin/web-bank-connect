# -*- coding: utf-8 -*-
"""
Web-bank-connect for Yapi Kredi Bank Turkey


Author: Alex Yushin <alexis@ww.net>

"""

from pprint import pformat

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


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


class Plugin(Connector):
    login_url = 'https://internetsube.yapikredi.com.tr/ngi/index.do?lang=en'

    def login(self, username, password):
        self.open_browser()
        self.driver.get(self.login_url)
        assert u"Yapı Kredi" in self.driver.title

        # Wait for the username and type it in...
        elem = self.driver.find_element_by_id('userCodeTCKN')
        elem.send_keys(username)

        elem = self.driver.find_element_by_id('password')
        elem.send_keys(password)

        self.driver.find_element_by_id('btnSubmit').click()

        # Get the auth code from the user and send it together with the 'pin'...
        auth_code = raw_input("Please enter the auth code:\n")
        elem = self.driver.find_element_by_id('otpPassword')
        elem.send_keys(auth_code)
        self.driver.find_element_by_id('btnSubmit').click()

        assert 'Kredi' in self.driver.title




    #
    #
    # List the accounts online
    #
    #
    def list_accounts(self):
        accounts = []

        logger.debug('Navigating to accounts list..')
        self.driver.find_element_by_xpath("//div[@id='boxData0_0']/div/div/a/img").click()

        accounts_table = self.driver.find_element_by_xpath("//table[@class='dataTable']")

        for account_tr in accounts_table.find_elements_by_xpath('tbody/tr'):
            (td_check, td_name, td_balance, td_limit, td_avail) = account_tr.find_elements_by_xpath('td')
            account_div = td_name.find_element_by_class_name('module-account')
            account = {
                'type'          :   'current',
                'name'          :   account_div.find_element_by_tag_name('h1').text.encode('utf-8'),
                # 'balance'       :   {
                #     'amount'    :   float(account_data[2].text.encode('utf-8').replace('.', '').replace(',','.').replace('€ ','')),
                #     'date'      :   datetime.utcnow().date()
                #}
            }
            accounts.append(account)

        return accounts

    def scrape_current(self, account, datefrom):
        logger.debug('Navigating to account movements..')
        # Home page...
        #self.driver.find_element_by_xpath("//div[@id='main-nav']/ul/li/a").click()
        # Default account...
        self.driver.find_element_by_xpath("//div[@id='boxData0_0']/div/div/a/img").click()
        #
        self.driver.find_element_by_xpath("//table[@class='dataTable']/tbody/tr/td/div/h1[@title='Current Account USD']").click()
        self.driver.find_element_by_link_text('Account Movements').click()

        # self.driver.find_element_by_id('s2id_selAccIdx').click()



    def logout(self):
        pass