"""
Web-bank-connect for Internatinal Card Services NL
http://www.icscards.nl

Author: Alex Yushin <alexis@ww.net>

"""

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


from datetime import date, datetime, timedelta
from time import sleep

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException,StaleElementReferenceException

from wbc.plugins.base import Plugin
from wbc.models import Statement, Transaction, transactionType

from pprint import pformat

class Plugin(Plugin):
    LOGIN_URL = 'https://www.icscards.nl/ics/login'
    CREDITCARD_URL = 'https://www.icscards.nl/ics/mijn/accountoverview'

    def login(self, username, password):
        self.open_browser()
        self.driver.get(self.LOGIN_URL)

#        self.driver.find_element_by_link_text('Accepteren').click()
        self.locate((By.ID, "trcAccept")).click()
        self.locate((By.ID, "username")).send_keys(username)
        self.locate((By.ID, "password")).send_keys(password)
        self.locate((By.ID, "button-login")).click()
        self.locate((By.LINK_TEXT,'Mijn ICS'), wait = self.LOGIN_TIMEOUT)

        self.logged_in = True

    def download_ccard(self, account):
        assert account.type == 'ccard'

        LOOKUP_MONTH = (None, 'jan', 'feb', 'mrt', 'apr', 'mei', 'jun', 'jul', 'aug', 'sep', 'okt', 'nov', 'dec')

        statement = Statement()

        # Download credit card statement
        logger.debug("Navigating to the credit card %s..." % self.CREDITCARD_URL)
        self.driver.get(self.CREDITCARD_URL)

        # ICS gives us all the available statements at once, just not all of them are visible...

        # XXX For some reason the last element is stale...
        for statement_tr in self.locate_all((By.CSS_SELECTOR, 'table tbody tr.statement-header'))[:-1]:
            logger.debug('found statement line:\n %s' % statement_tr.text)

            # Show more statements...
            if 'rowhide' in statement_tr.get_attribute('class'):
                show_more = self.locate_all((By.CSS_SELECTOR, 'tr.show-more'))
                if show_more[0].is_displayed():
                    show_more[0].click()

            # statement_id = statement_tr.get_attribute('id')
            # if statement_id != 'current':
            #     logger.debug('statement date %s, datefrom %s' %((datetime.strptime(statement_id, '%Y%m') + timedelta(days=31)).date(), datefrom))
            #     if (datetime.strptime(statement_id, '%Y%m') + timedelta(days=31)).date() < datefrom:
            #         break

            # Expand the statement to see its transactions...
            if not 'expanded' in statement_tr.get_attribute('class'):
                statement_tr.click()
                sleep(self.CLICK_SLEEP)
                self.wait(('loading' not in statement_tr.get_attribute('class')))

            for tr in self.locate_all(
                (By.CSS_SELECTOR, "table tbody tr.transaction-row.statement-"
                          + statement_tr.get_attribute('id'))):

                logger.debug('found transaction row %s\n' % tr.text)

                # Skip months with no transactions...
                if tr.find_elements_by_css_selector('td.no-transactions'):
                    continue

                # Get the statement year...
                tr_class = tr.get_attribute('class')
                pos = tr_class.find('statement-')+10
                year = tr_class[pos:pos+4]
                month = None
                if year == 'curr':
                    year = int(datetime.utcnow().year)
                    month = int(datetime.utcnow().month)
                else:
                    year = int(year)
                    month = int(tr_class[pos+4:pos+6])

                # ... and the date of the transaction...
                tr_date = tr.find_element_by_css_selector('td.col1').text.split()
                if not tr_date:
                    # skip transactions without date...
                    continue

                # special case... december in january statement... one case won't
                if LOOKUP_MONTH.index(tr_date[1]) == 12 and month == 1:
                    year -= 1

                transaction_date = date(year, LOOKUP_MONTH.index(tr_date[1]), int(tr_date[0]))
                logger.debug('transaction date %s' % transaction_date)

                # Set up a statement line...
                transaction = Transaction(
                    date = transaction_date,
                    name = tr.find_element_by_css_selector('td.col2').text,
                    amount = float(tr.find_element_by_css_selector("td div span.amount").text.replace('.','').replace(',','.'))
                )


                transaction.memo = (transaction.name + ' ' + tr.find_element_by_css_selector('td.foreign').text).strip()

                # Mark reservations as such...
                if 'Gereserveerd' in tr.find_element_by_css_selector("td.foreign span.popover").text:
                    transaction.reservation = True

                sign = tr.find_element_by_css_selector('td span.float-right').text
                if sign == 'Af':
                    transaction.type = transactionType.DEBIT
                    transaction.amount = -transaction.amount
                elif sign == 'Bij':
                    transaction.type = transactionType.CREDIT
                else:
                    raise ValueError('No sign for transaction')

                # Are we done?
                if account.last_download and transaction.date < account.last_download.date():
                    return statement.finalize()

                statement.transactions.append(transaction)

            # Collapse when done...
            statement_tr.click()

        return statement.finalize()

    def logout(self):
        pass