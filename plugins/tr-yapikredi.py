# -*- coding: utf-8 -*-
"""
Web-bank-connect for Yapi Kredi Bank Turkey

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
        auth_code = input("Please enter the auth code:\n")
        elem = self.driver.find_element_by_id('otpPassword')
        elem.send_keys(auth_code)
        self.driver.find_element_by_id('btnSubmit').click()