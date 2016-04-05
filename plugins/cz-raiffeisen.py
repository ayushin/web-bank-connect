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
        alert = self.driver.switch_to_alert()
        alert.accept()

        # Get the auth code from the user and send it together with the 'pin'...
        auth_code = input("Please enter the auth code:\n")
        elem = self.driver.find_element_by_name("a_userpassword")
        elem.send_keys(auth_code)
        elem = self.driver.find_element_by_name("Pin")
        elem.send_keys(password)

        # Click OK to log in
        self.driver.find_element_by_name("b_ok_Button").click()

