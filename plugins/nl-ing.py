"""
Web-bank-connect for ING NL

http://mijn.ing.nl

Author: Alex Yushin <alexis@ww.net>

"""

from connector import Connector
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
    login_url = 'https://mijn.ing.nl/internetbankieren/SesamLoginServlet'
    accounts_url = 'https://bankieren.mijn.ing.nl/particulier/betalen/index'
    creditcard_url = 'https://bankieren.mijn.ing.nl/particulier/creditcard/saldo-overzicht/index'


    #
    #
    # Log-in
    #
    #
    def login(self, username, password):
        self.open_browser()
        self.driver.get(self.login_url)
        assert "ING" in self.driver.title

        elem = self.driver.find_element_by_xpath('//label[text()="Gebruikersnaam"]')
        elem.send_keys(username)
        elem = self.driver.find_element_by_xpath('//label[text()="Wachtwoord"]')
        elem.send_keys(password)
        self.driver.find_element_by_class_name('submit').click()

        assert "Mijn ING Overzicht - Mijn ING" in self.driver.title


    #
    #
    #   Scraping of the credit card
    #
    #
    #
    def scrape_ccard(self, account, datefrom):
        # Download credit card statement
        self.driver.get(self.creditcard_url)

        transactions = []

        # We keep on clicking on "previous period" until we reach the datefrom or the very first statement available
        while True:
            # get all the lines of the current period
            for tr in self.driver.find_elements_by_xpath("//div[@id='statementDetailTable']/div/div[@class='riaf-datatable-canvas']/table/tbody/tr[@class='riaf-datatable-contents ']"):
                # Date of this transaction
                line= {
                    'date' : datetime.strptime(tr.find_element_by_class_name("riaf-datatable-column-date").text,'%d-%m-%Y').date(),
                    'amount' : float(tr.find_element_by_class_name("riaf-datatable-column-amount").text.replace('.','').replace(',','.'))}

                # Should we continue ?
                if datefrom and line['date'] < datefrom:
                    return transactions

                # Initialize amount and transaction type
                if tr.find_element_by_class_name("riaf-datatable-column-last").find_element_by_xpath('span').get_attribute("class") == 'riaf-datatable-icon-crdb-db' :
                    line['type'] = 'DEBIT'
                    line['amount'] = -line['amount']
                elif tr.find_element_by_class_name("riaf-datatable-column-last").find_element_by_xpath('span').get_attribute("class") == 'riaf-datatable-icon-crdb-cr' :
                    line['type'] = 'CREDIT'
                else:
                    raise ValueError('No sign for transaction')

                line['name'] = line['memo'] = tr.find_elements_by_class_name("riaf-datatable-column-text")[0].text

                transactions.append(line)

            # Download previous credit card statement
            try:
                self.driver.find_element_by_id('previousPeriod').click()
            except NoSuchElementException:
                # Reached the very first period...
                return transactions

    #
    #
    #
    # Scraping current account
    #
    #
    #
    #

    # At first we expand the account up to the datefrom
    def expand_account(self, account, datefrom):
        # Navigate to the payment index page...
        self.driver.get(self.accounts_url)

        # Navigate to the account... Click
        self.driver.find_element_by_xpath("//div[@id='accounts']/div/div/ol/li/a/div[contains(text(), '" + account +"')]").click()

        # Wait until the new account started to load...
        try:
            WebDriverWait(self.driver, 3).until(EC.invisibility_of_element_located((By.XPATH,
                    "//table[@id='receivedTransactions']/thead/tr/th[contains(text(), 'Datum')]")))
        except TimeoutException:
            # Perhaps the bank was quick enough to download the required account or it was open already
            pass

        # And until it is loaded.
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH,
                    "//table[@id='receivedTransactions']/thead/tr/th[contains(text(), 'Datum')]")))

        # Expand all the statement lines until the date from or until there are no more statements
        while True:
            for tr in self.driver.find_elements_by_xpath("//table[@id='receivedTransactions']/tbody/tr"):
                # Have we already clicked on it?
                if tr.find_elements_by_class_name('ng-hide'):
                    tr.click()

                # Skip horizontal lines...
                if tr.find_elements_by_tag_name('hr'):
                    continue

                tr_date = datetime.strptime(tr.find_elements_by_tag_name('td')[0].text,'%d-%m-%Y').date()

                if datefrom and tr_date < datefrom:
                    return

            # Click to download more
            try:
                getMore = self.driver.find_element_by_id('getMore')
                showMore = self.driver.find_element_by_id('showMore')
                if getMore.is_displayed():
                    getMore.click()
                elif showMore.is_displayed():
                    showMore.click()
                else:
                    return

            except NoSuchElementException:
                # reached the end
                return

    # Actually scrape the statement transactions
    def scrape_current(self, account, datefrom = None):
        self.expand_account(account, datefrom)

        transactions = []

        # Scrape the transactions
        for tr in self.driver.find_elements_by_xpath("//table[@id='receivedTransactions']/tbody/tr"):

            print tr.text

            # Skip horizontal lines...
            if tr.find_elements_by_tag_name('hr'):
                continue

            (td_date, td_descr, td_type, td_amount) = tr.find_elements_by_tag_name('td')


            line = {
                'date' : datetime.strptime(td_date.text,'%d-%m-%Y').date(),
            }

            if datefrom and line['date'] < datefrom:
                return transactions

            m = re.match('([^\s]+)\s(Af|Bij)',td_amount.text)
            line['amount'] = float(m.group(1).replace('.','').replace(',','.'))

            if m.group(2) == 'Bij':
                line['type'] = 'CREDIT'
            elif m.group(2) == 'Af':
                line['amount'] = -line['amount']
                line['type'] = 'DEBIT'
            else:
                raise ValueError('No sign for transaction')

            #
            # XXX We should do some name and memo beautifying here
            #
            m = re.match('Naam:(.+)\n(.+)', td_descr.text)
            line['name'] = m.group(1)
            line['memo'] = td_descr.text

            transactions.append(line)

        return transactions

    def logout(self):
        # keep the browser open for the development
        return