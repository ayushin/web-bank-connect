# -*- coding: utf-8 -*-
"""
Web-bank-connect for ING NL


Author: Alex Yushin <alexis@ww.net>

"""

import re
from datetime import date, datetime

from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException,TimeoutException,ElementNotVisibleException

from wbc.wbc import Connector

from pprint import pformat

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

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
        logger.info('Loggin in...')

        self.open_browser()
        logger.debug('Navigating to %s...' % self.login_url)
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
    #
    #   Scraping of the credit card
    #
    #   At this point multiple credit cards are not supported
    #
    #
    def scrape_ccard(self, account, datefrom):
        # Download credit card statement
        logger.debug('Navigating to %s...', self.creditcard_url)
        self.driver.get(self.creditcard_url)

        transactions = []

        # We keep on clicking on "previous period" until we reach the datefrom or the very first statement available
        while True:
            # get all the lines of the current period
            for tr in self.driver.find_elements_by_xpath("//div[@id='statementDetailTable']/div/div[@class='riaf-datatable-canvas']/table/tbody/tr[@class='riaf-datatable-contents ']"):
                logger.debug('transaction:\n%s' % tr.text)
                # Date of this transaction
                line= {
                    'date' : datetime.strptime(tr.find_element_by_class_name("riaf-datatable-column-date").text,'%d-%m-%Y').date(),
                    'amount' : float(tr.find_element_by_class_name("riaf-datatable-column-amount").text.replace('.','').replace(',','.'))}

                # Should we continue ?
                if datefrom and line['date'] < datefrom:
                    return transactions

                # Is this a reservation?
                if tr.find_element_by_class_name("riaf-datatable-column-first").text == '*':
                    line['reservation'] = True


                # Initialize amount and transaction type
                if tr.find_element_by_class_name("riaf-datatable-column-last").find_element_by_xpath('span').get_attribute("class") == 'riaf-datatable-icon-crdb-db' :
                    line['type'] = 'DEBIT'
                    line['amount'] = -line['amount']
                elif tr.find_element_by_class_name("riaf-datatable-column-last").find_element_by_xpath('span').get_attribute("class") == 'riaf-datatable-icon-crdb-cr' :
                    line['type'] = 'CREDIT'
                else:
                    raise ValueError('No sign for transaction')

                line['name'] = tr.find_elements_by_class_name("riaf-datatable-column-text")[0].text.encode('utf-8')

                # Get the memo...
                tr.click()
                tr_details = tr.find_element_by_xpath("following-sibling::tr[@class='riaf-datatable-details-open']")
                logger.debug('details row:\n %s' % tr_details.text)

                # XXX We could consider beautifying below...
                line['memo'] = tr_details.find_elements_by_class_name("riaf-datatable-details-contents")[0].text.encode('utf-8')

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

            self.parse_td_descr(td_descr, line)

            logger.debug("appening transaction:\n%s" % pformat(line))
            transactions.append(line)

        return transactions

    def parse_td_descr(self, td_descr, line):
        logger.debug("parsing transaction description:\n%s" % td_descr.text)

        (line1, line2, all_data) = td_descr.find_elements_by_xpath('div')
        line['name'] = line1.text.encode('utf-8').strip() + line2.text.encode('utf-8').strip()
        line['memo'] = ""

        for div in all_data.find_elements_by_xpath('div'):
            div_class = div.get_attribute('class')

            if div_class == 'clearfix':
                line['memo'] += "\n"
            elif 'l-w-30' in div_class:
                line['memo'] += div.text.encode('utf-8').strip() + ': '
            elif 'l-w-70' in div_class:
                line['memo'] += div.text.encode('utf-8').strip()
            else:
                logger.debug('found an unexpected div %s in the transaction data - skipping' % div_class)

    def logout(self):
        # keep the browser open for the development
        return

    #
    #
    # Return the list of the current accounts
    #
    #
    def list_accounts(self):
        accounts = []
        logger.info("Navigating to %s", self.accounts_url)
        self.driver.get(self.accounts_url)

        accounts_ol = self.driver.find_element_by_xpath("//div[@id='accounts']/div/div/ol")
        # Expand...
        while True:
            showMore = accounts_ol.find_element_by_id('accountslider')
            if showMore.is_displayed():
                showMore.click()
            else:
                break

        # Get the list of current accounts
        for account_li in accounts_ol.find_elements_by_tag_name('li'):
            logger.debug("found %s" % account_li.text)

            # We skip the "accountslider" and "totalBalance" items...
            if account_li.get_attribute('id') in ('accountslider', 'totalBalance'):
                continue

            account_data = account_li.find_elements_by_xpath('a/div')
            account = {
                'type'          :   'current',
                'name'          :   account_data[1].text.encode('utf-8'),
                'owner'         :   account_data[0].text.encode('utf-8'),
                'balance'       :   {
                    'amount'    :   float(account_data[2].text.encode('utf-8').replace('.', '').replace(',','.').replace('€ ','')),
                    'date'      :   datetime.utcnow().date()
                }
            }

            accounts.append(account)

        # # Check if we have a credit card...
        # logger.info("Navigating to %s", self.creditcard_url)
        # self.driver.get(self.creditcard_url)
        #
        # self.driver.find_element_by_id('cards_selector').click()
        #
        # credit_cards_tbody = self.driver.find_element_by_xpath(
        #     "//form[@id='cards_selector_form']/div/div/div/span/div/div/div[@class='riaf-popup']/div/table/tbody")
        #
        #
        # account = {
        #     'type'  : 'ccard',
        #     'name'  : credit_cards_tbody.find_element_by_xpath("tr/td/div/span[@class='riaf-listrenderer-account--accountnumber']").text.encode('utf-8'),
        #     'owner'  : credit_cards_tbody.find_element_by_xpath("tr/td/div/span[@class='riaf-listrenderer-account--accountname']").text.encode('utf-8'),
        #     'balance': {
        #         'amount'    : float(credit_cards_tbody.find_element_by_xpath("tr/td[@class='riaf-listrenderer-account--amount']").text.encode('utf-8').replace('.', '').replace(',','.').replace('€ ','')),
        #         'date'      : datetime.utcnow().date()
        #     }
        #
        # }
        # accounts.append(account)

        return accounts