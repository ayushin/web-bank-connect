"""
Web-bank-connect for Internatinal Card Services NL
http://www.icscards.nl

Author: Alex Yushin <alexis@ww.net>

"""

from datetime import date, datetime

from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException

from wbc.wbc import Connector

class Plugin(Connector):
    login_url = 'https://www.icscards.nl/ics/login'
    creditcard_url = 'https://www.icscards.nl/ics/mijn/accountoverview'

    def login(self, username, password):
        self.open_browser()
        self.driver.get(self.login_url)
        assert "Inloggen - Mijn ICS" in self.driver.title

        elem = self.driver.find_element_by_id("username")
        elem.send_keys(username)
        elem = self.driver.find_element_by_id("password")
        elem.send_keys(password)

        self.driver.find_element_by_id("trcAccept").click()
        self.driver.find_element_by_id("button-login").click()

        WebDriverWait(self.driver, 3)
        assert "International Card Services" in self.driver.title

    def scrape_ccard(self, account, datefrom = None):
        # Download credit card statement
        print "Navigating to the credit card URL..."
        self.driver.get(self.creditcard_url)

        transactions = []

        # Expand all the visible rows
        for element in self.driver.find_elements_by_class_name('statement-header'):

            if not element.is_displayed():
                self.driver.find_element_by_class_name('show-more').click()

            while not 'expanded' in element.get_attribute('class'):
                element.click()
                WebDriverWait(self.driver, 3)

            id = element.get_attribute('id')

            if id == 'current':
                #tr_xpath = '//tr[@class="transaction-row transaction-payment statement-' + id + '"]'
                year = str(date.today().year)
            else:
                year = str(id[:4])

            for tr_xpath in ('//tr[@class="transaction-row statement-' + id + '"]', '//tr[@class="transaction-row transaction-payment statement-' + id + '"]'):
                for tr in self.driver.find_elements_by_xpath(tr_xpath):

                    elem = None
                    try:
                        elem = tr.find_element_by_class_name('col1')

                    except NoSuchElementException:
                        elem = None

                    # No transactions this month?
                    if not elem:
                        break

                    tr_date = elem.text.encode()

                    # Do not import transactions without date
                    if tr_date == '':
                        continue

                    tr_date = str.replace(tr_date, 'dec', '12')
                    tr_date = str.replace(tr_date, 'nov', '11')
                    tr_date = str.replace(tr_date, 'okt', '10')
                    tr_date = str.replace(tr_date, 'sep', '09')
                    tr_date = str.replace(tr_date, 'aug', '08')
                    tr_date = str.replace(tr_date, 'jul', '07')
                    tr_date = str.replace(tr_date, 'jun', '06')
                    tr_date = str.replace(tr_date, 'mei', '05')
                    tr_date = str.replace(tr_date, 'apr', '04')
                    tr_date = str.replace(tr_date, 'mrt', '03')
                    tr_date = str.replace(tr_date, 'feb', '02')
                    tr_date = str.replace(tr_date, 'jan', '01')

                    # Set up a statement line...
                    line = {'date'  : datetime.strptime(tr_date + ' ' + year, '%d %m %Y').date(),
                            'name'  : tr.find_element_by_class_name('col2').text}

                    line['memo'] = line['name'] + ' ' + tr.find_element_by_class_name('foreign').text

                    line['amount'] = float(tr.find_element_by_xpath("td/div/span[@class='amount']").text.replace('.','').replace(',','.'))

                    sign = tr.find_element_by_xpath("td[not(@id) and not(@class)]/span").text

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