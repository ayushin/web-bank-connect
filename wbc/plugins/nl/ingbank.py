# -*- coding: utf-8 -*-
"""
Web-bank-connect for ING NL


Author: Alex Yushin <alexis@ww.net>

"""

import re
from datetime import datetime
from pprint import pformat
import logging

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from time import sleep

from wbc.plugins.base import Plugin
from wbc.models import Statement, Transaction, Account, Balance, transactionType

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class Plugin(Plugin):
    LOGIN_URL = 'https://mijn.ing.nl/internetbankieren/SesamLoginServlet'
    ACCOUNTS_URL = 'https://bankieren.mijn.ing.nl/particulier/betalen/index'
    CREDITCARD_URL = 'https://bankieren.mijn.ing.nl/particulier/creditcard/saldo-overzicht/index'

    #
    #
    # Log-in
    #
    #
    def login(self, username, password):
        self.open_browser()
        logger.debug('Navigating to %s...' % self.LOGIN_URL)

        self.driver.get(self.LOGIN_URL)
        assert "ING" in self.driver.title

        self.locate((By.XPATH, '//label[text()="Gebruikersnaam"]')).send_keys(username)
        self.locate((By.XPATH, '//label[text()="Wachtwoord"]')).send_keys(password)
        self.locate((By.CSS_SELECTOR, '.submit')).click()

        self.locate((By.XPATH,
            "//body/div/div/h1[contains(.,'Mijn ING Overzicht')]"),
            wait = self.LOGIN_TIMEOUT)

        self.logged_in = 1

    #
    #
    #
    #   Scraping of the credit card
    #
    #   At this point multiple credit cards are not supported
    #
    #
    def download_ccard(self, account):
        assert account.type == 'ccard'

        # Download credit card statement
        logger.debug('Navigating to %s...', self.CREDITCARD_URL)
        self.driver.get(self.CREDITCARD_URL)

        statement = Statement(account = account)

        # We keep on clicking on "previous period" until we reach the datefrom or the very first statement available
        while True:
            # get all the lines of the current period
            for tr in self.locate_all((By.XPATH,
                "//div[@id='statementDetailTable']/div/div[@class='riaf-datatable-canvas']"
                   + "/table/tbody/tr[contains(@class, 'riaf-datatable-contents')]")):

                logger.debug('transaction:\n%s' % tr.text)

                date_td = tr.find_element_by_css_selector("td.riaf-datatable-column-date")

                # Skip empty lines...
                if not date_td.text:
                    continue

                transaction = Transaction(
                    date    = datetime.strptime(date_td.text,'%d-%m-%Y').date(),
                    amount  = float(tr.find_element_by_css_selector(
                        "td.riaf-datatable-column-amount").text.replace('.','').replace(',','.'))
                )

                # Should we continue ?
                if account.last_download and transaction.date < account.last_download.date():
                    return statement.finalize()

                # Is this a reservation?
                if tr.find_element_by_css_selector("td.riaf-datatable-column-first").text == '*':
                    transaction.reservation = True

                # Set up the sign of the amount and the transaction type
                sign_class = tr.find_element_by_css_selector("td.riaf-datatable-column-last")\
                    .find_element_by_tag_name('span').get_attribute("class")
                if sign_class == 'riaf-datatable-icon-crdb-db':
                    transaction.type = transactionType.DEBIT
                    transaction.amount = -transaction.amount
                elif sign_class == 'riaf-datatable-icon-crdb-cr':
                    transaction.type = transactionType.CREDIT
                else:
                    raise ValueError('No sign for transaction')

                td_text = tr.find_elements_by_css_selector("td.riaf-datatable-column-text")
                card_number = td_text[1].text
                transaction.name = td_text[0].text

                # Get the memo...
                tr.click()
                tr_details = tr.find_element_by_xpath("following-sibling::tr[@class='riaf-datatable-details-open']")
                # logger.debug('details row:\n %s' % tr_details.text)

                # XXX We could consider beautifying below...
                transaction.memo  = tr_details.find_element_by_css_selector("td.riaf-datatable-details-contents").text

                statement.transactions.append(transaction)

            # Download previous credit card statement
            try:
                self.driver.find_element_by_id('previousPeriod').click()
            except NoSuchElementException:
                # Reached the very first period...
                return statement.finalize()


    #
    #
    # Download current account
    #
    #
    #
    def download_current(self, account):
        # Navigate to the curent accounts
        self.driver.get(self.ACCOUNTS_URL)
        sleep(self.CLICK_SLEEP)

        # Navigate to the account... Click
        self.locate((By.XPATH, "//div[@id='accounts']/div/div/ol/li/a/div[contains(text(), '"
                     + account.name + "')]")).click()
        sleep(self.CLICK_SLEEP)

        # Wait until the new account started to load...
        #self.wait().until(EC.invisibility_of_element_located((By.XPATH,
        #    "//table[@id='receivedTransactions']/thead/tr/th[contains(text(), 'Datum')]")))
        self.wait().until(EC.presence_of_element_located((By.XPATH,
            "//table[@id='receivedTransactions']/thead/tr/th[contains(text(), 'Datum')]")))

        statement = Statement(account = account)

        # Known transaction types...
        transaction_types = {
            'AC'    : transactionType.PAYMENT,
            'IC'    : transactionType.DIRECTDEBIT,
            'BA'    : transactionType.POS,
            'OV'    : transactionType.XFER,
            'DV'    : transactionType.OTHER,
            'PK'    : transactionType.CASH,
            'FL'    : transactionType.XFER,
            'PO'    : transactionType.REPEATPMT,
            'GF'    : transactionType.XFER,
            'ST'    : transactionType.DEP,
            'GM'    : transactionType.ATM,
            'VZ'    : transactionType.DIRECTDEBIT,
            'GT'    : transactionType.XFER
        }

        rows = self.locate_all((By.XPATH, "//table[@id='receivedTransactions']/tbody/tr"))
        while True:
            for tr in rows:
                # Skip horizontal lines...
                if tr.find_elements_by_tag_name('hr'):
                    continue

                if tr.find_elements_by_css_selector('div.ng-hide'):
                    tr.click()

                (td_date, td_descr, td_type, td_amount) = tr.find_elements_by_tag_name('td')
                transaction = Transaction(
                    date  = datetime.strptime(td_date.text,'%d-%m-%Y').date(),
                    type  = transaction_types.get(td_type.text, None)
                )

                if account.last_download and transaction.date < account.last_download.date():
                    return statement.finalize()

                # Amount...
                m = re.match('([^\s]+)\s(Af|Bij)',td_amount.text)
                transaction.amount = float(m.group(1).replace('.','').replace(',','.'))

                # Sign and type
                if m.group(2) == 'Bij':
                    if not transaction.type:
                        transaction.type = transactionType.CREDIT
                        logger.warning('uknown transaction type %s, using generic credit' % td_type.text)
                elif m.group(2) == 'Af':
                    transaction.amount = -transaction.amount
                    if not transaction.type:
                        transaction.type = transactionType.DEBIT
                        logger.warning('uknown transaction type %s, using generic debit' % td_type.text)
                else:
                    raise ValueError('No sign for transaction')

                all_data = td_descr.find_element_by_xpath(
                    "div/div/b[text()='Mededelingen']/../following-sibling::div").text.split('\n')

                transaction.name = all_data[0].replace('Naam: ','')

                all_data[1] = all_data[1].replace('Omschrijving: ', '')
                transaction.memo = "\n".join(all_data[1:])

                statement.transactions.append(transaction)

            # Click to download more
            getMore = self.driver.find_elements_by_id('getMore')
            showMore = self.driver.find_elements_by_id('showMore')
            if showMore and showMore[0].is_displayed():
                    showMore[0].click()
            elif getMore and getMore[0].is_displayed():
                    getMore[0].click()
            else:
                    return statement.finalize()

            rows = self.locate_all_inner(tr, (By.XPATH, 'following-sibling::tr'))


    def parse_td_descr(self, td_descr, transaction):
        logger.debug("parsing transaction description:\n%s" % td_descr.text)

        (line1, line2, all_data) = td_descr.find_elements_by_xpath('div')
        transaction.name = line1.text.encode('utf-8').strip() + line2.text.encode('utf-8').strip()
        transaction.memo = ""

        for div in all_data.find_elements_by_xpath('div'):
            div_class = div.get_attribute('class')

            if div_class == 'clearfix':
                transaction.memo += "\n"
            elif 'l-w-30' in div_class:
                transaction.memo += div.text.encode('utf-8').strip() + ': '
            elif 'l-w-70' in div_class:
                transaction.memo += div.text.encode('utf-8').strip()
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