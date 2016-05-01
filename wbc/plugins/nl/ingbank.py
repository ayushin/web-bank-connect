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
    CREDITCARD__LIST_URL = 'https://bankieren.mijn.ing.nl/particulier/creditcard/index'

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

        # card_li = self.locate((By.XPATH,
        #     "//div[@class='riaf-focusgroup-column-left']/div/div/div[@class='riaf-focusgroup-itemselector-content']/"
        #     + "div/ul/li[@class='actief']/p[@class='riaf-focusgroup-itemselector-name'][contains(.,'"
        #     + account.name + "')]/.."))
        # card_li.click()
        #
        # statement.closing_balance = Balance(
        #     date    = datetime.utcnow().date(),
        #     amount  = float(card_li.find_element_by_css_selector(
        #         'p.riaf-focusgroup-itemselector-balance').text.encode('utf-8').replace('.','').replace(',','.').replace('€','').strip())
        # )
        # logger.info('credit card %s balance %f' % (statement.account.name, statement.closing_balance.amount))

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
        account_div = self.locate((By.XPATH, "//div[@id='accounts']/div/div/ol/li/a/div[contains(text(), '"
                     + account.name + "')]"))
        account_div.click()
        sleep(self.CLICK_SLEEP)

        statement = Statement(account = account)
        statement.closing_balance = Balance(
            date    = datetime.utcnow().date(),
            amount  = float(account_div.find_element_by_xpath(
                'following-sibling::div').text.encode('utf-8').replace('.','').replace(',','.').replace('€','').strip())
        )
        logger.info('account %s balance %f' % (statement.account.name, statement.closing_balance.amount))

        # Wait until the new account started to load...
        #self.wait().until(EC.invisibility_of_element_located((By.XPATH,
        #    "//table[@id='receivedTransactions']/thead/tr/th[contains(text(), 'Datum')]")))

        try:
            self.driver.find_element_by_id('endListMessage')
            logger.info('No transactions for %s' % account.name)
            return statement
        except NoSuchElementException:
            pass

        self.wait().until(EC.presence_of_element_located((By.XPATH,
            "//table[@id='receivedTransactions']/thead/tr/th[contains(text(), 'Datum')]")))


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
        logger.info("Navigating to %s", self.ACCOUNTS_URL)
        self.driver.get(self.ACCOUNTS_URL)

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

            accounts.append(Account(
                type    =   'current',
                name    =   account_li.find_elements_by_xpath('a/div')[1].text
            ))

        # Check if we have a credit card...
        logger.info("Navigating to %s", self.CREDITCARD__LIST_URL)
        self.driver.get(self.CREDITCARD__LIST_URL)

        cards = self.locate_all((By.CSS_SELECTOR,
            "div.riaf-focusgroup-column-left div div div.riaf-focusgroup-itemselector-content div ul li.actief"))

        for card in cards:
            accounts.append(Account(
                type    =   'ccard',
                # The first p of this class is the name
                name    =   card.find_element_by_css_selector('p.riaf-focusgroup-itemselector-name').text
            ))

        return accounts