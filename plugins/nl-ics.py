"""
Web-bank-connect for Internatinal Card Services NL
http://www.icscards.nl

Author: Alex Yushin <alexis@ww.net>

"""

import re
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


from datetime import date, datetime, timedelta

from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException,StaleElementReferenceException

from wbc.wbc import Connector

from pprint import pformat

class Plugin(Connector):
    login_url = 'https://www.icscards.nl/ics/login'
    creditcard_url = 'https://www.icscards.nl/ics/mijn/accountoverview'

    def login(self, username, password):
        self.open_browser()
        self.driver.get(self.login_url)

#        self.driver.find_element_by_link_text('Accepteren').click()
        self.driver.find_element_by_id("trcAccept").click()

        elem = self.driver.find_element_by_id("username")
        elem.send_keys(username)
        elem = self.driver.find_element_by_id("password")
        elem.send_keys(password)

        self.driver.find_element_by_id("button-login").click()
        self.driver.find_element_by_link_text('Mijn ICS')


    def scrape_ccard(self, account, datefrom = None):
        LOOKUP_MONTH = (None,'jan', 'feb', 'mrt', 'apr', 'mei', 'jun', 'jul', 'aug', 'sep', 'okt', 'nov', 'dec')

        # Download credit card statement
        logger.debug("Navigating to the credit card %s..." % self.creditcard_url)
        self.driver.get(self.creditcard_url)

        transactions = []

        # ICS gives us all the available statements at once, just not all of them are visible...
        # XXX For some reason the last element is stale...
        for statement_tr in self.driver.find_elements_by_css_selector('table tbody tr.statement-header')[:-1]:
            logger.debug('found statement line:\n %s' % statement_tr.text)

            # Show more statements...
            if 'rowhide'in statement_tr.get_attribute('class'):
                show_more = self.driver.find_elements_by_css_selector('tr.show-more')
                if show_more[0].is_displayed():
                    show_more[0].click()

            statement_id = statement_tr.get_attribute('id')
            if statement_id != 'current':
                logger.debug('statement date %s, datefrom %s' %((datetime.strptime(statement_id, '%Y%m') + timedelta(days=31)).date(), datefrom))
                if (datetime.strptime(statement_id, '%Y%m') + timedelta(days=31)).date() < datefrom:
                    break

            # Expand the statement to see its transactions...
            if not 'expanded' in statement_tr.get_attribute('class'):
                statement_tr.click()


        for transaction_tr in self.driver.find_elements_by_css_selector("table tbody tr.transaction-row"):
            logger.debug('found transaction %s\n' % transaction_tr.text)

            # Skip months with no transactions...
            if 'no-transactions' in transaction_tr.find_element_by_tag_name('td').get_attribute('class'):
                continue

            # Get the statement year...
            tr_class = transaction_tr.get_attribute('class')
            pos = tr_class.find('statement-')+10
            year = tr_class[pos:pos+4]
            if year == 'curr':
                year = int(datetime.utcnow().year)
            else:
                year = int(year)

            # ... and the date of the transaction...
            tr_date = transaction_tr.find_element_by_css_selector('td.col1').text.split()
            if not tr_date:
                # skip transactions without date...
                continue

            # special case... december in january statement
            if tr_class[pos+5:pos+6] == '01' and LOOKUP_MONTH.index(tr_date[1]) == 12:
                year -= 1

            transaction_date = date(year, LOOKUP_MONTH.index(tr_date[1]), int(tr_date[0]))
            logger.debug('transaction date %s' % transaction_date)

            # Set up a statement line...
            line = {'date'  : transaction_date,
                    'name'  : transaction_tr.find_element_by_css_selector('td.col2').text.encode('utf-8')}

            line['memo'] = line['name'] + ' ' + transaction_tr.find_element_by_css_selector('td.foreign').text.encode('utf-8')

            line['amount'] = float(transaction_tr.find_element_by_css_selector("td div span.amount").text.replace('.','').replace(',','.'))

            if 'Gereserveerd' in transaction_tr.find_element_by_css_selector("td.foreign span.popover").text:
                line['reservation'] = True

            sign = transaction_tr.find_element_by_css_selector('td span.float-right').text

            if sign == 'Af':
                line['type'] = 'DEBIT'
                line['amount'] = -line['amount']
            elif sign == 'Bij':
                line['type'] = 'CREDIT'
            else:
                raise ValueError('No sign for transaction')

            # Are we done?
            if datefrom and line['date'] < datefrom:
                return transactions

            transactions.append(line)

        return transactions